from flask import render_template, session
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.endworld.Mecha import Mecha
from gamepack.WikiPage import WikiPage
from NossiSite.renderers import register_renderer
from NossiSite.mecha_history import MechaEncounterManager


@register_renderer(Mecha)
def render_mecha(sheet: WikiCharacterSheet[Mecha]):
    identifier = sheet.file.stem if sheet.file else "mechtest"
    # Special case for tests/testmecha to keep it consistent if needed
    if sheet.file and "tests" in sheet.file.parts:
        identifier = "tests/" + sheet.file.stem

    mech = sheet.char
    if mech is None:
        return "Character data missing"
    history_mgr = MechaEncounterManager(WikiPage.wikipath(), identifier)

    current_encounter_id = session.get("mecha_encounter", {}).get(identifier)
    if not current_encounter_id:
        current_encounter_id = history_mgr.get_latest_encounter_id()

    from NossiSite.sheet_helpers import infolet_filler, infolet_extractor

    return render_template(
        "sheets/mechasheet.html",
        mech=sheet.char,
        identifier=identifier,
        mech_history_mgr=lambda m: MechaEncounterManager(WikiPage.wikipath(), m),
        current_encounter_id=current_encounter_id,
        infolet=infolet_filler(identifier),
        extract=infolet_extractor,
    )
