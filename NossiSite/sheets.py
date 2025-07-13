import html
import json
import time
from pathlib import Path

from flask import (
    render_template,
    Blueprint,
    render_template_string,
    request,
    session,
    redirect,
    url_for,
    flash,
    Response,
)
from markupsafe import Markup

from NossiPack.LocalMarkdown import LocalMarkdown
from NossiPack.User import User
from NossiSite.base_ext import decode_id
from NossiSite.socks import (
    generate_clock,
    generate_line,
    broadcast_elements,
    BroadcastElement,
    broadcast,
)
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import MDObj
from gamepack.PBTACharacter import PBTACharacter
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage

views = Blueprint("sheets", __name__)
ordinals = [
    "primary",
    "secondary",
    "tertiary",
    "quaternary",
    "quinary",
    "senary",
    "septenary",
    "octonary",
    "nonary",
    "denary",
]


@views.route("/ew/<path:c>")
def ewsheet(c):
    try:
        char = WikiCharacterSheet.load_locate(c)
        return render_template("sheets/ewsheet.html", character=char.char, c=c)
    except DescriptiveError:
        return render_template("sheets/chargen.html", charname=Path(c).stem)


@views.route("/skills/<system>/<heading>")
def get_skills(system, heading):
    print("received skill request for ", system, heading)

    def flatten_skills(node):
        if hasattr(node, "children") and node.children:
            return [
                item
                for child in node.children.values()
                for item in flatten_skills(child)
            ]
        return [node]

    page = system + "/descriptions/" + heading.lower() + "skills"
    skills = WikiPage.load_locate(page).md()
    skills = flatten_skills(skills)
    skills = {
        x.header: html.escape(LocalMarkdown.process(x.plaintext, page)) for x in skills
    }
    options = "\n".join(f'<option value="{s}" data-desc="{skills[s]}">' for s in skills)
    options = f'<datalist id="{heading}_skills">{options}</datalist>'
    return Response(options, mimetype="text/html")


@views.route("/chargen/reset", methods=["GET"])
@views.route("/chargen", methods=["GET"])
def chargen():
    username = session.get("user", "")
    if not username:
        return redirect(url_for("views.login"))
    if "character_gen" not in session or request.path.endswith("/reset"):
        session["character_gen"] = {"stage": 0}
        return redirect(url_for("sheets.chargen"))
    else:
        print("request to chargen:", session["character_gen"])
    return render_template("sheets/chargen.html")


@views.route("/chargen/htmx", methods=["GET"])
def chargen_htmx():
    username = session.get("user", "")
    if not username:
        return redirect(url_for("login"))
    match int(session.get("character_gen", {}).get("stage", 0)):
        case 0:
            return render_template(
                "sheets/chargen_htmx/fen_gen_0.html",
                name=session.get("character_gen", {}).get("name", ""),
                categories="Physical, Mental, Social, Ability, Special",
                points="12, 10, 8, 6, 4",
            )
        case 1:
            items = [
                x.strip().strip(",")
                for x in session["character_gen"].get("categories", "error").split(", ")
                if x
            ]
            points = [
                x.strip().strip(",")
                for x in session["character_gen"].get("points", "error").split(", ")
                if x
            ]
            return render_template(
                "sheets/chargen_htmx/fen_gen_1.html",
                ordinals=ordinals,
                items=items,
                points=points,
            )
        case 2:
            order: list[str] = session["character_gen"].get("order", "").split(",")
            points = session["character_gen"].get("points", "").split(",")
            categories = []
            for c in session["character_gen"]["categories"].split(","):
                c = c.strip()
                i = order.index(c)
                p = points[i]
                fields = []
                try:
                    for k, v in (
                        session["character_gen"].get("category_" + c, {}).items()
                    ):
                        fields.append([k, v])
                except AttributeError:
                    fields = [["", 0]]

                categories.append({"heading": c, "points": p, "fields": fields})

            return render_template(
                "sheets/chargen_htmx/fen_gen_2.html", categories=categories, system="ew"
            )
        case 3:
            return render_template(
                "sheets/chargen_htmx/fen_gen_3.html",
                character_details=[
                    "archetype",
                    "background",
                    "age",
                    "appearance",
                    "alias",
                    "player",
                    "vice",
                    "category",
                ],
                prefill=session["character_gen"].get("desc", {}),
            )
        case _:
            session["character_gen"]["stage"] = 1
            return (
                "",
                204,
                {
                    "HX-Redirect": "/edit_from_chargen/"
                    + session["character_gen"]["name"]
                },
            )

    print("no stage found:  " + session.get("character_gen", {}).get("stage", "0"))
    return str(session.get("character_gen", 0))


