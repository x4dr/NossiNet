from collections import defaultdict
from pathlib import Path
from typing import cast, List, Tuple, Any

import requests
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
    abort,
)
from markupsafe import Markup

from NossiPack.LocalMarkdown import LocalMarkdown
from NossiPack.User import Config, Userlist
from NossiSite import chat
from NossiSite.base_ext import decode_id
from NossiSite.helpers import checklogin
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
from gamepack.endworld import Mecha
from NossiSite.renderers import render_sheet

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


def system_map(selection):
    if selection in ["offensive", "defensive", "support"]:
        selection = "generic"

    return f"sheets/mechasheet_htmx/{selection}.html"


def system_map_classic(selection):
    if selection in ["offensive", "defensive", "support"]:
        selection = "generic"

    return f"sheets/mechsystems_classic/{selection}.html"


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
    p = WikiPage.load_locate(page)
    if not p:
        return jsonify({})
    skills = flatten_skills(p.md())
    result = {x.header: lm.process(x.plaintext, page) for x in skills}
    return jsonify(result)


def get_attributes(system, heading):
    page = system + "/descriptions/attributes"
    p = WikiPage.load_locate(page)
    if not p:
        return ["", "", ""]
    md = p.md()
    attributes = md.children.get("Attributes")
    if attributes and attributes.tables:
        attributes_table = attributes.tables[0]
        return attributes_table.column(heading, ["", "", ""])
    return ["", "", ""]


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


def charactergen_stage(stage):
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
    p = WikiPage.load(path)
    if not p:
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


def generate_meter_segments(fills, colors, total, names):
    segments = []
    bottom = 0
    for i, fill in enumerate(fills):
        color = colors[i % len(colors)]
        percent = (100 * fill) / total
        offset = (100 * bottom) / total
        if offset + percent > 100:
            percent = 100 - offset
            color = "var(--warn-color)"
        segments.append(
            {"fill": percent, "color": color, "offset": offset, "name": names[i]}
        )
        bottom += fill
    return segments


# Unused for now
def generate_heat_segments(mech: Mecha):
    sinks = []
    fluxmax = mech.fluxmax()
    for sys_any in mech.Heat.values():
        sys: Any = sys_any
        current = sys.current
        heatmax = sys.capacity
        percent = (100 * current) / heatmax
        print(percent)

    return {"sinks": sinks, "fluxmax": fluxmax}


@views.route("/mecha_use/<s>/<n>/<path:m>")
def mecha_use(s: str, n: str, m):
    if m != "mechtest":
        checklogin()
    use = request.args.get("use") or 0
    n = decode_id(n)

    m_sheet = WikiCharacterSheet.load_locate(m, cache=False)
    if m_sheet is None or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char

    mech.use_system(s, n, use)

    if m != "mechtest":
        m_sheet.save_low_prio(session["user"])

    template = system_map(s.lower())
    if not template:
        abort(404)
    syscat = mech.get_syscat(s.title())
    system = syscat.get(n)
    if not system:
        abort(404)
    return render_template(template, system=system, identifier=m, sys_category=s)


@views.route("/doroll", methods=["POST"])
def doroll():
    checklogin()
    ul = Userlist()
    username = session.get("user")
    if not username:
        abort(401)
    u = ul.loaduserbyname(username)
    if not u:
        abort(404)
    configchar = u.config("character_sheet", None)
    if not configchar:
        return (
            jsonify({"status": "error", "message": "no character sheet configured"}),
            400,
        )

    m_sheet = WikiCharacterSheet.load_locate(str(configchar))
    if not m_sheet or not isinstance(m_sheet.char, FenCharacter):
        return jsonify({"status": "error", "message": "no valid character sheet"}), 404

    c = m_sheet.char
    attributes = ["0"]
    skills = ["0", "0"]
    vals = defaultdict(int)
    data = request.get_json() or []
    for cat in c.Categories.values():
        for item in data:
            for stat_index, val_type in enumerate(cat.keys()):
                if item in cat[val_type]:
                    if stat_index:  # second type is skills
                        skills.append(item)
                    else:  # first type is attributes
                        attributes.append(item)
                    vals[item] = int(cat[val_type][item])
    wh = chat.data.get("webhook")
    if not wh:
        return (
            jsonify(
                {"status": "error", "message": "webhook not working on the server"}
            ),
            500,
        )
    if not (int(vals[attributes[-1]]) + int(vals[skills[-1]]) + int(vals[skills[-2]])):
        return jsonify({"status": "error", "message": "no valid selection"}), 400
    message_data = {
        "content": f"{attributes[-1]}, {skills[-1]} {skills[-2]}@5\n"
        f"{vals[attributes[-1]]}, {vals[skills[-1]]} {vals[skills[-2]]}@5",
        "username": session["user"],
    }
    requests.post(wh, json=message_data)

    return jsonify({"status": "ok"})


