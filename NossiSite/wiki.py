"""Blueprint for wiki page viewing, editing, searching, tag management, and administration."""

import json
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any
from urllib import parse

import bleach
import markdown
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import MDObj, traverse_md
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage
from markupsafe import Markup
from werkzeug.wrappers.response import Response as WerkzeugResponse

from NossiPack.markdown import NossiMarkdownProcessor
from NossiPack.User import Config
from NossiSite.base import log
from NossiSite.clock_sync import sync_clocks_with_db
from NossiSite.helpers import checklogin

WikiPage.set_wikipath(Path.home() / "wiki")
wikistamp = [0.0]
nossi_markdown = NossiMarkdownProcessor()
wiki_tags_json = json.dumps([tag.to_dict() for tag in nossi_markdown.tags])

chara_objects: dict[str, Any] = {}
mdlinks = re.compile(r"<a href=\"(.*?)\".*?</a")


bleach.ALLOWED_ATTRIBUTES.update(
    {
        "img": ["src"],
        "h1": ["id"],
        "h2": ["id"],
        "h3": ["id"],
        "h4": ["id"],
        "h5": ["id"],
    },
)
views = Blueprint("wiki", __name__)


@views.after_app_request
def update(response: WerkzeugResponse) -> WerkzeugResponse:
    """Refresh the wiki cache periodically after each request if stale."""

    def refresh() -> None:
        WikiPage.updatewikicache()

    if not WikiPage.wikicache or time.time() - WikiPage.wikistamp > 15 * 60:
        threading.Thread(target=refresh, daemon=True).start()
    return response


@views.route("/index/<path:path>")
@views.route("/index/")
def wiki_index(path: str = ".") -> str:
    """Render the wiki index page showing subdirectories and entries."""
    root = WikiPage.wikipath()
    r = WikiPage.wikindex()
    requested_path = root / path
    if not requested_path.exists() or not requested_path.is_dir():
        abort(404)

    return render_template(
        "wiki/wikindex.html",
        current_path=(requested_path.relative_to(root) if requested_path != root else None),
        parent=requested_path.relative_to(root).parent,
        subdirs=sorted(
            [
                x.stem
                for x in requested_path.iterdir()
                if x.is_dir() and not x.stem.startswith(".")  # only show directories  # hide hidden directories
            ],
        ),
        entries=[x.relative_to(root).with_suffix("") for x in r if x.parent == requested_path],
        tags=WikiPage.gettags(),
    )


@views.route("/bytag/")
@views.route("/bytag/<tag>")
def tagsearch(tag: str | None = None) -> str:
    """Render wiki index filtered by a specific tag."""
    files = WikiPage.wikindex()
    tags_by_name = WikiPage.gettags()
    results = []

    for path in files:
        name = path.as_posix().replace(path.name, path.stem)
        tags_of_page = tags_by_name.get(name, [])
        if (tag is None and not tags_of_page) or (tag in tags_of_page):
            results.append(path)

    return render_template(
        "wiki/wikindex.html",
        current_path=None,
        parent=None,
        subdirs=[],
        entries=[x.relative_to(WikiPage.wikipath()).with_suffix("").as_posix() for x in results],
        tags=tags_by_name,
    )


