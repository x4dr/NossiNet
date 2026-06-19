"""Renderer for FenCharacter and EWCharacter sheets."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import redirect, render_template, session, url_for
from gamepack.endworld.EWCharacter import EWCharacter
from gamepack.FenCharacter import FenCharacter
from gamepack.WikiPage import WikiPage

from NossiPack.markdown import NossiMarkdownProcessor
from NossiPack.User import User
from NossiSite.renderers import register_renderer
from NossiSite.sheet_helpers import infolet_extractor, infolet_filler

if TYPE_CHECKING:
    from gamepack.WikiCharacterSheet import WikiCharacterSheet

lm = NossiMarkdownProcessor()


@register_renderer(FenCharacter)
@register_renderer(EWCharacter)
def render_character(sheet: WikiCharacterSheet[Any]) -> str:
    """Render a FenCharacter or EWCharacter sheet to HTML.

    Args:
        sheet: The wiki character sheet to render.

    Returns:
        A redirect to the tag search if sheet is None, or a rendered HTML
        template for the character sheet.
    """
    # LSP check
    if sheet is None:
        return redirect(url_for("wiki.tagsearch", tag="character"))

    username = session.get("user", "")
    u = User(username).configs()
    charsh = u.get("character_sheet", None)
    path = sheet.file.relative_to(sheet.wikipath()) if sheet.file else Path()

    owner = ""
    if charsh:
        sh_path = WikiPage.locate(str(charsh))
        if sh_path and WikiPage.locate(path.as_posix()) == sh_path:
            owner = charsh

    return render_template(
        "sheets/fensheet.html",
        character=sheet.char,
        context=path,
        userconf=u,
        infolet=infolet_filler(path),
        md=lambda x: lm.process(
            x,
            page=(sheet.file.relative_to(WikiPage.wikipath()).as_posix() if sheet.file else ""),
        ),
        extract=infolet_extractor,
        owner=owner,
    )
