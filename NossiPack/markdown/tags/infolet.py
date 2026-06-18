import re

from NossiPack.markdown.base import NossiTag, WikiEnvironment
from NossiPack.markdown.tags.section_tooltip import TOOLTIP_EMBED_THRESHOLD
from gamepack.Item import Item

_infolet_content: list[list[tuple[str, str]]] = []
_counter: int = 0


class InfoletTag(NossiTag):
    priority = 40
    tag_id = "infolet"
    syntax = "[!q:itemname]"
    description = "Hover tooltip with item description from the game database"
    example = "[!q:healing potion]"
    category = "content"
    pattern = r"\[!q:(?P<name>.*?)]"
    flags = "i"
    infolet_re = re.compile(r"\[!q:(?P<name>.*?)]", re.IGNORECASE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        _infolet_content.append([])
        html = self.infolet_re.sub(self._render_trigger, html)

        pending = _infolet_content.pop()
        if pending:
            tips = "\n".join(
                f'<div class="tip-content" id="tip-{tid}" hidden>{content}</div>'
                for tid, content in pending
            )
            html = html + "\n" + tips
        return html

    def _render_trigger(self, match: re.Match):
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