@views.route("/wikiadmin/<path:page>", methods=["GET", "POST"])
def adminwiki(page: str) -> str | WerkzeugResponse:
    """Render the wiki admin page or process move/delete actions."""
    path: Path = (WikiPage.wikipath() / page).with_suffix(".md")
    if request.method == "GET":
        backlinks = [k for k, v in WikiPage.getlinks().items() if any(link.startswith(page) for link in v)]
        info = subprocess.run(
            [
                (Path("~").expanduser() / "bin/wikidata").as_posix(),
                path.relative_to(WikiPage.wikipath()).as_posix(),
            ],
            shell=True,
            stdout=subprocess.PIPE,
        )
        (info.stdout or b"").decode("utf-8")
        try:
            loaded_page = WikiPage.load_locate(page)
            if not loaded_page:
                abort(404)
            return render_template(
                "wiki/adminwiki.html",
                page=page,
                links=WikiPage.getlinks().get(page, []),
                backlinks=backlinks,
                wordcount=len(loaded_page.body.split()),
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
        ) and (loc := WikiPage.locate(k)):
            WikiPage.reload_cache(loc)
    if loc := WikiPage.locate(path):
        WikiPage.reload_cache(loc)
    if "delete" in request.form:
        if n is None:
            flash("Invalid page name.", "error")
            return redirect(url_for("wiki.adminwiki", page=page))
        n_path = (WikiPage.wikipath() / n).with_suffix(".md")
        if n_path != path:
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
        if n is None:
            flash("Invalid target name.", "error")
            return redirect(url_for("wiki.adminwiki", page=page))
        with (WikiPage.wikipath() / "control").open("a+") as h:
            h.write(
                f"{session['user']} moved {path.relative_to(WikiPage.wikipath())} to {n}.\n",
            )
        subprocess.run(
            [
                Path("~").expanduser() / "bin/wikimove",
                path.relative_to(WikiPage.wikipath()).with_suffix(".md").as_posix(),
                n.with_suffix(".md").as_posix(),
            ],
        )
        flash(f"Moved {path.relative_to(WikiPage.wikipath())} to {n}.", "warning")
        WikiPage.updatewikicache()
        return redirect(url_for("wiki.adminwiki", page=n.as_posix()))
    abort(400)


@views.route("/wiki", methods=["GET", "POST"])
@views.route("/wiki/", methods=["GET", "POST"])
@views.route("/wiki/<path:page>", methods=["GET", "POST"])
def wikipage(page: str | None = None) -> str | WerkzeugResponse:
    """Render or redirect to a wiki page, or show the creation form if it does not exist."""
    raw = request.url.endswith("/raw")
    if raw and page:
        page = page[:-4]
    if page is None:
        page = request.form.get("n", None)
        if page is None:
            return wiki_index()
        if "edit" in request.form:
            return redirect(url_for("wiki.wikipage", page=page))
        if "administrate" in request.form:
            return redirect(url_for("wiki.adminwiki", page=page))
        abort(400)
    try:
        page_lower = page.lower()
        page_lower = page_lower.strip(".").replace(
            "/.",
            "/",
        )  # remove hidden directory-dots
        p = WikiPage.locate(page_lower)
        if p is None:
            raise FileNotFoundError
        if p.with_suffix("").as_posix() != page_lower:
            return redirect(url_for("wiki.wikipage", page=p.with_suffix("").as_posix()))
        loaded_page: WikiCharacterSheet[Any] | None = WikiCharacterSheet.load_locate(page_lower)
        if not loaded_page:
            raise FileNotFoundError
    except (DescriptiveError, FileNotFoundError) as e:
        if isinstance(e, DescriptiveError) and str(e.args[0]) != page + "not found in wiki.":
            raise
        if session.get("logged_in"):
            entry = dict(id=0, text="", tags="", author=session.get("user"))
            return render_template(
                "base/edit_entry.html",
                mode="wiki",
                wiki=page,
                entry=entry,
            )
        flash("That page doesn't exist. Log in to create it!")
        session["returnto"] = request.url
        return redirect(url_for("views.login"))
    if not raw:
        body = bleach.clean(loaded_page.body)
        body = nossi_markdown.process(body, page=page)
        return render_template(
            "wiki/wikipage.html",
            title=loaded_page.title,
            tags=loaded_page.tags,
            body=body,
            wiki=page,
            wiki_tags_json=wiki_tags_json,
            sheet_available=loaded_page.char is not None,
            css=(url_for("static", filename="wikimecha.css") if "endworld" in page else ""),
        )
    return WerkzeugResponse(loaded_page.body, 200, {"Content-Type": "text/plain; charset=utf-8"})


_checkbox_state: dict[str, bool] = {}


@views.route("/checkbox/<path:rest>")
def checkbox_toggle(rest: str) -> WerkzeugResponse:
    """Toggle a checkbox state and return the updated HTML."""
    key = rest
    current = _checkbox_state.get(key, False)
    _checkbox_state[key] = not current
    checked = "checked" if not current else ""
    return WerkzeugResponse(
        f'<input type="checkbox" {checked} ' f'hx-get="/checkbox/{key}" ' f'hx-swap="outerHTML" hx-trigger="change">',
        200,
        {"Content-Type": "text/html"},
    )


