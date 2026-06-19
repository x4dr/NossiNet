"""Renderer for Mecha character sheets."""

from typing import TYPE_CHECKING

from flask import render_template, session
from gamepack.endworld.Mecha import Mecha
from gamepack.WikiPage import WikiPage

from NossiSite.mecha_history import MechaEncounterManager
from NossiSite.renderers import register_renderer

if TYPE_CHECKING:
    from gamepack.WikiCharacterSheet import WikiCharacterSheet


@register_renderer(Mecha)
def render_mecha(sheet: WikiCharacterSheet[Mecha]) -> str:
    """Render a Mecha sheet to HTML.

    Args:
        sheet: The wiki character sheet containing the Mecha to render.

    Returns:
        A rendered HTML template for the mecha sheet, or an error string if
        the character data is missing.
    """
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

    from NossiSite.sheet_helpers import infolet_extractor, infolet_filler

    return render_template(
        "sheets/mechasheet.html",
        mech=sheet.char,
        identifier=identifier,
        mech_history_mgr=lambda m: MechaEncounterManager(WikiPage.wikipath(), m),
        current_encounter_id=current_encounter_id,
        infolet=infolet_filler(identifier),
        extract=infolet_extractor,
    )
