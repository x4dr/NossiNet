from typing import Any
from flask import render_template
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.PBTACharacter import PBTACharacter
from NossiSite.renderers import register_renderer


@register_renderer(PBTACharacter)
def render_pbta(sheet: WikiCharacterSheet[Any]):
    return render_template(
        "sheets/pbtasheet.html",
        character=sheet.char,
        context=sheet.file.stem if sheet.file else "",
    )
