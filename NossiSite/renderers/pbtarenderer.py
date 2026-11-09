"""Renderer for PBTACharacter sheets."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import render_template, session
from gamepack.PBTACharacter import PBTACharacter

from NossiPack.User import Config
from NossiSite.pbta_edit import render_gauge
from NossiSite.renderers import register_renderer

if TYPE_CHECKING:
    from collections.abc import Callable

    from gamepack.WikiCharacterSheet import WikiCharacterSheet


def _owner_of(c: str) -> str:
    """Return the configured owner of a character sheet, or "" if unclaimed.

    Args:
        c: Sheet reference.

    Returns:
        The owning username, or an empty string.
    """
    owners = Config.users_with_option_value("character_sheet", c)
    return str(owners[0][0]) if owners else ""


def _health_pair(health: dict[str, Any], name: str) -> tuple[int, int]:
    """Pull current and maximum for a health row out of the parsed sheet.

    Args:
        health: The character's parsed health mapping.
        name: Health row label.

    Returns:
        A ``(current, maximum)`` pair, defaulting to zeros when absent.
    """
    row = health.get(name) or {}
    try:
        return int(row.get("Current", 0)), int(row.get("Maximum", 0))
    except TypeError, ValueError:
        return 0, 0


@register_renderer(PBTACharacter)
def render_pbta(sheet: WikiCharacterSheet[Any]) -> str:
    """Render a PBTACharacter sheet to HTML.

    Health gauges are rendered server-side from the markdown Health table and
    kept in sync over SSE; the sheet previously embedded ``hx-ws`` calls to a
    WebSocket route removed when clock handling moved to SSE, so those gauges
    never populated.

    Args:
        sheet: The wiki character sheet containing the PBTA character.

    Returns:
        A rendered HTML template for the PBTA sheet.
    """
    path = sheet.file.relative_to(sheet.wikipath()) if sheet.file else Path()
    context = path.as_posix()
    owner = _owner_of(context)

    def health_gauge(name: str, css_class: str = "") -> str:
        """Render the gauge for one health row, reading its value from the sheet.

        Args:
            name: Health row label.
            css_class: Extra container class, e.g. ``"trauma"``.

        Returns:
            The gauge HTML.
        """
        assert sheet.char is not None
        current, maximum = _health_pair(sheet.char.health, name)
        return render_gauge(name, current, maximum, context, css_class=css_class)

    render: Callable[[str, str], str] = health_gauge
    return render_template(
        "sheets/pbtasheet.html",
        character=sheet.char,
        context=context,
        owner=context if (owner and owner == session.get("user", "")) else "",
        gauge=render,
    )
