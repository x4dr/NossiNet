import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.Item import Item


class InfoletTag(NossiTag):
    """
    Item tooltip: `[!q:itemname]`

    Renders a hover tooltip with the item's description from the game database.
    Falls back to showing just the item name if not found.

    Examples:
      [!q:healing potion]
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

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.infolet_re.sub(self._replace, html)

    def _replace(self, match: re.Match):
        name = match.group("name")
        item = Item.item_cache.get(name)
        if item and item.description:
            return f'<div class="tooltip">{name}<span class="tooltiptext">{item.description}</span></div>'
        return name
