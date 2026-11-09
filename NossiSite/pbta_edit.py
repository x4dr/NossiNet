"""Structured markdown edits for PBTA character sheets.

A PBTA sheet is a wiki markdown page and the wiki is the source of truth for
health, moves and notes. Clicking a gauge or toggling a move therefore has to
rewrite the page source, exactly the way ``live_edit`` does for the Fen sheet.

These helpers are deliberately pure: they take a page body and return a new one.
Keeping the rewriting separate from Flask, the database and SSE means the tricky
part -- not corrupting someone's character sheet -- is testable on its own.
"""

import re
from urllib.parse import quote

from NossiSite.base_ext import encode_id

__all__ = [
    "HEALTH_ROWS",
    "gauge_id",
    "page_id",
    "render_gauge",
    "set_health",
    "set_notes",
    "toggle_move",
]

#: The health rows the PBTA sheet renders as gauges. Order matches the sheet.
HEALTH_ROWS = ("Stress", "Trauma", "Healing", "Armor")


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp ``value`` into ``[low, high]``.

    Args:
        value: The raw value.
        low: Minimum allowed.
        high: Maximum allowed.

    Returns:
        The clamped value.
    """
    return max(low, min(high, value))


def set_health(body: str, name: str, current: int, maximum: int | None = None) -> str:
    """Set one health gauge's Current (and optionally Maximum) in the Health table.

    Matches the row by label and rewrites only that row, preserving the column
    padding and any Maximum the caller did not change. A label that is not
    present leaves the body untouched.

    Args:
        body: The full wiki page markdown.
        name: Health row label, e.g. ``"Stress"`` (case-insensitive).
        current: New current value.
        maximum: New maximum, or None to keep the existing one.

    Returns:
        The page body with the row updated.
    """
    row_re = re.compile(
        r"^(?P<pre>\s*\|\s*" + re.escape(name) + r"\s*\|\s*)(?P<cur>\d+)(?P<mid>\s*\|\s*)"
        r"(?P<max>\d+)(?P<post>\s*\|)(?P<rest>.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = row_re.search(body)
    if not match:
        return body
    new_max = str(maximum) if maximum is not None else match.group("max")
    replacement = (
        match.group("pre")
        + str(_clamp(current, 0, int(new_max)))
        + match.group("mid")
        + new_max
        + match.group("post")
        + match.group("rest")
    )
    return body[: match.start()] + replacement + body[match.end() :]


def toggle_move(body: str, name: str, checked: bool | None = None) -> str:
    """Flip or set a move's checkbox in a ``- [ ]`` / ``- [x]`` checklist.

    Args:
        body: The full wiki page markdown.
        name: The move text as it appears after the checkbox.
        checked: True/False to force a state, or None to flip the current one.

    Returns:
        The page body with that checklist item updated.
    """
    item_re = re.compile(
        r"^(?P<pre>\s*-\s*)\[(?P<mark>[^\]])\](?P<post>\s*" + re.escape(name) + r"\s*)$",
        re.MULTILINE,
    )
    match = item_re.search(body)
    if not match:
        return body
    was_checked = match.group("mark").strip().lower() == "x"
    now_checked = (not was_checked) if checked is None else checked
    replacement = (
        match.group("pre") + "[x]" + match.group("post")
        if now_checked
        else match.group("pre") + "[ ]" + match.group("post")
    )
    return body[: match.start()] + replacement + body[match.end() :]


def set_notes(body: str, notes: str) -> str:
    """Replace the body of the ``# Notes`` section.

    Everything after the Notes heading up to the next heading of the same or
    higher level is replaced. A page with no Notes heading is unchanged.

    Args:
        body: The full wiki page markdown.
        notes: The replacement notes text.

    Returns:
        The page body with the Notes section replaced.
    """
    heading_re = re.compile(r"^(?P<hashes>#{1,6})\s*Notes\s*$", re.IGNORECASE | re.MULTILINE)
    match = heading_re.search(body)
    if not match:
        return body

    level = len(match.group("hashes"))
    after = body[match.end() :]
    stop_re = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    stop = stop_re.search(after)
    if stop:
        tail = after[stop.start() :]
        replacement = "\n\n" + notes.strip() + "\n\n"
    else:
        tail = ""
        replacement = "\n\n" + notes.strip() + "\n"

    return body[: match.end()] + replacement + tail


def page_id(c: str) -> str:
    """Normalise a sheet reference to its wiki-relative ``.md`` id.

    Args:
        c: A sheet reference, with or without the ``.md`` suffix.

    Returns:
        The page id ending in ``.md``.
    """
    return c if c.endswith(".md") else c + ".md"


def gauge_id(name: str, c: str) -> str:
    """Return the DOM id of a PBTA health gauge.

    ``sse_handler.js`` locates the gauge to update by this id when a ``line``
    event arrives, and the broadcast path builds the same id, so both sides must
    agree. Shared here rather than computed twice.

    Args:
        name: Health row label.
        c: Sheet reference (with or without ``.md``).

    Returns:
        The element id.
    """
    return f"{encode_id(name)}-{encode_id(page_id(c))}"


def render_gauge(name: str, active: int, total: int, c: str, *, css_class: str = "") -> str:
    """Render one PBTA health gauge as a clickable line gauge.

    Emits the same ``.gauge`` / ``.gauge-box`` structure that
    ``socks.generate_line`` produces, so ``clock.js`` click handling and the
    ``line`` SSE handler work unchanged. Unlike the wiki clock variant the value
    comes from the markdown source of truth and the click endpoint rewrites that
    markdown.

    Args:
        name: Health row label.
        active: Current value.
        total: Maximum value.
        c: Sheet reference, used to build the click endpoint and element id.
        css_class: Extra class for the container (e.g. ``"trauma"``).

    Returns:
        The gauge HTML.
    """
    total = max(1, int(total))
    active = _clamp(int(active), 0, total)
    boxes = ""
    for i in range(total):
        incdec = "-1" if i < active else "1"
        endpoint = f"/pbta/{quote(page_id(c))}/health/{quote(name)}/{incdec}"
        boxes += (
            f'<div class="gauge-box {"filled" if i < active else "empty"}" '
            f'data-endpoint="{endpoint}" style="--bouncedelay:{i / total}"></div>'
        )
    cls = f"gauge {css_class}".strip()
    return f'<div class="{cls}" id="{gauge_id(name, c)}">{boxes}</div>'
