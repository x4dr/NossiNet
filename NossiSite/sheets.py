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
    jsonify,
)
from markupsafe import Markup

from NossiPack.LocalMarkdown import LocalMarkdown
from NossiPack.User import User, Config
from NossiSite.base_ext import decode_id
from NossiSite.socks import (
    generate_clock,
    generate_line,
    broadcast_elements,
    BroadcastElement,
    broadcast,
)
from gamepack.Dice import DescriptiveError
from gamepack.EWCharacter import EWCharacter
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import MDObj, MDTable
from gamepack.PBTACharacter import PBTACharacter
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage

lm = LocalMarkdown()
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


@views.route("/skills/<system>/<heading>")
def get_skills(system, heading):
    print("received skill request for", system, heading)
    if system == "context":
        system = session["character_gen"]["system"]
        print("context:", system)

    def flatten_skills(node):
        if hasattr(node, "children") and node.children:
            return [
                item
                for child in node.children.values()
                for item in flatten_skills(child)
            ]
        return [node]

    if system == "endworld" and heading.lower() == "detail":
        return jsonify(
            {
                "archetype": "the core role or narrative type your character embodies",
                "background": "a term/less than a sentence summary of your character's history or origin",
                "age": "either how old you look or how long you have been alive",
                "appearance": "a quick description",
                "alias": "any nickname, street name?",
                "player": "you",
                "vice": "for roleplay purposes",
                "category": "see the wiki :)",
            }
        )

    page = f"{system}/descriptions/{heading.lower()}skills"
    skills = flatten_skills(WikiPage.load_locate(page).md())
    result = {x.header: lm.process(x.plaintext, page) for x in skills}
    return jsonify(result)


def get_attributes(system, heading):
    page = system + "/descriptions/attributes"
    md = WikiPage.load_locate(page).md()
    attributes = md.children.get("Attributes")
    attributes = (attributes.tables or [MDTable([], [])])[0]
    return attributes.column(heading, ["", "", ""])


@views.route("/chargen/reset", methods=["GET"])
@views.route("/chargen/", methods=["GET"])
def chargen():
    username = session.get("user", "")
    if not username:
        session["returnto"] = url_for("sheets.chargen")
        return redirect(url_for("views.login"))
    if "character_gen" not in session or request.path.endswith("/reset"):
        session["character_gen"] = {"stage": "start"}
        return redirect(url_for("sheets.chargen"))
    else:
        print("request to chargen:", session["character_gen"])
    return render_template("sheets/chargen.html")


stage_handlers = {}


def charactergen_stage(stage, system=None):
    def decorator(func):
        stage_handlers[stage] = func
        return func

    return decorator


@views.route("/chargen/htmx", methods=["GET"])
def chargen_htmx():
    username = session.get("user", "")
    if not username:
        session["returnto"] = url_for("sheets.chargen")
        return redirect(url_for("login"))

    gen = session.setdefault("character_gen", {})
    gen["name"] = gen.get("name", "").rsplit("/")[-1]
    stage = gen.get("stage", "start")
    handler = stage_handlers.get(stage, stage_handlers["?"])
    return handler(gen)


@charactergen_stage("start")
def chargen_start(state: dict):
    return render_template(
        "sheets/chargen_htmx/char_gen_start.html",
        name=state.get("name", ""),
        categories="Physical, Mental, Social, Ability, Special",
        points="12, 10, 8, 6, 4",
        system=state.get("system"),
    )


@charactergen_stage("prio")
def chargen_priority(state: dict):
    try:
        items = [x.strip() for x in state["order"].split(",")]
    except KeyError:
        items = [
            x.strip().strip(",")
            for x in state.get("categories", "error").split(", ")
            if x
        ]
    points = [
        x.strip().strip(",") for x in state.get("points", "error").split(", ") if x
    ]
    return render_template(
        "sheets/chargen_htmx/char_gen_prio.html",
        ordinals=ordinals,
        items=items,
        points=points,
        system=state.get("system"),
    )


