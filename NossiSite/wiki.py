import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

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
    jsonify,
)
from markupsafe import Markup

from NossiPack.LocalMarkdown import LocalMarkdown
from NossiPack.User import User, Config
from NossiSite.base import log
from NossiSite.helpers import checklogin
from NossiSite.socks import (
    broadcast_elements,
    BroadcastElement,
    broadcast,
    generate_clock,
    generate_line,
)
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import traverse_md, MDObj
from gamepack.PBTACharacter import PBTACharacter
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage

WikiPage.set_wikipath(Path.home() / "wiki")
wikistamp = [0.0]

chara_objects = {}
mdlinks = re.compile(r"<a href=\"(.*?)\".*?</a")


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
    path = WikiPage.wikipath() / path
    if (
        not (WikiPage.wikipath() / path).exists()
        or not (WikiPage.wikipath() / path).is_dir()
    ):
        abort(404)
    return render_template(
        "wikindex.html",
        current_path=(
            path.relative_to(WikiPage.wikipath())
            if path != WikiPage.wikipath()
            else None
        ),
        parent=path.relative_to(WikiPage.wikipath()).parent.as_posix(),
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
    # copy to list to avoid changing dict while iterating
    for k in list(WikiPage.wikicache.keys()):
        if (
            path.relative_to(WikiPage.wikipath()).as_posix() in k
            or k in path.relative_to(WikiPage.wikipath()).as_posix()
        ):
            WikiPage.cacheclear(WikiPage.locate(k))
    WikiPage.cacheclear(WikiPage.locate(path))
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
                path.relative_to(WikiPage.wikipath()).with_suffix(".md").as_posix(),
                n.with_suffix(".md").as_posix(),
            ]
        )
        flash(f"Moved {path.relative_to(WikiPage.wikipath())} to {n}.", "warning")
        WikiPage.updatewikicache()
        return redirect(url_for("wiki.adminwiki", page=n))
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
            return redirect(url_for("wiki.wikipage", page=p.as_posix()[:-3]))
        loaded_page = WikiPage.load_str(page)
    except (DescriptiveError, FileNotFoundError) as e:
        if (
            isinstance(e, DescriptiveError)
            and str(e.args[0]) != page + ".md not found in wiki."
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
        body = LocalMarkdown().process(body, page=page)
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
                    meta={},
                    file=WikiPage.wikipath() / p,
                )

            page.save_overwrite(session["user"])
            flash(f"Saved {page.title.strip() or p}.")
        return redirect(url_for("wiki.wikipage", page=request.form.get("wiki", None)))
    return abort(405)


@views.route("/pbta/<path:c>")
def pbtasheet(c):
    char = WikiCharacterSheet.load_str(c)

    return render_template("pbtasheet.html", character=char.char, c=c)


@views.route("/pbta-update-notes", methods=["POST"])
def update_notes():
    context = request.args["c"]
    username = session.get("user", "")

    notes = request.form.get("notes")  # Ensure your textarea has name="notes"

    sheet = WikiCharacterSheet.load_str(context)
    if username.lower() in sheet.tags:
        sheet.char.notes = notes
        sheet.body = sheet.char.to_md()
        sheet.save_low_prio(f"notes updated by {username}")
    return jsonify(success=True)


@views.route("/active_sheet_element/<c>/health/<element_type>")
def active_elem(c, element_type):
    char = WikiCharacterSheet.load_str(c).char
    if not isinstance(char, PBTACharacter):
        raise ValueError("only PBTACharacters have active sheet elements for now")
    if element_type == "healing":
        healing = char.health_get(element_type)
        return generate_clock(
            healing[0],
            healing[1],
            f"{element_type}-{c}",
            "change_sheet_clock",
            initial=True,
        )
    return f"<div>{element_type} unhandled </div>"


@views.route("/clock/<int:active>/<int:total>/<name>/page")
@views.route("/clock/<int:active>/<int:total>")
def _generate_clock(
    active: int, total: int, name="", page="", endpoint="changeclock", initial=False
):
    generate_clock(active, total, name, page, endpoint, initial)


@views.route("/line/<int:active>/<int:total>/<name>/page")
@views.route("/line/<int:active>/<int:total>")
def _generate_line(
    active: int, total: int, name="", page="", endpoint="changeline", initial=False
):
    generate_line(active, total, name, page, endpoint, initial)


@views.route("/changeline/<name>/<page>/<delta>")
@views.route("/changeclock/<name>/<page>/<delta>")
def change_clock(name: str, page: str, delta: str):
    username = session.get("user", "")
    if username:
        if request.path.startswith("/changeline"):
            element_type = "line"
        else:
            element_type = "round"
        broadcast_elements.append(
            BroadcastElement(name, page, "wiki", element_type, False)
        )
        WikiPage.load_str(page).change_clock(name, int(delta)).save_low_prio("clock")
        broadcast.set()
    return "", 204


