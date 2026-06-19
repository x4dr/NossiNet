"""Inline item infolet tooltips for wiki markdown."""

import re

from gamepack.Item import Item

from NossiPack.markdown.base import NossiTag, WikiEnvironment
from NossiPack.markdown.tags.section_tooltip import TOOLTIP_EMBED_THRESHOLD

_infolet_content: list[list[tuple[str, str]]] = []
_counter: int = 0


class InfoletTag(NossiTag):
    """Inline item infolet: ``[!q:itemname]``.

    Renders a hover tooltip showing an item's description from the game
    database. Short descriptions are embedded directly; longer ones
    use a deferred tooltip lookup.
    """

    priority = 40
    tag_id = "infolet"
    syntax = "[!q:itemname]"
    description = "Hover tooltip with item description from the game database"
    example = "[!q:healing potion]"
    category = "content"
    pattern = r"\[!q:(?P<name>.*?)]"
    flags = "i"
    infolet_re = re.compile(r"\[!q:(?P<name>.*?)]", re.IGNORECASE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace infolet syntax with tooltip trigger HTML.

        Renders item name tooltips and appends hidden tip-content divs
        at the end of the HTML.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with infolet placeholders replaced by tooltip triggers.
        """
        _infolet_content.append([])
        html = self.infolet_re.sub(self._render_trigger, html)

        pending = _infolet_content.pop()
        if pending:
            tips = "\n".join(
                f'<div class="tip-content" id="tip-{tid}" hidden>{content}</div>' for tid, content in pending
            )
            html = html + "\n" + tips
        return html

    def _render_trigger(self, match: re.Match[str]) -> str:
        """Render a single infolet match as a tooltip trigger.

        Looks up the item in the game database and decides whether to
        embed the description inline or use a deferred tooltip reference.

        Args:
            match: The regex match for an infolet pattern.

        Returns:
            HTML for the tooltip trigger element, or the item name as
            plain text if the item is not found.
        """
        name = match.group("name")
        item = Item.item_cache.get(name)
        if not item or not item.description:
            return name

        desc = item.description
        if len(desc) <= TOOLTIP_EMBED_THRESHOLD:
            global _counter
            tip_id = f"iq-{_counter}"
            _counter += 1
            _infolet_content[-1].append((tip_id, desc))
            return f'<span class="tip-trigger" data-tip="{tip_id}">{name}</span>'

        return f'<span class="tip-trigger" data-tooltip="item:{name}">{name}</span>'