@charactergen_stage("core")
def chargen_corestats(state: dict):
    heading = "Core Stats"
    attributes = ["Resistance", "Fate", "Affinity"]
    attributes = [
        (x, int(state.get("attributes", {}).get(heading, {}).get(x, 1)))
        for x in attributes
    ]
    return render_template(
        "sheets/chargen_htmx/char_gen_core.html",
        heading=heading,
        attributes=attributes,
        points=10,
        system=state.get("system"),
    )


@charactergen_stage("skills")
def chargen_skills(state: dict):
    order: list[str] = state.get("order", "").split(",")
    points = state.get("points", "").split(",")
    categories = []
    for c in state["categories"].split(","):
        c = c.strip()
        i = order.index(c)
        p = points[i]
        fields = []
        try:
            for k, v in state.get("skills", {}).get(c, {}).items():
                fields.append([k, int(v)])
        except AttributeError:
            fields = [["", 0]]

        categories.append({"heading": c, "points": p, "fields": fields})

    return render_template(
        "sheets/chargen_htmx/char_gen_skills.html",
        categories=categories,
        system="endworld",
    )


@charactergen_stage("attributes")
def chargen_attributes(state: dict):
    categories = []
    for c in state["categories"].split(","):
        c = c.strip()
        p = sum(int(x) for x in state.get("skills", {}).get(c, {}).values())
        p = 1 + (p // 2)
        attributes = get_attributes("endworld", c)
        attributes = [
            (x, int(state.get("attributes", {}).get(c, {}).get(x, 1)))
            for x in attributes
        ]
        categories.append({"heading": c, "points": p, "attributes": attributes})
    return render_template(
        "sheets/chargen_htmx/char_gen_attributes.html",
        categories=categories,
        system="endworld",
    )


@charactergen_stage("descriptions")
def chargen_descriptions(state: dict):
    return render_template(
        "sheets/chargen_htmx/char_gen_desc.html",
        prefill=state.get("desc", {}),
    )


@charactergen_stage("end")
def chargen_end(state: dict):
    return render_template("sheets/chargen_htmx/char_gen_end.html", data=state)


@charactergen_stage("?")
def chardgen_htmx(state: dict):
    state["stage"] = "start"
    session.modified = True
    return (
        "",
        204,
        {"HX-Redirect": "/edit_from_chargen/" + state["name"].lower().replace(" ", "")},
    )


@views.route("/edit_from_chargen/<name>")
def edit_from_chargen(name):
    path = Path("character") / name
    gen = session["character_gen"]
    try:
        p = WikiPage.load(path)
    except DescriptiveError:
        p = WikiPage(gen["name"], [], "", [], {})
    c = FenCharacter.from_md(p.body)
    default_headings = {
        "Attributes": {"Attribute": "Value"},
        "Skills": {"Skill": "Value"},
    }
    category_headings = {}
    for cat in gen["categories"].split(","):
        cat = cat.strip()
        c.Categories[cat] = {
            "Attributes": gen["attributes"].get(cat, {}),
            "Skills": gen["skills"].get(cat, {}),
        }
        category_headings[cat] = default_headings
    c.Character["name"] = gen["name"]

    c.headings_used = {"categories": category_headings}
    for k, v in gen.get("desc", {}).items():
        c.Character[k] = v
    if gen["system"] == "endworld":
        for k, v in gen["attributes"]["Core Stats"].items():
            c.Character[k] = v
    p.body = c.to_md()
    p.tags.add(gen.get("system", "endworld"))
    p.tags.add(session["user"])
    p.tags.add("Character")
    entry = dict(
        author=session["user"],
        id=path,
        title=p.title or gen["name"],
        tags=" ".join(p.tags),
        text=p.body,
    )
    Config.save(session["user"], "character_sheet", path.as_posix())
    return render_template("base/edit_entry.html", mode="wiki", wiki=path, entry=entry)


@views.route("/add-detail-row")
def add_detail_row():
    return render_template("sheets/chargen_htmx/detail_row.html")


@views.route("/chargen/", methods=["POST"])
def handle_chargen():
    data = {k: v for k, v in list(request.form.lists())}
    if "csrf_token" in data:
        data.pop("csrf_token")
    print("received:", data)
    gen = session["character_gen"]
    for k, v in data.items():
        if len(v) != 1:
            if k not in ["key", "value", "skill", "attribute"]:
                raise ValueError("only keyvalue, not", k)
            if k == "key":
                gen["desc"] = gen.get("desc", {})
                for i, key in enumerate(v):
                    if not key:
                        continue
                    gen["desc"][key] = data["value"][i]
            if k in ("skill", "attribute"):
                section = gen.setdefault(k + "s", {})
                heading = data["heading"][0]
                section[heading] = {}
                section_for_heading = section[heading]

                for i, key in enumerate(v):
                    if not key:
                        continue
                    section_for_heading[key] = data["value"][i]
            continue
        else:
            v = v[0]
        gen[k] = v
        print("setting", k, v)
        session.modified = True
    print(gen)
    return chargen_htmx()


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
    s = WikiCharacterSheet.load_locate(context)
    username = session.get("user", "")
    assert isinstance(s.char, PBTACharacter)
    res = False
    if s.tagcheck(username):
        for move in s.char.moves:
            if move[0] == name:
                if request.method == "POST":
                    move[1] = not move[1]
                res = move[1]
            break
        s.body = s.char.to_md()
        s.save_low_prio(f"moves updated by {username}")
    return make_checkbox(context, name, res)


@views.route("/pbta-update-notes", methods=["POST"])
def update_notes():
    context = request.args["c"]
    username = session.get("user", "")

    notes = request.form.get("notes")  # Ensure your textarea has name="notes"

    s = WikiCharacterSheet.load_locate(context)
    if s.tagcheck(username):
        s.char.notes = notes
        s.body = s.char.to_md()
        s.save_low_prio(f"notes updated by {username}")
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


@views.route("/sheet/<path:c>")
def sheet(c):
    try:
        if s := WikiCharacterSheet.load_locate(c):
            return s.render()
        flash("Error: not found. Create Character?")
        session.setdefault("character_gen", {})["stage"] = "start"
        session["character_gen"]["name"] = c
        return redirect(url_for("sheets.chargen"))
    except DescriptiveError as e:
        flash("Error with character sheet:\n" + e.args[0])
        return redirect(url_for("wiki.wikipage", page=c))


@views.route("/pbta/<path:c>")
@views.route("/fensheet/<path:c>")
def oldsheet(c):
    return redirect(url_for("sheets.sheet", c=c))


def infolet_filler(context):
    def wrap(s):
        return lm.fill_infolet(s, context)

    return wrap


def infolet_extractor(x):
    m = lm.infolet_re.match(str(x))
    if not m:
        return str(x)
    return m.group("name")


@WikiCharacterSheet.renderer(EWCharacter)
@WikiCharacterSheet.renderer(FenCharacter)
def fensheet_render(self: WikiCharacterSheet):
    if self is None:
        return redirect(url_for("wiki.tagsearch", tag="character"))

    username = session.get("user", "")
    u = User(username).configs()
    charsh = u.get("character_sheet", None)
    path = self.file.relative_to(self.wikipath())
    return render_template(
        "sheets/fensheet.html",
        character=self.char,
        context=path,
        userconf=u,
        infolet=infolet_filler(path),
        md=lambda x: lm.process(
            x, page=self.file.relative_to(WikiPage.wikipath()).as_posix()
        ),
        extract=infolet_extractor,
        owner=(charsh if WikiPage.locate(path) == WikiPage.locate(charsh) else ""),
    )


@WikiCharacterSheet.renderer(PBTACharacter)
def pbta_render(self: WikiCharacterSheet):
    path = self.file.relative_to(self.wikipath())
    return render_template(
        "sheets/pbtasheet.html", character=self.char, c=path.as_posix()
    )