@views.route("/change_sheet_line/<name>/<page>/<delta>")
@views.route("/change_sheet_clock/<name>/<page>/<delta>")
def change_sheet_clock(name: str, page: str, delta: str):
    username = session.get("user", "")
    if username:
        if request.path.startswith("/change_sheet_line"):
            element_type = "line"
        else:
            element_type = "round"
        broadcast_elements.append(
            BroadcastElement(name, page, "sheet", element_type, False)
        )
        if username.lower() in (charpage := WikiCharacterSheet.load_str(page)).tags:
            char: PBTACharacter = charpage.char
            char.health[name.title()][char.current_headings[0].title()] = (
                char.health_get(name)[0] + int(delta)
            )
            charpage.save_low_prio(f"active element used by {username}")
            broadcast.set()
    return "", 204


@views.route("/fensheet/<path:c>")
def fensheet(c):
    username = session.get("user", "")
    try:
        time0 = time.time()
        char = WikiCharacterSheet.load_str(c)
        if char is None:
            return redirect(url_for("wiki.tagsearch", tag="character"))
        u = User(username).configs()
        time1 = time.time()
        charsh = u.get("character_sheet", None)
        body = render_template(
            "fensheet.html",
            character=char.char,
            context=c,
            userconf=u,
            infolet=infolet_filler(c),
            md=lambda x: LocalMarkdown.process(x, page=charsh),
            extract=infolet_extractor,
            owner=(
                u.get("character_sheet", None)
                if WikiPage.locate(c) == WikiPage.locate(charsh)
                else ""
            ),
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
                    f"{loaded_page.body[max(p + m - pre, 0):p + m + pos + length]}",
                )
            )
            p += m + 1
    return render_template(
        "search_results.html", results=matches, start=pre, end=pre + length
    )


def live_edit_get(formdata):
    a = formdata.get("path", [])
    a = [urllib.parse.unquote(x) for x in a if x]
    if not a:
        a = [formdata["percentage"]]
    t = urllib.parse.unquote(formdata.get("type", "text"))
    res: str = WikiPage.load_str(formdata["context"]).body
    if t == "text":
        return live_edit_get_text(res, a)
    if t == "table":
        return {**live_edit_get_table(res, a), "path": a}
    return {"data": "", "type": "error"}


def live_edit_get_text(res, a):
    if m := re.match(r"(0\.?\d*|1)", a[0]):  # percentage request
        ratio = float(m.group(1))
        pos = int(len(res) * ratio)
        return {"data": res[max(0, pos - 200) : pos + 500]}
    mdo = MDObj.from_md(res)
    for step in a:
        mdo = mdo.children[step]
    return {"data": mdo.to_md(), "type": "text"}


def live_edit_get_table(res, a):
    mdo = MDObj.from_md(res)
    for step in a:
        mdo = mdo.children[step]
    if mdo.tables is None:
        return {"data": "", "type": "error"}

    return {"data": mdo.tables[0].to_simple(), "type": "table"}


def live_edit_write(formdata, context):
    if formdata["type"] == "text":
        return live_edit_write_text(formdata, context)
    elif formdata["type"] == "table":
        return live_edit_write_table(formdata, context)


def live_edit_write_text(formdata, context):
    old = formdata["original"].replace("\r\n", "\n")
    new = formdata["new"].replace("\r\n", "\n")
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
        page.save_overwrite(session.get("user"))
    else:
        log.info(f"rejected empty replace {context}")


def live_edit_write_table(formdata, context):
    context = WikiPage.locate(context)
    page = WikiPage.load(context)
    md = MDObj.from_md(page.body)
    path = json.loads(formdata["path"])
    t = md
    for p in path:
        t = t.children[p]
    if not t.tables:
        raise ValueError("path failure")
    t = t.tables[0]
    t.clear_rows()

    data = [x for x in formdata.items() if x[0].startswith("table_")]
    # remove empty rows at the end
    for k, v in data:
        _, row, col = k.split("_")
        t.update_cell(int(row), int(col), v)
    t.headers = [x[1] for x in formdata.items() if x[0].startswith("header_")]
    md = md.to_md()
    if md != page.body:
        page.body = md
        page.save_overwrite(session.get("user"))


@views.route("/live_edit", methods=["POST"])
def live_edit():
    if request.is_json and (formdata := request.get_json()):
        return live_edit_get(formdata)
    # else, form was transmitted
    formdata = request.form
    context = formdata.get("context", None)
    wiki = not context
    context = context or formdata.get("wiki", None)
    sheet_owner = Config.users_with_option_value("character_sheet", context)
    if sheet_owner:
        sheet_owner = sheet_owner[0][0]
    if (not sheet_owner) or session.get("user") == sheet_owner:
        live_edit_write(formdata, context)
    else:
        flash("Unauthorized, so ... no.", "error")
    if not wiki:
        return redirect(url_for("wiki.fensheet", c=formdata["context"]))
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
        return Markup(LocalMarkdown.process(article, page=a[0]))
    return article


def infolet_filler(context):
    def wrap(s):
        return LocalMarkdown.fill_infolet(s, context)

    return wrap


def infolet_extractor(x):
    m = LocalMarkdown.infolet_re.match(str(x))
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
