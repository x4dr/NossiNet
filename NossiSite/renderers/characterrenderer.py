from typing import Any
from flask import render_template, session, redirect, url_for
from pathlib import Path
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage
from gamepack.FenCharacter import FenCharacter
from gamepack.endworld.EWCharacter import EWCharacter
from NossiSite.renderers import register_renderer
from NossiPack.User import User
from NossiPack.markdown import NossiMarkdownProcessor
from NossiSite.sheet_helpers import infolet_filler, infolet_extractor

lm = NossiMarkdownProcessor()


@register_renderer(FenCharacter)
@register_renderer(EWCharacter)
def render_character(sheet: WikiCharacterSheet[Any]):
    # LSP check
    if sheet is None:
        return redirect(url_for("wiki.tagsearch", tag="character"))

    username = session.get("user", "")
    u = User(username).configs()
    charsh = u.get("character_sheet", None)
    path = sheet.file.relative_to(sheet.wikipath()) if sheet.file else Path(".")

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
            page=(
                sheet.file.relative_to(WikiPage.wikipath()).as_posix()
                if sheet.file
                else ""
            ),
        ),
        extract=infolet_extractor,
        owner=owner,
    )
