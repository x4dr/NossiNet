import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from re import Match
import bleach
import markdown
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    Blueprint,
)
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import traverse_md, search_tables
from markupsafe import Markup

from NossiPack.User import User, Config
from NossiPack.WikiCharacterSheet import WikiCharacterSheet
from NossiPack.WikiPage import WikiPage
from NossiSite import ALLOWED_TAGS
from NossiSite.base import log
from NossiSite.helpers import checklogin, srs

WikiPage.set_wikipath(Path.home() / "wiki")
wikistamp = [0.0]

chara_objects = {}
page_cache = {}
mdlinks = re.compile(r"<a href=\"(.*?)\".*?</a")

bleach.ALLOWED_TAGS = ALLOWED_TAGS

bleach.ALLOWED_ATTRIBUTES.update(
    {
        "img": ["src"],
        "h1": ["id"],
        "h2": ["id"],
        "h3": ["id"],
        "h4": ["id"],
        "h5": ["id"],
    }
)
views = Blueprint("wiki", __name__)


@views.after_app_request
def update(response):
    if not WikiPage.wikicache:
        WikiPage.updatewikicache()
    return response


@views.route("/index/<path:path>")
@views.route("/index/")
def wiki_index(path="."):
    r = WikiPage.wikindex()
    path = Path(path)
    if (
        not (WikiPage.wikipath() / path).exists()
        or not (WikiPage.wikipath() / path).is_dir()
    ):
        abort(404)
    return render_template(
        "wikindex.html",
        current_path=path if path.as_posix() != "." else None,
        parent=path.parent.as_posix(),
        subdirs=sorted(
            [
                x.stem
                for x in (WikiPage.wikipath() / path).iterdir()
                if x.is_dir()  # only show directories
                and not x.stem.startswith(".")  # hide hidden directories
            ]
        ),
        entries=[x.with_suffix("").as_posix() for x in r if x.parent == path],
        tags=WikiPage.gettags(),
    )


@views.route("/bytag/")
@views.route("/bytag/<tag>")
def tagsearch(tag=None):
    r = WikiPage.wikindex()
    t = WikiPage.gettags()
    r = (
        [x for x in r if tag in t[x.as_posix().replace(x.name, x.stem)]]
        if tag
        else [x for x in r if not t[x.as_posix().replace(x.name, x.stem)]]
    )
    return render_template(
        "wikindex.html",
        current_path=None,
        parent=None,
        subdirs=[],
        entries=[x.with_suffix("").as_posix() for x in r],
        tags=t,
    )


@views.route("/wikiadmin/<path:page>", methods=["GET", "POST"])
def adminwiki(page: str = None):
    path: Path = (WikiPage.wikipath() / page).with_suffix(".md")
    if request.method == "GET":
        backlinks = [
            k
            for k, v in WikiPage.getlinks().items()
            if any(link.startswith(page) for link in v)
        ]
        info = subprocess.run(
            [
                (Path("~").expanduser() / "bin/wikidata").as_posix(),
                path.relative_to(WikiPage.wikipath()).as_posix(),
            ],
            shell=True,
            stdout=subprocess.PIPE,
        )
        info = (info.stdout or bytes()).decode("utf-8")
        try:
            return render_template(
                "adminwiki.html",
                page=page,
                links=WikiPage.getlinks().get(page, []),
                backlinks=backlinks,
                wordcount=len(WikiPage.load_str(page).body.split()),
                last_edited=info,
            )
        except DescriptiveError as e:
            flash(" ".join(e.args), "error")
            return redirect(url_for("wiki.wiki_index"))
    n = None
    if path.exists():
        n = WikiPage.wikipath() / request.form["n"]
        if n.is_dir():
            n = n / path.name
        n = n.relative_to(WikiPage.wikipath())
    for k in WikiPage.wikicache.keys():
        if path.relative_to(
            WikiPage.wikipath()
        ).as_posix() in k or k in path.relative_to(WikiPage.wikipath()):
            WikiPage.cacheclear(WikiPage.locate(k))
    if "delete" in request.form:
        n = (WikiPage.wikipath() / n).with_suffix(".md")
        if n != path:
            flash("Type in the page name to delete it.", "error")
            return redirect(url_for("wiki.adminwiki", page=page))
        with (WikiPage.wikipath() / "control").open("a+") as h:
            h.write(f"{session['user']} deleted {page}.\n")
        retcode = subprocess.run(
            [
                Path("~").expanduser() / "bin/wikimove",
                path.relative_to(WikiPage.wikipath()).as_posix(),
                (".deleted" / path.relative_to(WikiPage.wikipath())).as_posix(),
            ],
        ).returncode
        if retcode:
            flash(f"Something went wrong while deleting {page}.", "warning")
        else:
            flash(f"Deleted {page}.", "warning")
        WikiPage.updatewikicache()
        return redirect(url_for("wiki.wiki_index"))
    if "move" in request.form:
        with (WikiPage.wikipath() / "control").open("a+") as h:
            h.write(
                f"{session['user']} moved {path.relative_to(WikiPage.wikipath())} to {n}.\n"
            )
        subprocess.run(
            [
                Path("~").expanduser() / "bin/wikimove",
                path.relative_to(WikiPage.wikipath()).as_posix(),
                n.as_posix(),
            ]
        )
        flash(f"Moved {path.relative_to(WikiPage.wikipath())} to {n}.", "warning")
        WikiPage.updatewikicache()
        return redirect(url_for("wiki.wiki_index", page=n))
    abort(400)


