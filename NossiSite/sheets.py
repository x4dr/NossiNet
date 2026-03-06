from collections import defaultdict
from pathlib import Path
from datetime import datetime
from typing import cast, Tuple, Any, Optional, Dict

import requests
from flask import (
    render_template,
    Blueprint,
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
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage
from gamepack.endworld import Mecha
from NossiSite.renderers import render_sheet
from NossiSite.mecha_history import MechaEncounterManager


def add_pending_event(m: str, event: Dict[str, Any]):
    pending = session.setdefault("mecha_pending", {}).setdefault(m, [])
    etype = event.get("type")
    name = event.get("name")

    if etype == "HEAT_ASSIGNMENT":
        for existing in pending:
            if (
                existing.get("type") == "HEAT_ASSIGNMENT"
                and existing.get("name") == name
            ):
                existing["amount"] = existing.get("amount", 0.0) + event.get(
                    "amount", 0.0
                )
                if abs(existing["amount"]) < 0.001:
                    pending.remove(existing)
                session.modified = True
                return
    elif etype == "SPEED_TARGET":
        for existing in pending:
            if existing.get("type") == "SPEED_TARGET":
                existing["value"] = event.get("value")
                session.modified = True
                return
    elif etype == "SYSTEM_TOGGLE":
        for i, existing in enumerate(pending):
            if existing.get("type") == "SYSTEM_TOGGLE" and existing.get("name") == name:
                pending.pop(i)
                session.modified = True
                return
    elif etype == "MANUAL_HEAT":
        for existing in pending:
            if existing.get("type") == "MANUAL_HEAT":
                existing["value"] = event.get("value")
                session.modified = True
                return
    elif etype == "SYSTEM_ROLL":
        for existing in pending:
            if existing.get("type") == "SYSTEM_ROLL" and existing.get("name") == name:
                existing["value"] = event.get("value")
                session.modified = True
                return

    pending.append(event)
    session.modified = True


def load_mecha_state(
    m: str,
) -> Tuple[WikiCharacterSheet[Mecha], MechaEncounterManager, Optional[str]]:
    m_sheet = WikiCharacterSheet.load_locate(m, cache=False)
    if m_sheet is None or not isinstance(m_sheet.char, Mecha):
        abort(404)

    mech = cast(Mecha, m_sheet.char)
    history_mgr = MechaEncounterManager(WikiPage.wikipath(), m)

    # Get current encounter ID from session or latest
    enc_session = session.get("mecha_encounter", {})
    encounter_id = enc_session.get(m)
    if not encounter_id:
        encounter_id = history_mgr.get_latest_encounter_id()
        if encounter_id:
            enc_session[m] = encounter_id
            session["mecha_encounter"] = enc_session
            session.modified = True
        else:
            # Auto-start first encounter
            encounter_id = history_mgr.start_new_encounter()
            enc_session[m] = encounter_id
            session["mecha_encounter"] = enc_session
            session.modified = True

    # Get playback turn from session
    playback_session = session.get("mecha_playback_turn", {})
    playback_turn = playback_session.get(m)
    if playback_turn is None:
        playback_turn = 0

    if encounter_id:
        log_data = history_mgr.load_encounter(encounter_id)
        if log_data:
            mech.replay(log_data.get("events", []), turn_limit=playback_turn)

    # Apply pending session changes
    pending = session.get("mecha_pending", {}).get(m, [])
    for event in pending:
        try:
            mech.apply_event(event)
        except Exception:
            pass

    return m_sheet, history_mgr, encounter_id


lm = LocalMarkdown()
views = Blueprint("sheets", __name__)


@views.route("/debug/session")
def debug_session():
    from flask import current_app

    return jsonify({"session_id": current_app.config.get("SESSION_ID", "not set")})


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
    if system == "context":
        system = session["character_gen"]["system"]

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
        session.modified = True
    return chargen_htmx()


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
    vals = defaultdict(int)
    data = request.get_json() or []

    # Build components in order: Stat1, Stat2 + Mod @5 R
    stats = [p for p in data if isinstance(p, dict) and p.get("type") == "stat"]
    reroll = next(
        (p for p in data if isinstance(p, dict) and p.get("type") == "reroll"), None
    )

    # labels of stats to look up
    stat_labels = [s.get("label", "") for s in stats]
    for cat in c.Categories.values():
        for item in stat_labels:
            for val_type in cat.keys():
                if item in cat[val_type]:
                    vals[item] = int(cat[val_type][item])

    if not stats:
        return jsonify({"status": "error", "message": "no valid selection"}), 400

    wh = chat.data.get("webhook")
    # Build components in order as provided in the payload
    labels = []
    values = []

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue

        # Skip reroll in main loop, we add it at the end
        if entry.get("type") == "reroll":
            continue

        label = entry.get("label", "")
        raw_val = entry.get("val", "0")
        joiner = entry.get("joiner", "")  # , or +

        # If this is not the first item, prepend the joiner
        prefix = ""
        if i > 0 and joiner:
            prefix = joiner + " "

        # Labels line
        labels.append(f"{prefix}{label}")

        # Values line
        # If it's a stat from the sheet, use its actual value. Otherwise use the raw value.
        val_to_use = raw_val
        if label in vals:
            val_to_use = str(vals[label])

        values.append(f"{prefix}{val_to_use}")

    labels.append("@5")
    values.append("@5")

    if reroll:
        labels.append("R" + reroll.get("val", "0"))
        values.append("R" + reroll.get("val", "0"))

    message_data = {
        "content": "".join(labels) + "\n" + "".join(values),
        "username": session["user"],
    }
    requests.post(wh, json=message_data)

    return jsonify({"status": "ok"})


def generate_meter_segments(fills, colors, total, names):
    if total <= 0:
        return []
    segments = []
    bottom = 0
    for i, fill in enumerate(fills):
        color = colors[i % len(colors)]
        percent = (100 * fill) / total
        offset = (100 * bottom) / total
        if offset + percent > 100:
            percent = max(0, 100 - offset)
            color = "var(--warn-color)"
        segments.append(
            {"fill": percent, "color": color, "offset": offset, "name": names[i]}
        )
        bottom += fill
    return segments


@views.route("/mecha_status_summary/<path:m>")
def mecha_status_summary(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return render_template(
        "sheets/mechasheet_htmx/status_bar.html", mech=mech, identifier=m
    )


@views.route("/mecha_movement_summary/<path:m>")
def mecha_movement_summary(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return Markup(
        f"Speed: <span class='highlight'>{round(mech.current_speed, 1)}</span> km/h"
    )


@views.route("/mecha_timeline/<path:m>")
def mecha_timeline(m):
    _, history_mgr, encounter_id = load_mecha_state(m)
    if not encounter_id:
        return "<p style='color: var(--text-dim); font-style: italic;'>No encounter history found.</p>"

    latest = history_mgr.load_encounter(encounter_id)
    if not latest:
        return "<p style='color: var(--text-dim); font-style: italic;'>No encounter history found.</p>"

    playback_turn = session.get("mecha_playback_turn", {}).get(m)

    return render_template(
        "sheets/mechasheet_htmx/timeline.html",
        encounter=latest,
        playback_turn=playback_turn,
        identifier=m,
    )


@views.route("/mecha_energy_summary/<path:m>")
def mecha_energy_summary(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return Markup(f"Output: <span class='highlight'>{mech.energy_output()}</span>")


@views.route("/mecha_heat_summary/<path:m>")
def mecha_heat_summary(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return Markup(
        f"Flux: <span class='highlight'>{round(mech.fluxpool, 1)} / {round(mech.fluxpool_max(), 1)}</span>"
    )


@views.route("/mecha_start_encounter/<path:m>", methods=["POST"])
def mecha_start_encounter(m):
    history_mgr = MechaEncounterManager(WikiPage.wikipath(), m)
    # Default name is the applied loadout
    encounter_id = history_mgr.start_new_encounter(custom_name="Default")

    session.setdefault("mecha_encounter", {})[m] = encounter_id
    session.setdefault("mecha_pending", {})[m] = []
    session.setdefault("mecha_playback_turn", {})[m] = 0
    session.modified = True

    return redirect(url_for("sheets.sheet", c=m))


@views.route("/mecha_select_encounter/<path:m>/<id>", methods=["POST"])
def mecha_select_encounter(m, id):
    session.setdefault("mecha_encounter", {})[m] = id
    session.setdefault("mecha_pending", {})[m] = []
    # Reset playback turn so load_mecha_state finds the latest for this encounter
    session.setdefault("mecha_playback_turn", {})[m] = None
    session.modified = True

    return redirect(url_for("sheets.sheet", c=m))


@views.route("/mecha_rename_encounter/<path:m>/<id>", methods=["POST"])
def mecha_rename_encounter(m, id):
    new_name = request.form.get("new_encounter_name")
    if new_name:
        history_mgr = MechaEncounterManager(WikiPage.wikipath(), m)
        history_mgr.rename_encounter(id, new_name)

    return redirect(url_for("sheets.sheet", c=m))


@views.route("/mecha_next_turn_view/<path:m>")
def mecha_next_turn_view(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return render_template(
        "sheets/mechasheet_htmx/next_turn_view.html", mech=mech, identifier=m
    )


@views.route("/mecha_assign_heat/<n>/<path:m>", methods=["POST"])
def mecha_assign_heat(n, m):
    if m != "mechtest":
        checklogin()

    amount = request.form.get("amount")
    current_val = request.form.get("current_val")

    n = decode_id(n)
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    sys = mech.Heat.get(n)
    if not sys:
        abort(404)

    if current_val is not None:
        try:
            target_val = float(current_val)
            delta = target_val - sys.current
            if abs(delta) > 0.001:
                add_pending_event(
                    m, {"type": "HEAT_ASSIGNMENT", "name": n, "amount": delta}
                )
        except (ValueError, TypeError):
            abort(400)
    elif amount is not None:
        try:
            delta = float(amount)
            if abs(delta) > 0.001:
                add_pending_event(
                    m, {"type": "HEAT_ASSIGNMENT", "name": n, "amount": delta}
                )
        except (ValueError, TypeError):
            abort(400)

    # Re-load state to reflect change in UI
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    sys = mech.Heat.get(n)
    if not sys:
        abort(404)

    # Return the system fragment and trigger a refresh of the heat UI
    return render_template(
        "sheets/mechasheet_htmx/heat.html",
        system=sys,
        identifier=m,
        sys_category="heat",
    ), {"HX-Trigger": "resource-updated"}


@views.route("/mecha_commit_turn/<path:m>", methods=["POST"])
def mecha_commit_turn(m):
    data = request.json
    print(f"DEBUG: Processing commit for {m}: {data}")
    if not data:
        abort(400)

    m_sheet, history_mgr, encounter_id = load_mecha_state(m)
    if not encounter_id:
        encounter_id = (
            history_mgr.get_latest_encounter_id() or history_mgr.start_new_encounter()
        )
        session.setdefault("mecha_encounter", {})[m] = encounter_id

    # 1. Truncate log if we are in the past
    playback_session = session.get("mecha_playback_turn", {})
    playback_turn = playback_session.get(m)
    if playback_turn is not None:
        history_mgr.truncate_log(encounter_id, playback_turn)

    mech = cast(Mecha, m_sheet.char)

    # 2. Add pending actions from the JSON data
    # Speed
    if data.get("speed") is not None:
        event = {"type": "SPEED_TARGET", "value": data["speed"]}
        history_mgr.log_event(encounter_id, event)
        mech.apply_event(event)

    # Loadout
    if data.get("loadout"):
        event = {"type": "LOADOUT_APPLY", "name": data["loadout"]}
        print(f"DEBUG: Applying loadout rename: {data['loadout']} to {encounter_id}")
        history_mgr.log_event(encounter_id, event)
        mech.apply_event(event)
        # Rename encounter to the applied loadout
        history_mgr.rename_encounter(encounter_id, data["loadout"])

    # Toggles
    toggles = data.get("toggles", {})
    for b64, state in toggles.items():
        name = decode_id(b64)
        event = {
            "type": "SYSTEM_TOGGLE",
            "name": name,
            "state": "active" if state else "inactive",
        }
        history_mgr.log_event(encounter_id, event)
        mech.apply_event(event)

    # Heat assignments
    heat = data.get("heat", {})
    for b64, absolute_val in heat.items():
        name = decode_id(b64)
        sys = mech.Heat.get(name)
        if sys:
            delta = absolute_val - sys.current
            if abs(delta) > 0.001:
                event = {"type": "HEAT_ASSIGNMENT", "name": name, "amount": delta}
                history_mgr.log_event(encounter_id, event)
                mech.apply_event(event)

    # System Rolls
    rolls = data.get("rolls", {})
    for b64, val in rolls.items():
        name = decode_id(b64)
        event = {"type": "SYSTEM_ROLL", "name": name, "value": val}
        history_mgr.log_event(encounter_id, event)
        mech.apply_event(event)

    # 3. Process the turn transition
    summary = mech.next_turn()
    print(
        f"DEBUG: Commit turn result: new_turn={mech.turn}, overheated={summary.get('overheated')}"
    )

    # 4. Log individual transition events first so they are replayed
    for event in summary.get("events", []):
        history_mgr.log_event(encounter_id, event)

    # 5. Log the turn commit
    history_mgr.log_event(
        encounter_id,
        {
            "type": "TURN_COMMIT",
            "turn": mech.turn,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "summary": summary,
        },
    )

    # 6. Update session

    session.setdefault("mecha_pending", {})[m] = []
    session.setdefault("mecha_playback_turn", {})[m] = mech.turn

    if summary.get("overheated"):
        session.setdefault("mecha_modals", {}).setdefault(m, []).append(
            {
                "type": "OVERHEAT",
                "target": next(
                    (e["target"] for e in summary["events"] if e["type"] == "OVERHEAT"),
                    None,
                ),
            }
        )

    session.modified = True

    if m != "mechtest":
        m_sheet.save_low_prio(session.get("user", "system"))
    else:
        m_sheet.save_low_prio("test-session")

    return jsonify({"status": "ok", "turn": mech.turn})


@views.route("/mecha_undo/<path:m>", methods=["POST"])
def mecha_undo(m):
    # 1. Try to undo pending changes first
    pending = session.get("mecha_pending", {}).get(m, [])
    if pending:
        pending.pop()
        session.modified = True
        return "", 204, {"HX-Refresh": "true"}
    else:
        # 2. If no pending, move playback pointer back
        playback_session = session.setdefault("mecha_playback_turn", {})
        current_turn = playback_session.get(m)
        if current_turn is None:
            _, _, encounter_id = load_mecha_state(m)
            current_turn = session.get("mecha_playback_turn", {}).get(m, 0)

        if current_turn > 0:
            session.setdefault("mecha_playback_turn", {})[m] = current_turn - 1
            session.modified = True
            return "", 204, {"HX-Refresh": "true"}

    return "", 204


@views.route("/mecha_redo/<path:m>", methods=["POST"])
def mecha_redo(m):
    m_sheet, history_mgr, encounter_id = load_mecha_state(m)
    if not encounter_id:
        return "", 204

    log_data = history_mgr.load_encounter(encounter_id)
    if not log_data:
        return "", 204

    max_turn = 0
    for event in log_data.get("events", []):
        if event.get("type") == "TURN_COMMIT":
            max_turn = max(max_turn, event.get("turn", 0))

    playback_session = session.setdefault("mecha_playback_turn", {})
    current_turn = playback_session.get(m, max_turn)

    if current_turn < max_turn:
        playback_session[m] = current_turn + 1
        session.modified = True
        return "", 204, {"HX-Refresh": "true"}

    return "", 204


@views.route("/mecha_restore_state/<path:m>/<int:turn>", methods=["POST"])
def mecha_restore_state(m, turn):
    # Non-destructive: just move the pointer
    playback_session = session.setdefault("mecha_playback_turn", {})
    playback_session[m] = turn
    session.modified = True

    # Clear pending when jumping to a specific turn
    session.setdefault("mecha_pending", {})[m] = []

    return "", 204, {"HX-Refresh": "true"}


@views.route("/mecha_next_turn/<path:m>", methods=["POST"])
def mecha_next_turn(m):
    if m != "mechtest":
        checklogin()

    m_sheet, history_mgr, encounter_id = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)

    # 1. Start encounter if none exists
    if not encounter_id:
        encounter_id = history_mgr.start_new_encounter()
        session.setdefault("mecha_encounter", {})[m] = encounter_id
        session.modified = True

    # 2. Truncate log if we are in the past (Clear Redo stack on commit)
    playback_session = session.get("mecha_playback_turn", {})
    playback_turn = playback_session.get(m)
    if playback_turn is not None:
        history_mgr.truncate_log(encounter_id, playback_turn)

    # 3. Commit pending session changes to the log
    pending = session.get("mecha_pending", {}).pop(m, [])
    for event in pending:
        history_mgr.log_event(encounter_id, event)
    session.modified = True

    # 4. Process the turn transition
    summary = mech.next_turn()

    # 5. Log the turn commit in encounter history
    history_mgr.log_event(
        encounter_id,
        {
            "type": "TURN_COMMIT",
            "turn": mech.turn,
            "summary": summary,
            "events": summary.get("events", []),
        },
    )

    # 6. Update playback pointer to the new turn
    playback_session[m] = mech.turn
    session["mecha_playback_turn"] = playback_session
    session.modified = True

    # 7. Save the mecha state (permanent changes like sectors/damage)
    if m != "mechtest":
        m_sheet.save_low_prio(session.get("user", "system"))
    else:
        m_sheet.save_low_prio("test-session")

    # 8. Return a success response that triggers a page refresh
    headers = {"HX-Refresh": "true"}
    if summary.get("overheated"):
        # We can't really do both HX-Refresh and a modal easily
        # unless we redirect to a specific state.
        # But maybe we can set a session flag for the modal to show on next load.
        session.setdefault("mecha_modals", {}).setdefault(m, []).append(
            {
                "type": "OVERHEAT",
                "target": next(
                    (e["target"] for e in summary["events"] if e["type"] == "OVERHEAT"),
                    None,
                ),
            }
        )
        session.modified = True

    return "", 204, headers


@views.route("/mecha_use/<s>/<n>/<path:m>", methods=["POST"])
def mecha_use(s: str, n: str, m):
    if m != "mechtest":
        checklogin()
    n = decode_id(n)

    # Add to pending session changes
    # Determine state for toggle
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    sys = mech.get_system(n)
    if sys:
        new_state = "inactive" if sys.is_active() or sys.is_booting() else "active"
        add_pending_event(m, {"type": "SYSTEM_TOGGLE", "name": n, "state": new_state})

    # Re-load state to reflect change in UI
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    syscat = mech.get_syscat(s.title())
    system = syscat.get(n)
    if not system:
        abort(404)

    template = system_map(s.lower())
    return render_template(template, system=system, identifier=m, sys_category=s), {
        "HX-Trigger": "resource-updated"
    }


@views.route("/mecha_sys/<s>/<n>/<path:m>")
def mecha_sys(s: str, n: str, m):
    n = decode_id(n)
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    syscat = mech.get_syscat(s.capitalize())
    if not syscat:
        abort(404)
    sys = syscat.get(n)
    if not sys:
        abort(404)
    template = system_map(s.lower())
    if not template:
        abort(404)

    return render_template(template, system=sys, identifier=m, sys_category=s)


@views.route("/mecha_system_detail/<path:m>/<s>/<n>")
def mecha_system_detail(m, s, n):
    if m != "mechtest":
        checklogin()

    n = decode_id(n)
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    syscat = mech.get_syscat(s.capitalize())
    if not syscat:
        abort(404)
    sys = syscat.get(n)
    if not sys:
        abort(404)

    from gamepack.WikiPage import WikiPage

    base_page = WikiPage.load_locate(sys.name)

    from NossiSite.sheet_helpers import infolet_filler, infolet_extractor

    return render_template(
        "sheets/mecha_system_detail.html",
        system=sys,
        identifier=m,
        sys_category=s,
        base_page=base_page,
        infolet=infolet_filler(m),
        extract=infolet_extractor,
    )


@views.route("/mecha_set_roll/<path:m>/<s>/<n>", methods=["POST"])
def mecha_set_roll(m, s, n):
    if m != "mechtest":
        checklogin()

    n = decode_id(n)
    roll = request.form.get("roll")
    if roll is not None:
        try:
            val = int(roll)
            add_pending_event(m, {"type": "SYSTEM_ROLL", "name": n, "value": val})
        except (ValueError, TypeError):
            abort(400)

    # Re-load state
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    syscat = mech.get_syscat(s.capitalize())
    sys = syscat.get(n)
    if not sys:
        abort(404)

    template = system_map(s.lower())
    return render_template(template, system=sys, identifier=m, sys_category=s)


@views.route("/mecha_update_sector/<path:m>/<name>", methods=["POST"])
def mecha_update_sector(m, name):
    if m != "mechtest":
        checklogin()

    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)

    if name == "NEW":
        new_name = request.form.get("new_name")
        if new_name:
            mech.Sectors[new_name] = {"Damage": 0, "Malfunctions": ""}
    else:
        damage = request.form.get("damage")
        malfunctions = request.form.get("malfunctions")
        if name in mech.Sectors:
            if damage is not None:
                try:
                    mech.Sectors[name]["Damage"] = int(damage)
                except (ValueError, TypeError):
                    pass
            if malfunctions is not None:
                mech.Sectors[name]["Malfunctions"] = malfunctions

    if m != "mechtest":
        m_sheet.save_low_prio(session.get("user", "system"))
    else:
        m_sheet.save_low_prio("test-session")

    return render_template(
        "sheets/mechasheet_htmx/overview_ui.html", mech=mech, identifier=m
    )


@views.route("/mecha_check_modals/<path:m>")
def mecha_check_modals(m):
    modals = session.get("mecha_modals", {}).get(m, [])
    if not modals:
        return "", 204

    modal = modals[0]
    if modal["type"] == "OVERHEAT":
        return render_template(
            "sheets/mechasheet_htmx/overheat_modal.html",
            m=m,
            target=modal.get("target"),
        )

    return "", 204


@views.route("/mecha_clear_modals/<path:m>", methods=["POST"])
def mecha_clear_modals(m):
    if "mecha_modals" in session and m in session["mecha_modals"]:
        session["mecha_modals"][m] = []
        session.modified = True
    return "", 204


@views.route("/mecha_overheat_redirect/<path:m>/<target>")
def mecha_overheat_redirect(m, target):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    return render_template(
        "sheets/mechasheet_htmx/overview_ui.html",
        mech=mech,
        identifier=m,
        suggested_system=target,
    )


@views.route("/mech_energy_meter/<path:m>")
def energy_meter(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
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
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    total_flux = mech.fluxpool_max()
    current_flux = mech.fluxpool
    projected_gen = mech.projected_flux()
    projected_cooling = mech.projected_cooling()

    heatsys = list(mech.Heat.values())

    # Total heat capacity of the mech
    total_capacity = sum(h.capacity for h in heatsys)
    if total_capacity == 0:
        total_capacity = 1  # avoid div by zero

    fills = [h.current for h in heatsys]
    colors = [
        "var(--danger)",
        "var(--warn-color)",
        "var(--secondary-color)",
        "var(--primary-color)",
        "var(--accent)",
    ]
    names = [h.name for h in heatsys]

    segments = generate_meter_segments(fills, colors, total_capacity, names)

    # Heat producers (Next Turn)
    producers = []
    for cat in ["Movement", "Energy", "Heat", "Offensive", "Defensive", "Support"]:
        for sys in getattr(mech, cat).values():
            if sys.is_active() or sys.is_booting():
                h = sys.amount * (
                    sum(sys.heats.values()) if hasattr(sys, "heats") else sys.heat
                )
                if h > 0:
                    producers.append({"name": sys.name, "amount": h})

    return render_template(
        "sheets/mechasheet_htmx/heat_ui.html",
        systems=heatsys,
        max_flux=total_flux,
        current_flux=current_flux,
        projected_gen=projected_gen,
        projected_cooling=projected_cooling,
        identifier=m,
        segments=segments,
        total_capacity=total_capacity,
        total_heat=sum(fills),
        producers=producers,
    )


@views.route("/sheet/<path:c>")
def sheet(c):
    try:
        s = WikiCharacterSheet.load_locate(c, cache=False)
        if s:
            if isinstance(s.char, Mecha):
                s, _, _ = load_mecha_state(c)

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


@views.route("/mecha_movement_graph/<path:m>")
def mecha_movement_graph(m):
    m_sheet, _, _ = load_mecha_state(m)
    mech = cast(Mecha, m_sheet.char)
    data = mech.speeds()
    ns_max_time = 1
    ns_max_speed = 1
    for _, sys in data.items():
        for t, v in sys["speeds"].items():
            ti = int(t)
            if ti > ns_max_time:
                ns_max_time = ti
            if v > ns_max_speed:
                ns_max_speed = v

    return render_template(
        "sheets/mechasheet_htmx/movement_graph.html",
        speeds=data,
        max_time=ns_max_time,
        max_speed=ns_max_speed,
        identifier=m,
    )


@views.route("/pbta/<path:c>")
@views.route("/fensheet/<path:c>")
def oldsheet(c):
    return redirect(url_for("sheets.sheet", c=c))