@views.route("/localmarkdown")
def localmarkdown_demo() -> str:
    """Render an auto-generated reference page for all local markdown tags."""
    sections = [
        "# Local Markdown Features\n\n" "Auto-generated reference documentation for all markdown tags.\n",
    ]
    placeholders: list[str] = []
    rendered_snippets: list[str] = []

    for tag in nossi_markdown.tags:
        cls = type(tag)
        doc = cls.__doc__
        if doc:
            doc_rendered = nossi_markdown.process(
                bleach.clean(doc),
                page="localmarkdown",
            )
            idx = len(placeholders)
            placeholder = f"<!--LOCALMD_{idx:04d}-->"
            sections.append(
                f"---\n\n## {cls.__name__}\n\n```\n{doc}\n```\n\n{placeholder}\n",
            )
            placeholders.append(placeholder)
            rendered_snippets.append(doc_rendered)

    body = "\n".join(sections)
    body = nossi_markdown.process(body, page="localmarkdown")

    for placeholder, snippet in zip(placeholders, rendered_snippets, strict=False):
        body = body.replace(placeholder, snippet)

    return render_template(
        "wiki/wikipage.html",
        title="Local Markdown Demo",
        tags=[],
        body=Markup(body),
        wiki="localmarkdown",
        sheet_available=False,
        css="",
    )


@views.route("/localmarkdown/raw")
def localmarkdown_raw() -> WerkzeugResponse:
    """Return raw markdown source for the local markdown reference page."""
    sections = [
        "# Local Markdown Features\n\n" "Auto-generated reference documentation for all markdown tags.\n",
    ]

    for tag in nossi_markdown.tags:
        cls = type(tag)
        doc = cls.__doc__
        if doc:
            sections.append(f"---\n\n## {cls.__name__}\n\n{doc}\n")

    return WerkzeugResponse("\n".join(sections), 200, {"Content-Type": "text/plain; charset=utf-8"})


@views.route("/wiki-tags.json")
def wiki_tags_json_endpoint() -> str:
    """Return all available markdown tags as JSON."""
    return json.dumps([tag.to_dict() for tag in nossi_markdown.tags])


@views.route("/tag-validate", methods=["POST"])
def tag_validate() -> WerkzeugResponse:
    """Validate a markdown tag specification and return its parsed content."""
    data = request.get_json()
    if not data:
        return WerkzeugResponse(json.dumps({"valid": False}), 400, {"Content-Type": "application/json"})
    tag_type = data.get("type", "")
    raw = data.get("raw", "")

    if tag_type in ("glitch", "invert"):
        return WerkzeugResponse(json.dumps({"valid": True, "content": raw}), 200, {"Content-Type": "application/json"})

    if tag_type == "transclude":
        page_match = re.search(
            r"\[!(?![tq]:)([^#|\]]+?)(?:#([^|\]]*?))?(?:\|([^\]]*?))?\]",
            raw,
        )
        if page_match:
            exists = WikiPage.locate(page_match.group(1).lower()) is not None
            data = json.dumps({"valid": exists, "content": page_match.group(2) or ""})
            return WerkzeugResponse(data, 200, content_type="application/json")
        return WerkzeugResponse(json.dumps({"valid": False}), 200, content_type="application/json")

    if tag_type == "linked-tooltip":
        spec_match = re.search(r"\[!t:([^\]]+?)\]", raw, re.IGNORECASE)
        if spec_match:
            spec = spec_match.group(1)
            if spec.startswith('"'):
                data = json.dumps({"valid": True, "content": spec})
                return WerkzeugResponse(data, 200, content_type="application/json")
            parts = spec.split("#", 1)
            exists = WikiPage.locate(parts[0].lower()) is not None
            data = json.dumps({"valid": exists, "content": spec})
            return WerkzeugResponse(data, 200, content_type="application/json")
        return WerkzeugResponse(json.dumps({"valid": False}), 200, content_type="application/json")

    if tag_type == "infolet":
        name_match = re.search(r"\[!q:(.*?)\]", raw, re.IGNORECASE)
        if name_match:
            data = json.dumps({"valid": True, "content": name_match.group(1)})
            return WerkzeugResponse(data, 200, content_type="application/json")
        return WerkzeugResponse(json.dumps({"valid": False}), 200, content_type="application/json")

    if tag_type == "wikilink":
        link_match = re.search(r"\[\[([^\]]+?)\]\]", raw)
        if link_match:
            inner = link_match.group(1)
            # Strip optional |text suffix
            pipe_idx = inner.find("|")
            page_ref = inner[:pipe_idx].strip() if pipe_idx >= 0 else inner.strip()
            # Extract page name (strip #heading if present)
            page_name = page_ref.split("#", 1)[0].strip()
            exists = WikiPage.locate(page_name.lower()) is not None
            data = json.dumps({"valid": exists, "content": page_ref})
            return WerkzeugResponse(data, 200, content_type="application/json")
        return WerkzeugResponse(json.dumps({"valid": False}), 200, content_type="application/json")

    return WerkzeugResponse(json.dumps({"valid": False}), 200, content_type="application/json")