@views.route("/wiki", methods=["GET", "POST"])
@views.route("/wiki/", methods=["GET", "POST"])
@views.route("/wiki/<path:page>", methods=["GET", "POST"])
def wikipage(page=None):
    raw = request.url.endswith("/raw")
    if raw:
        page = page[:-4]
    if page is None:
        page = request.form.get("n", None)
        if page is None:
            return wiki_index()
        if "edit" in request.form:
            return redirect(url_for("wiki.wikipage", page=page))
        elif "administrate" in request.form:
            return redirect(url_for("wiki.adminwiki", page=page))
        else:
            abort(400)
    try:
        page = page.lower()
        page = page.strip(".").replace("/.", "/")  # remove hidden directory-dots
        p = WikiPage.locate(page)
        if p.as_posix()[:-3] != page:
            return redirect(url_for("wiki.wikipage", page=p))
        loaded_page = WikiPage.load_str(page)
    except (DescriptiveError, FileNotFoundError) as e:
        if (
            isinstance(e, DescriptiveError)
            and str(e.args[0]) != page + " not found in wiki."
        ):
            raise
        if session.get("logged_in"):
            entry = dict(id=0, text="", tags="", author=session.get("user"))
            return render_template(
                "edit_entry.html", mode="wiki", wiki=page, entry=entry
            )
        flash("That page doesn't exist. Log in to create it!")
        session["returnto"] = request.url
        return redirect(url_for("views.login"))
    if not raw:
        body = bleach.clean(loaded_page.body)
        body = markdown.markdown(body, extensions=["tables", "toc", "nl2br"])
        body = fill_infolets(body, page)
        return render_template(
            "wikipage.html",
            title=loaded_page.title,
            tags=loaded_page.tags,
            body=body,
            wiki=page,
        )
    return loaded_page.body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@views.route("/edit/<path:page>", methods=["GET", "POST"])