@views.route("/edit_from_chargen/<name>")
def edit_from_chargen(name):
    path = Path("character") / name
    data = session["character_gen"]
    try:
        p = WikiPage.load(path)
    except DescriptiveError:
        p = WikiPage(data["name"], [], "", [], {})
    c = FenCharacter.from_md(p.body)
    for cat in data["categories"].split(","):
        cat = cat.strip()
        c.Categories[cat] = data["category_" + cat]
    for k, v in data.get("desc", {}).items():
        c.Character[k] = v
    c.Character["name"] = session["character_gen"]["name"]
    p.body = c.to_md()
    entry = dict(
        author=session["user"],
        id=path,
        title=p.title or session["character_gen"]["name"],
        tags=" ".join(p.tags),
        text=p.body,
    )
    return render_template("base/edit_entry.html", mode="wiki", wiki=path, entry=entry)


@views.route("/add-detail-row")
def add_detail_row():
    return render_template("sheets/chargen_htmx/detail_row.html")


@views.route("/chargen/", methods=["POST"])
def handle_chargen():
    data = {k: v for k, v in list(request.form.lists())}
    if "csrf_token" in data:
        data.pop("csrf_token")
    # print("received:", data)
    for k, v in data.items():
        if len(v) != 1:
            if k not in ["key", "value"]:
                raise ValueError("only keyvalue, not", k)
            if k == "key":
                session["character_gen"]["desc"] = session["character_gen"].get(
                    "desc", {}
                )
                for i, key in enumerate(v):
                    if not key:
                        continue
                    session["character_gen"]["desc"][key] = data["value"][i]
            continue
        else:
            v = v[0]

        if k.startswith("category_"):
            v = json.loads(v)
        session["character_gen"][k] = v
        # print("setting", k, v)
        session.modified = True
    return chargen_htmx()


@views.route("/pbta/<path:c>")
def pbtasheet(c):
    char = WikiCharacterSheet.load_locate(c)
    return render_template("sheets/pbtasheet.html", character=char.char, c=c)


@views.route("/preview_move/<context>/<name>")
def preview_move(context, name):
    page = WikiPage.load_locate(context)  # Load the wiki page
    md_obj = MDObj.from_md(page.body)  # Convert to Markdown object
    result = md_obj.search_children(name)  # Search for the name
    if not result:
        page = WikiPage.load_locate("pbtamoves")  # Load the wiki page
        md_obj = MDObj.from_md(page.body)  # Convert to Markdown object
        result = md_obj.search_children(name)  # Search for the name
    if not result:
        return "Not Found"
    result.level = None
    preview_content = Markup(result.to_md(False))

    return render_template_string(
        "<a href=/wiki/{{c|urlencode }}#{{ name|urlencode }}><b>{{header}}:</b> {{ preview_content }}</a>",
        c=page.file.stem,
        name=name,
        preview_content=preview_content,
        header=result.header.title(),
    )


@views.route("/checkbox/<name>/<path:context>", methods=["GET", "POST"])
def checkbox(context, name):
    page = WikiPage.load_locate(context)
    #    username = session.get("user", "")
    md = page.md()
    checklists = md.search_checklist_with_path(name)
    for path in checklists:
        current = md
        for p in path:
            current = current.children[p]
        for li in md.checklists:
            val = li.get(name)
            if val is not None:
                checked = "checked" if val else ""
                text = li.get(name, {}).get("text", name)
                return make_checkbox(context, text, checked)