@views.route("/render/<path:locator>")
def render_locator(locator: str) -> WerkzeugResponse:
    """Render a wiki page fragment (optionally with section anchor) as HTML."""
    from gamepack.Item import Item

    # Handle infolet lookups
    if locator.startswith("q:"):
        item_name = locator[2:]
        item = Item.item_cache.get(item_name)
        if item and item.description:
            rendered = nossi_markdown.process(item.description, locator)
            return WerkzeugResponse(
                rendered,
                200,
                {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"},
            )
        return WerkzeugResponse(
            f"<p>Item <strong>{item_name}</strong> not found</p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    raw = WikiPage.resolve_address(locator)
    if raw is None:
        parts = locator.split("#", 1)
        page_name = parts[0]
        if len(parts) > 1 and parts[1].strip():
            return WerkzeugResponse(
                f"<p>Heading <strong>{parts[1]}</strong> not found on page" f" <strong>{page_name}</strong></p>",
                200,
                {"Content-Type": "text/html; charset=utf-8"},
            )
        return WerkzeugResponse(
            f"<p>Page <strong>{page_name}</strong> not found</p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    rendered = nossi_markdown.process(raw, locator.split("#", 1)[0])
    return WerkzeugResponse(
        rendered,
        200,
        {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"},
    )


@views.route("/edit/<path:page>", methods=["GET", "POST"])
def editwiki(page: str) -> str | WerkzeugResponse:
    """Render the wiki editor for a page or process a save submission."""
    checklogin()
    page_lower = page.lower()
    try:
        p = WikiPage.locate(page_lower)
    except FileNotFoundError:
        # check if the page is eligible for creation
        if not (WikiPage.wikipath() / Path(page_lower).parent).exists():
            return redirect(url_for("wiki.wikipage", page=Path(page_lower).stem))
        (WikiPage.wikipath() / Path(page_lower)).touch()  # create
        p = WikiPage.locate(page_lower)
    if p is None:
        p = Path(page_lower).with_suffix(".md")
    if p.as_posix()[:-3] != page_lower:
        return redirect(url_for("wiki.wikipage", page=p.as_posix()[:-3]))
    if request.method == "GET":
        try:
            author = ""
            ident = (page,)
            try:
                loaded_page = WikiPage.load(p)
                if not loaded_page:
                    return wikipage(page)
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
                "base/edit_entry.html",
                mode="wiki",
                wiki=page,
                entry=entry,
            )
        except FileNotFoundError:
            flash("entry " + str(page) + " not found.")
    if request.method == "POST":
        if request.form.get("wiki", None) is not None:
            log.info(f"saving wiki file {request.form['wiki']}")
            try:
                loaded_page = WikiPage.load(p)
                if not loaded_page:
                    raise DescriptiveError("Page not found")
                loaded_page.title = request.form["title"]
                loaded_page.tags = set(request.form["tags"].split(" "))
                loaded_page.body = request.form["text"]
                loaded_page.links = mdlinks.findall(
                    markdown.markdown(request.form["text"]),
                )
                page_to_save = loaded_page
            except DescriptiveError:
                p_str = p.as_posix().lower()
                page_to_save = WikiPage(
                    title=request.form["title"],
                    tags=request.form["tags"].split(" "),
                    body=request.form["text"],
                    links=mdlinks.findall(markdown.markdown(request.form["text"])),
                    meta={},
                    file=WikiPage.wikipath() / p_str,
                )

            page_to_save.save_overwrite(session["user"])
            sync_clocks_with_db()
            flash(f"Saved {page_to_save.title.strip() or p}.")
        return redirect(url_for("wiki.wikipage", page=request.form.get("wiki", None)))
    return abort(405)


@views.route("/costcalc/all/<costs>/<penalty>")
@views.route("/costcalc/all/<costs>/<penalty>/<width>")
@views.route("/costcalc/all")
def ddos(costs: str = "0, 15, 35, 60, 100", penalty: str = "0, 0, 0, 50, 100", width: int = 3) -> WerkzeugResponse:
    """Calculate and cache FenCharacter cost tables for all levels up to a given cost/penalty."""
    # filter costs and penalty to not include path traversal
    costs = ",".join(str(int(x)) for x in costs.split(",") if int(x) >= 0)
    penalty = ",".join(str(int(x)) for x in penalty.split(",") if int(x) >= 0)
    p = Path(costs + "-" + penalty + ".result")
    # noinspection PyBroadException
    try:
        if p.exists():
            with open(p) as f:
                return WerkzeugResponse(f.read(), 200, {"Content-Type": "text/plain; charset=utf-8"})
        start = time.time()
        if int(costs.split(",")[-1]) * 3 + sum(int(x) for x in penalty.split(",")) * 3 > 10000:
            raise AttributeError("just too large of a space")
        with open(p, "w") as f:
            res: list[Any] = []
            i = 0
            while i == 0 or not all(all(int(x) >= 5 for x in y if x) for y in res[-1][1]):
                r = FenCharacter.cost_calc(str(i), width)
                log.debug(f"Fencalc {i} {res}")
                if i == 0 or r != res[-1][1]:
                    res.append([str(i), r])
                if time.time() - start > 30:
                    raise TimeoutError
                i += 1
            for k, v in res:
                line = f"{'      '.join(', '.join(str(y) for y in x) for x in v)}"
                f.write(f" {k: <4}: {line} \n")
        return WerkzeugResponse("Reload please", 200, {"Content-Type": "text/plain; charset=utf-8"})
    except Exception:
        with open(p, "w") as f:
            f.write("an error has previously occured and this request is blocked")
            return WerkzeugResponse(
                "error, this request is now blocked",
                200,
                {"Content-Type": "text/plain; charset=utf-8"},
            )


@views.route("/costcalc/<inputstring>/<width>")
@views.route("/costcalc/<inputstring>")
def fen_calc(inputstring: str, width: int = 3) -> WerkzeugResponse:
    """Calculate FenCharacter costs for a given input string and return plain text results."""
    res = FenCharacter.cost_calc(inputstring, width)
    if isinstance(res, int):
        return WerkzeugResponse(str(res), 200, {"Content-Type": "text/plain; charset=utf-8"})
    return WerkzeugResponse(
        "\n".join(", ".join(str(y) for y in line) for line in res),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@views.route("/search", methods=["GET"])
def searchwiki() -> str | WerkzeugResponse:
    """Search wiki pages by title, tag, and body text, returning rendered results."""
    pre = 30
    pos = 30
    key = request.args.get("s", "")
    key = key.lower()
    if not key.strip():
        return WerkzeugResponse(json.dumps([]), 200, {"Content-Type": "application/json"})
    matches = []
    length = len(key)
    for w in WikiPage.wikindex():
        loaded_page = WikiPage.load(w)
        if not loaded_page:
            continue
        w_rel = w.relative_to(WikiPage.wikipath()).with_suffix("")
        if key in loaded_page.title.lower():
            matches.append((w_rel, loaded_page.title, "title"))
        for tag in loaded_page.tags:
            if key in tag.lower():
                matches.append((w_rel, loaded_page.title, f"tag: {tag}"))
        p = 0
        while loaded_page.body[p:]:
            m = loaded_page.body[p:].lower().find(key)
            if m == -1:
                break
            matches.append(
                (
                    w_rel,
                    loaded_page.title,
                    f"{loaded_page.body[max(p + m - pre, 0) : p + m + pos + length]}",
                ),
            )
            p += m + 1

    return render_template(
        "wiki/search_results.html",
        results=matches,
        start=pre,
        end=pre + length,
    )


def live_edit_get(formdata: dict[str, Any]) -> dict[str, Any]:
    """Retrieve wiki page content for live editing based on type and path.

    Args:
        formdata: Dict with type, context, and path keys.

    Returns:
        Response dict with data and type fields.
    """
    t = parse.unquote(formdata.get("type", "text"))
    loaded_page = WikiPage.load_locate(formdata["context"])
    if not loaded_page:
        return {"data": "", "type": "error"}
    res: str = loaded_page.body
    if t == "tiptap":
        return {"data": res, "type": "tiptap"}
    a = formdata.get("path", [])
    a = [parse.unquote(x) for x in a if x]
    if not a:
        a = [formdata["percentage"]]
    if t == "text":
        return live_edit_get_text(res, a)
    if t == "table":
        return {**live_edit_get_table(res, a), "path": a}
    return {"data": "", "type": "error"}


def live_edit_get_text(res: str, a: list[str]) -> dict[str, Any]:
    """Extract text content from a wiki page for live editing.

    Args:
        res: Full wiki page body.
        a: Path segments or percentage string.

    Returns:
        Dict with extracted text data.
    """
    if m := re.match(r"(0\.?\d*|1)", a[0]):  # percentage request
        ratio = float(m.group(1))
        pos = int(len(res) * ratio)
        return {"data": res[max(0, pos - 200) : pos + 500]}
    mdo = MDObj.from_md(res)
    for step in a:
        mdo = mdo.children[step]
    return {"data": mdo.to_md(), "type": "text"}


def live_edit_get_table(res: str, a: list[str]) -> dict[str, Any]:
    """Extract table data from a wiki page for live editing.

    Args:
        res: Full wiki page body.
        a: Path segments to the table node.

    Returns:
        Dict with table data and type.
    """
    mdo = MDObj.from_md(res)
    for step in a:
        mdo = mdo.children[step]
    if not mdo.tables:
        return {"data": "", "type": "error"}

    return {"data": mdo.tables[0].to_simple(), "type": "table"}


def live_edit_write(formdata: dict[str, Any], context: str | None) -> None:
    """Dispatch live edit write operation to the appropriate handler based on type.

    Args:
        formdata: Dict with type, original, new, and path keys.
        context: Wiki page context identifier.
    """
    if formdata["type"] == "text":
        return live_edit_write_text(formdata, context)
    if formdata["type"] == "table":
        return live_edit_write_table(formdata, context)
    if formdata["type"] == "tiptap":
        return live_edit_write_tiptap(formdata, context)


def live_edit_write_text(formdata: dict[str, Any], context: str | None) -> None:
    """Apply a text replacement to a wiki page.

    Args:
        formdata: Dict with original and new text.
        context: Wiki page context identifier.
    """
    old = formdata["original"].replace("\r\n", "\n")
    new = formdata["new"].replace("\r\n", "\n")
    if old != new:
        loc = WikiPage.locate(context)
        if not loc:
            return
        log.info(f"livereplacing {loc}")
        page = WikiPage.load(loc)
        if not page:
            return
        page.body = page.body.replace("\r\n", "\n")
        if old not in page.body:
            if old[:-1] in page.body:
                old = old[:-1]
            else:
                log.error(f"live replace didn't match {loc}")
        page.body = page.body.replace(old, new, 1)
        page.save_overwrite(str(session.get("user") or ""))
    else:
        log.info(f"rejected empty replace {context}")


def live_edit_write_tiptap(formdata: dict[str, Any], context: str | None) -> None:
    """Save a full TipTap editor body to a wiki page.

    Args:
        formdata: Dict with body key containing the full page content.
        context: Wiki page context identifier.
    """
    body = formdata["body"].replace("\r\n", "\n")
    if not body.strip():
        log.warning("tiptap save with empty body — rejected")
        return
    loc = WikiPage.locate(context)
    if not loc:
        return
    log.info(f"tiptap saving {loc}")
    page = WikiPage.load(loc)
    if not page:
        return
    page.body = body
    page.save_overwrite(str(session.get("user") or ""))


def live_edit_write_table(formdata: dict[str, Any], context: str | None) -> None:
    """Apply table cell edits to a wiki page.

    Args:
        formdata: Dict with path, header_, and table_ keys.
        context: Wiki page context identifier.
    """
    loc = WikiPage.locate(context)
    if not loc:
        return
    page = WikiPage.load(loc)
    if not page:
        return
    md = page.md()
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
    md_text = md.to_md()
    if md_text != page.body:
        page.body = md_text
        page.save_overwrite(str(session.get("user") or ""))


@views.route("/live_edit", methods=["POST"])
def live_edit() -> WerkzeugResponse:
    """Handle live edit AJAX requests — load modal data or save changes."""
    # loading edit modal is accomplished by posting relevant context data and receiving the reply
    if request.is_json and (formdata := request.get_json()):
        return WerkzeugResponse(json.dumps(live_edit_get(formdata)), 200, {"Content-Type": "application/json"})
    # else, form was transmitted
    formdata = request.form
    context: str | None = formdata.get("context", None)
    wiki = not context
    context = context or formdata.get("wiki", None)
    sheet_owner = Config.users_with_option_value("character_sheet", context or "")
    if sheet_owner:
        sheet_owner = sheet_owner[0][0]
    if (not sheet_owner) or session.get("user") == sheet_owner:
        live_edit_write(formdata, context)
    else:
        flash("Unauthorized, so ... no.", "error")
    if not wiki:
        return redirect(url_for("sheets.sheet", c=formdata["context"]))
    return redirect(url_for("wiki.wikipage", page=context))


@views.route("/q/<a>")
@views.route("/q/<a>/raw")
@views.route("/specific/<a>")
@views.route("/specific/<path:a>")
def specific(a: str, parse_md: bool | None = None) -> str | WerkzeugResponse:
    """Render a specific section or fragment of a wiki page by colon-separated path."""
    parse_md = not request.url.endswith("/raw") if parse_md is None else parse_md
    a = a.removesuffix("/raw")
    a = a.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
    parts: list[str] = a.split(":")
    if parts[-1] == "-":
        parts = parts[:-1]
        hide_headline = 1
    else:
        hide_headline = 0

    loaded_page = WikiPage.load_locate(parts[0])
    if not loaded_page:
        return WerkzeugResponse("not found", 404)
    article: str = loaded_page.body
    for seek in parts[1:]:
        article = traverse_md(article, seek)
    if not article:
        return WerkzeugResponse("not found", 404)
    article = article[article.find("\n") * hide_headline :]
    if parse_md:
        return Markup(nossi_markdown.process(article, page=parts[0]))
    return article


def weaponadd(weapon_damage_array: list[list[int]], b: list[int], ind: int = 0) -> list[list[int]]:
    """Add weapon damage arrays element-wise, clamping to zero.

    Args:
        weapon_damage_array: List of weapon damage values.
        b: List of bonus values to add.
        ind: Index within each damage entry to modify.

    Returns:
        New list of damage arrays with the bonus applied.
    """
    if len(weapon_damage_array) != len(b):
        raise DescriptiveError("Length mismatch!", weapon_damage_array, b)
    c = []
    for i, w in enumerate(weapon_damage_array):
        c.append(([*w, 0, 0])[:2])
        c[-1][ind] = max(c[-1][ind] + b[i], 0)
    return c


def lowercase_access(d: dict[str, Any], k: str) -> Any:
    """Look up a key in a dict case-insensitively.

    Args:
        d: Dictionary to search.
        k: Key to look up (case-insensitive).

    Returns:
        The value for the matching key.

    Raises:
        DescriptiveError: If the key is not found.
    """
    data = {k.lower(): v for k, v in d.items()}
    res = data.get(k.lower())
    if res is None:
        raise DescriptiveError(
            k.lower() + " does not exist in " + " ".join(data.keys()),
        )
    return res