def editwiki(page=None):
    checklogin()
    page = page.lower()
    try:
        p = WikiPage.locate(page)
    except FileNotFoundError:
        # check if the page is eligible for creation
        if not (WikiPage.wikipath() / Path(page).parent).exists():
            return redirect(url_for("wiki.wikipage", page=Path(page).stem))
        (WikiPage.wikipath() / Path(page)).touch()  # create
        p = WikiPage.locate(page)
    if p.as_posix()[:-3] != page:
        return redirect(url_for("wiki.wikipage", page=p))
    if request.method == "GET":
        try:
            author = ""
            ident = (page,)
            try:
                loaded_page = WikiPage.load(p)
            except DescriptiveError:
                return wikipage(page)
            entry = dict(
                author=author,
                id=ident,
                title=loaded_page.title,
                tags=" ".join(loaded_page.tags),
                text=loaded_page.body,
            )
            return render_template(
                "edit_entry.html", mode="wiki", wiki=page, entry=entry
            )
        except FileNotFoundError:
            flash("entry " + str(page) + " not found.")
    if request.method == "POST":
        if request.form.get("wiki", None) is not None:
            log.info(f"saving wiki file {request.form['wiki']}")
            try:
                page = WikiPage.load(p)
                page.title = request.form["title"]
                page.tags = request.form["tags"].split(" ")
                page.body = request.form["text"]
                page.links = mdlinks.findall(markdown.markdown(request.form["text"]))
            except DescriptiveError:
                page = WikiPage(
                    title=request.form["title"],
                    tags=request.form["tags"].split(" "),
                    body=request.form["text"],
                    links=mdlinks.findall(markdown.markdown(request.form["text"])),
                    meta=[],
                )

            page.save(p, session["user"])
            flash(f"Saved {page.title.strip() or p}.")
        return redirect(url_for("wiki.wikipage", page=request.form.get("wiki", None)))
    return abort(405)


@views.route("/fensheet/<c>")
def fensheet(c):
    un = session.get("user", "")
    try:
        time0 = time.time()
        char = WikiCharacterSheet.load_str(c)
        if char is None:
            return redirect(url_for("wiki.tagsearch", tag="character"))
        u = User(un).configs()
        time1 = time.time()
        body = render_template(
            "fensheet.html",
            character=char,
            context=c,
            userconf=u,
            infolet=infolet_filler(c),
            md=lambda x: markdown.markdown(x, extensions=["tables", "nl2br"]),
            extract=infolet_extractor,
            owner=u.get("character_sheet", None)
            if u.get("character_sheet", None) == c
            else "",
        )
        time2 = time.time()
        return body + f"<!---load: {time1 - time0} render: {time2 - time1}--->"
    except DescriptiveError as e:
        flash("Error with character sheet:\n" + e.args[0])
        return redirect(url_for("views.showsheet", name=c))


@views.route("/costcalc/all/<costs>/<penalty>")
@views.route("/costcalc/all/<costs>/<penalty>/<width>")
@views.route("/costcalc/all")
def ddos(costs="0, 15, 35, 60, 100", penalty="0, 0, 0, 50, 100", width=3):
    # filter costs and penalty to not include path traversal
    costs = ",".join(str(int(x)) for x in costs.split(",") if int(x) >= 0)
    penalty = ",".join(str(int(x)) for x in penalty.split(",") if int(x) >= 0)
    p = Path(costs + "-" + penalty + ".result")
    # noinspection PyBroadException
    try:
        if p.exists():
            with open(p, "r") as f:
                return f.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}
        start = time.time()
        if (
            int(costs.split(",")[-1]) * 3 + sum(int(x) for x in penalty.split(",")) * 3
            > 10000
        ):
            raise AttributeError("just too large of a space")
        with open(p, "w") as f:
            res = []
            i = 0
            while i == 0 or not all(
                all(int(x) >= 5 for x in y if x) for y in res[-1][1]
            ):
                r = FenCharacter.cost_calc(str(i), width)
                log.debug(f"Fencalc {i} {res}")
                if i == 0 or r != res[-1][1]:
                    res.append([str(i), r])
                if time.time() - start > 30:
                    raise TimeoutError()
                i += 1
            for k, v in res:
                line = f"{'      '.join(', '.join(str(y) for y in x) for x in v)}"
                f.write(f" {k: <4}: {line} \n")
        return "Reload please", 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception:
        with open(p, "w") as f:
            f.write("an error has previously occured and this request is blocked")
            return (
                "error, this request is now blocked",
                200,
                {"Content-Type": "text/plain; charset=utf-8"},
            )