@views.route("/mecha_sys/<s>/<n>/<path:m>")
def mecha_sys(s: str, n: str, m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char
    syscat = mech.get_syscat(s.capitalize())
    if not syscat:
        abort(404)
    sys = syscat.get(n)
    template = system_map(s.lower())
    if not template:
        abort(404)
    if not sys:
        abort(404)

    return render_template(template, system=sys, identifier=m, sys_category=s)


@views.route("/mech_energy_meter/<path:m>")
def energy_meter(m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char
    current_max = mech.energy_budget()
    overall_max = mech.energy_total()
    systems, active = mech.energy_allocation()
    fills = [x.energy for x in systems]
    colors = ["var(--secondary-color)", "var(--primary-color)"]
    segments = generate_meter_segments(
        fills, colors, current_max, [x.name for x in systems]
    )
    return render_template(
        "sheets/mechasheet_htmx/bar.html",
        segments=segments,
        name=m.rsplit("/")[-1],
        maximum=100 * current_max / overall_max,
    )


@views.route("/mech_heat_ui/<path:m>")
def mech_heat_ui(m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char
    total_flux = mech.fluxmax()
    current_flux = mech.heatflux
    heatsys = list(mech.Heat.values())
    return render_template(
        "sheets/mechasheet_htmx/heat_ui.html",
        systems=heatsys,
        max_flux=total_flux,
        current_flux=current_flux,
        identifier=m,
    )


@views.route("/mecha_sys_classic/<s>/<n>/<path:m>")
def mecha_sys_classic(s: str, n: str, m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char
    template = system_map_classic(s.lower())
    if not template:
        abort(404)
    system = mech.get_syscat(s.capitalize()).get(n)
    if not system:
        abort(404)
    return render_template(template, system=system, identifier=m)


@views.route("/mech_energy_meter_classic/<path:m>")
def energy_meter_classic(m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    mech = m_sheet.char
    current_max = mech.energy_budget()
    overall_max = mech.energy_total()
    systems, active = mech.energy_allocation()
    fills = [x.energy for x in systems]
    colors = ["var(--secondary-color)", "var(--primary-color)"]
    segments = generate_meter_segments(
        fills, colors, current_max, [x.name for x in systems]
    )
    return render_template(
        "sheets/mechsystems_classic/bar.html",
        segments=segments,
        name=m.rsplit("/")[-1],
        maximum=100 * current_max / overall_max,
    )


@views.route("/preview_move/<path:context>")
def preview_move(context: str):
    context_part, name = context.rsplit("/", 1)
    page = WikiPage.load_locate(context_part)
    if not page:
        abort(404)
    md_obj = MDObj.from_md(page.body)
    result = md_obj.search_children(name)
    if not result:
        page = WikiPage.load_locate("pbtamoves")
        if page:
            md_obj = MDObj.from_md(page.body)
            result = md_obj.search_children(name)
    if not result:
        return "Not Found"
    result.level = 0
    preview_content = Markup(result.to_md(False))

    c_val = context_part
    if page and page.file:
        c_val = page.file.stem

    return render_template_string(
        "<a href=/wiki/{{c|urlencode }}#{{ name|urlencode }}><b>{{header}}:</b> {{ preview_content }}</a>",
        c=c_val,
        name=name,
        preview_content=preview_content,
        header=result.header.title(),
    )


@views.route("/checkbox/<name>/<path:context>", methods=["GET", "POST"])
def checkbox(context: str, name: str):
    page = WikiPage.load_locate(context)
    if not page:
        abort(404)
    md = page.md()
    for item_text, checked in md.all_checklists:
        if item_text == name:
            return make_checkbox(context, name, "checked" if checked else "")
    return ""


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
    if not s or not isinstance(s.char, PBTACharacter):
        abort(404)
    username = session.get("user", "")
    res = False
    if s.tagcheck(username):
        char = s.char
        moves = cast(List[Tuple[str, bool]], char.moves)
        for i, move in enumerate(moves):
            if move[0] == name:
                if request.method == "POST":
                    moves[i] = (name, not move[1])
                res = moves[i][1]
                break
        s.body = char.to_md()
        s.save_low_prio(f"moves updated by {username}")
    return make_checkbox(context, name, "checked" if res else "")


@views.route("/pbta-update-notes", methods=["POST"])
def update_notes():
    context = request.args["c"]
    username = session.get("user", "")

    notes = request.form.get("notes") or ""

    s = WikiCharacterSheet.load_locate(context)
    if s and s.tagcheck(username):
        char = s.char
        if isinstance(char, PBTACharacter):
            char.notes = notes
        elif isinstance(char, FenCharacter):
            char.Notes = MDObj.from_md(notes)
        else:
            return notes
        s.body = char.to_md()
        s.save_low_prio(f"notes updated by {username}")
    return notes


@views.route("/clock/<int:active>/<int:total>/<name>/page")
@views.route("/clock/<int:active>/<int:total>")
def _generate_clock(
    active: int, total: int, name="", page="", endpoint="changeclock", initial=False
):
    generate_clock(active, total, name, page, endpoint, initial)
    return "", 204


@views.route("/line/<int:active>/<int:total>/<name>/page")
@views.route("/line/<int:active>/<int:total>")
def _generate_line(
    active: int, total: int, name="", page="", endpoint="changeline", initial=False
):
    generate_line(active, total, name, page, endpoint, initial)
    return "", 204


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
        p = WikiPage.load_locate(page)
        if p:
            p.change_clock(name, int(delta)).save_low_prio("clock")
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
        if charpage and charpage.tagcheck(username):
            char = charpage.char
            if not isinstance(char, PBTACharacter):
                return "", 204
            if name.startswith("item-"):
                for item in char.inventory:
                    if item.name == name[5:]:
                        item.count += int(delta)
                        break
            else:
                h_val = char.health.get(name.title())
                if isinstance(h_val, dict):
                    h_val[char.current_headings[0].title()] = char.health_get(name)[
                        0
                    ] + int(delta)
            charpage.save_low_prio(f"active element used by {username}")
            broadcast.set()
            charpage.body = char.to_md()
    return "", 204


@views.route("/sheet/<path:c>")
def sheet(c):
    try:
        if s := WikiCharacterSheet.load_locate(c):
            rendered = render_sheet(s)
            if rendered:
                return rendered
            return redirect(url_for("wiki.wikipage", page=c))
        flash("Error: not found. Create Character?")
        session.setdefault("character_gen", {})["stage"] = "start"
        session["character_gen"]["name"] = c
        return redirect(url_for("sheets.chargen"))
    except DescriptiveError as e:
        flash("Error with character sheet:\n" + e.args[0])
        return redirect(url_for("wiki.wikipage", page=c))


@views.route("/sheet/<path:m>/unmodified")
def sheet_unmodified(m):
    m_sheet = WikiCharacterSheet.load_locate(m)
    if not m_sheet or not isinstance(m_sheet.char, Mecha):
        abort(404)
    return render_template(
        "sheets/mechasheet_classic.html", mech=m_sheet.char, identifier=m
    )


@views.route("/pbta/<path:c>")
@views.route("/fensheet/<path:c>")
def oldsheet(c):
    return redirect(url_for("sheets.sheet", c=c))