def make_checkbox(context, name, checked):
    return render_template_string(
        """<input type="checkbox"
           class="checkbox{{cd}}"
           id="checkbox-{{ name }}"
           name="{{ name }}"
           {% if checked %}checked{% endif %}
           hx-post="/update_move/{{c|urlencode}}/{{name|urlencode}}"
           hx-trigger="change"
           hx-swap="outerHTML"
           aria-checked="{{ 'true' if checked else 'false' }}"
           role="checkbox"
           hx-include="#csrf"
           aria-labelledby="checkbox-{{ name }}-label">""",
        name=name,
        c=context,
        checked=checked,
        cd=" cooldown" if request.method == "POST" else "",
    )


@views.route("/update_move/<context>/<name>", methods=["GET", "POST"])
def update_move(context, name):
    sheet = WikiCharacterSheet.load_locate(context)
    username = session.get("user", "")
    assert isinstance(sheet.char, PBTACharacter)
    res = False
    if sheet.tagcheck(username):
        for move in sheet.char.moves:
            if move[0] == name:
                if request.method == "POST":
                    move[1] = not move[1]
                res = move[1]
            break
        sheet.body = sheet.char.to_md()
        sheet.save_low_prio(f"moves updated by {username}")
    return make_checkbox(context, name, res)


@views.route("/pbta-update-notes", methods=["POST"])
def update_notes():
    context = request.args["c"]
    username = session.get("user", "")

    notes = request.form.get("notes")  # Ensure your textarea has name="notes"

    sheet = WikiCharacterSheet.load_locate(context)
    if sheet.tagcheck(username):
        sheet.char.notes = notes
        sheet.body = sheet.char.to_md()
        sheet.save_low_prio(f"notes updated by {username}")
    return notes


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
    page = decode_id(page)
    name = decode_id(name)
    username = session.get("user", "")
    if username:
        if request.path.startswith("/changeline"):
            element_type = "line"
        else:
            element_type = "round"
        broadcast_elements.append(
            BroadcastElement(name, page, "wiki", element_type, False)
        )
        WikiPage.load_locate(page).change_clock(name, int(delta)).save_low_prio("clock")
        broadcast.set()
    return "", 204


@views.route("/change_sheet_line/<name>/<page>/<delta>")
@views.route("/change_sheet_clock/<name>/<page>/<delta>")
def change_sheet_clock(name: str, page: str, delta: str):
    page = decode_id(page)
    username = session.get("user", "")
    name = decode_id(name)
    if username:
        if request.path.startswith("/change_sheet_line"):
            element_type = "line"
        else:
            element_type = "round"
        broadcast_elements.append(
            BroadcastElement(name, page, "sheet", element_type, False)
        )
        charpage = WikiCharacterSheet.load_locate(page)
        if charpage.tagcheck(username):
            char: PBTACharacter = charpage.char
            if name.startswith("item-"):
                for item in char.inventory:
                    if item.name == name[5:]:
                        item.count += int(delta)
                        break
            else:
                char.health[name.title()][char.current_headings[0].title()] = (
                    char.health_get(name)[0] + int(delta)
                )
            charpage.save_low_prio(f"active element used by {username}")
            broadcast.set()
            charpage.body = char.to_md()
    return "", 204


@views.route("/fensheet/<path:c>")
def fensheet(c):
    username = session.get("user", "")
    try:
        time0 = time.time()
        char = WikiCharacterSheet.load_locate(c)
        if char is None:
            return redirect(url_for("wiki.tagsearch", tag="character"))
        u = User(username).configs()
        time1 = time.time()
        charsh = u.get("character_sheet", None)
        body = render_template(
            "sheets/fensheet.html",
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


def infolet_filler(context):
    def wrap(s):
        return LocalMarkdown.fill_infolet(s, context)

    return wrap


def infolet_extractor(x):
    m = LocalMarkdown.infolet_re.match(str(x))
    if not m:
        return str(x)
    return m.group("name")