@views.route("/costcalc/<inputstring>/<width>")
@views.route("/costcalc/<inputstring>")
def fen_calc(inputstring: str, width=3):
    return (
        "\n".join(
            ", ".join(str(y) for y in line)
            for line in FenCharacter.cost_calc(inputstring, width)
        ),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@views.route("/search", methods=["GET"])
def searchwiki():
    pre = 30
    pos = 30
    key = request.args.get("s", "")
    key = key.lower()
    if not key.strip():
        return []
    matches = []
    length = len(key)
    for w in WikiPage.wikindex():
        loaded_page = WikiPage.load(w)
        w = w.stem
        if key in loaded_page.title.lower():
            matches.append((w, loaded_page.title, "title"))
        for tag in loaded_page.tags:
            if key in tag.lower():
                matches.append((w, loaded_page.title, f"tag: {tag}"))
        p = 0
        while loaded_page.body[p:]:
            m = loaded_page.body[p:].lower().find(key)
            if m == -1:
                break
            matches.append(
                (
                    w,
                    loaded_page.title,
                    f"{loaded_page.body[max(p+m-pre,0):p+m+pos+length]}",
                )
            )
            p += m + 1
    return render_template(
        "search_results.html", results=matches, start=pre, end=pre + length
    )


@views.route("/live_edit", methods=["POST"])
def live_edit():
    if request.is_json and (x := request.get_json()):
        a = [
            e
            for e in [
                urllib.parse.unquote(x["cat"]),
                urllib.parse.unquote(x.get("sec", "")),
                urllib.parse.unquote(x.get("it", "")),
            ]
            if e
        ]

        res: str = WikiPage.load_str(x["context"]).body
        if m := re.match(r"perc(0\.?\d*|1)", a[0]):  # percentage request
            ratio = float(m.group(1))
            pos = int(len(res) * ratio)
            return {"data": res[max(0, pos - 200) : pos + 500]}
        for seek in a[:-1]:
            res = traverse_md(res, seek)
        found = traverse_md(res, a[-1])

        if not found:
            found = search_tables(res, a[-1], 1)

        return {"data": found}
    # else, form was transmitted
    x = request.form
    context = x.get("context", None)
    wiki = not context
    context = context or x.get("wiki", None)

    sheet_owner = Config.users_with_option_value("character_sheet", context)
    if sheet_owner:
        sheet_owner = sheet_owner[0][0]
    if (not sheet_owner) or session.get("user") == sheet_owner:
        old = x["original"].replace("\r\n", "\n")
        new = x["new"].replace("\r\n", "\n")
        if not old == new:
            context = WikiPage.locate(context)
            log.info(f"livereplacing {context}")
            page = WikiPage.load(context)
            page.body = page.body.replace("\r\n", "\n")
            if old not in page.body:
                if old[:-1] in page.body:
                    old = old[:-1]
                else:
                    log.error(f"live replace didn't match {context}")
            page.body = page.body.replace(old, new, 1)
            page.save(context, session.get("user"))
        else:
            log.info(f"rejected empty replace {context}")
    else:
        flash("Unauthorized, so ... no.", "error")
    if not wiki:
        return redirect(url_for("wiki.fensheet", c=context))
    else:
        return redirect(url_for("wiki.wikipage", page=context))


@views.route("/q/<a>")
@views.route("/q/<a>/raw")
@views.route("/specific/<a>")
@views.route("/specific/<a>/raw")
def specific(a: str, parse_md=None):
    parse_md = not request.url.endswith("/raw") if parse_md is None else parse_md
    a = a.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
    a = a.split(":")
    if a[-1] == "-":
        a = a[:-1]
        hide_headline = 1
    else:
        hide_headline = 0

    article: str = WikiPage.load_str(a[0]).body
    for seek in a[1:]:
        article = traverse_md(article, seek)
    if not article:
        return "not found", 404
    else:
        article = article[article.find("\n") * hide_headline :]
    if parse_md:
        return Markup(markdown.markdown(article, extensions=["tables", "toc", "nl2br"]))
    return article


def infolet_filler(context):
    def wrap(s):
        return fill_infolets(str(s), context)

    return wrap


def infolet_extractor(x):
    m = hiddeninfos.match(str(x))
    if not m:
        return str(x)
    return m.group("name")


def weaponadd(weapon_damage_array, b, ind=0):
    if len(weapon_damage_array) != len(b):
        raise DescriptiveError("Length mismatch!", weapon_damage_array, b)
    c = []
    for i, w in enumerate(weapon_damage_array):
        c.append((w + [0, 0])[:2])
        c[-1][ind] = max(c[-1][ind] + b[i], 0)
    return c


def lowercase_access(d, k):
    data = {k.lower(): v for k, v in d.items()}
    res = data.get(k.lower(), None)
    if res is None:
        raise DescriptiveError(
            k.lower() + " does not exist in " + " ".join(data.keys())
        )
    return res


def get_info(info_context):
    def recursive_traverse(focus, path):
        for seek in path[1:]:
            focus = traverse_md(focus, seek.strip())
        return focus

    def wrap(match):
        a = match.group("ref").split(":")
        article = None
        if a[-1] == "-":
            a = a[:-1]
            hide_headline = 1
        else:
            hide_headline = 0
        try:
            if a[0].strip() == "-":
                for context_attempt in [info_context, "items", "prices", "notes"]:
                    try:
                        article = recursive_traverse(
                            WikiPage.load_str(
                                context_attempt,
                            ).body,
                            a,
                        )
                        if article:
                            context = context_attempt
                            break
                    except Exception as e:
                        print(
                            f"searching {context_attempt} for {a} encountered Error {repr(e)}"
                        )
                        article = ""
                else:
                    context = info_context
            else:
                article = recursive_traverse(WikiPage.load_str(a[0]).body, a)
                context = a[0]
        except DescriptiveError as e:
            flash(e.args[0])
            article = ""
            context = info_context

        if not article:
            if match.group("cmd") == "q":  # short version => no error
                return None
            article = ":".join(a) + "<br>[[not found]]"
        elif hide_headline:
            article = article[article.find("\n") * hide_headline :]

        res = markdown.markdown(
            fill_infolets(article, context), extensions=["tables", "toc", "nl2br"]
        )
        return res

    return wrap


def hide(func):
    def hidden(text: Match):
        header = (
            text.group("name") or text.group("ref").strip("[]-:").split(":")[-1].title()
        )
        res = func(text)
        if res is None:  # means do not replace
            return text.group("name")
        try:
            h = srs()
            return (
                f'<div class=hider data-for="{h}"><b>{header}</b></div>\n'
                f'<div id="{h}" class="hiding">{str(res)}</div>'
            )
        except Exception as e:
            return f"Error with {header}:\n  {e.args} !"

    return hidden


def headerfix(text: Match):
    if "\n" not in text.group("content"):
        return text.group()
    return (
        f"<{text.group('h')} {text.group('extra')}> "
        f"{text.group('content').splitlines()[0]}</{text.group('h')}>"
        + "\n".join(text.group("content").splitlines()[1:])
    )


hiddentable = re.compile(
    r"\[(?P<name>.*?)\[\[(?P<kind>.+?):(?P<ref>[\S ]+):(?P<mod>.*?)]]]",
    re.IGNORECASE,
)
table = re.compile(r"\[\[(?P<kind>.+?):(?P<ref>[\S ]+):(?P<mod>.*?)]]", re.IGNORECASE)
hiddeninfos = re.compile(
    r"\[(?P<name>.*?)\[\[(?P<cmd>specific|q):(?P<ref>[\S ]+)]]]", re.IGNORECASE
)
infos = re.compile(r"\[\[(?P<cmd>specific|q):(?P<ref>(-:)?[\S ]+)]]", re.IGNORECASE)
re_links = re.compile(r"\[(.+?)]\((?P<ref>.+?)\)")
headers = re.compile(
    r"<(?P<h>h\d*)\b(?P<extra>[^>]*)>(?P<content>.*?)</(?P=h)\b[^>]*>",
    re.IGNORECASE | re.DOTALL,
)


def fill_infolets(body, context):
    body = re_links.sub(r'<a href="/wiki/\g<2>"> \g<1> </a>', body)
    body = infos.sub(get_info(context), hiddeninfos.sub(hide(get_info(context)), body))
    return headers.sub(headerfix, body)
