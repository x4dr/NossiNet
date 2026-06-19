"""Renderer for PBTACharacter sheets."""

from typing import TYPE_CHECKING, Any

from flask import render_template
from gamepack.PBTACharacter import PBTACharacter

from NossiSite.renderers import register_renderer

if TYPE_CHECKING:
    from gamepack.WikiCharacterSheet import WikiCharacterSheet


@register_renderer(PBTACharacter)
def render_pbta(sheet: WikiCharacterSheet[Any]) -> str:
    """Render a PBTACharacter sheet to HTML.

    Args:
        sheet: The wiki character sheet containing the PBTA character.

    Returns:
        A rendered HTML template for the PBTA sheet.
    """
    return render_template(
        "sheets/pbtasheet.html",
        character=sheet.char,
        context=sheet.file.stem if sheet.file else "",
    )
