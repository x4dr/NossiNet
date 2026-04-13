import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.Item import Item


class InfoletTag(NossiTag):
    """
    Handles infolet syntax: [!q:name]
    """

    priority = 40
    infolet_re = re.compile(r"\[!q:(?P<name>.*?)]", re.IGNORECASE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.infolet_re.sub(self._replace, html)

    def _replace(self, match: re.Match):
        name = match.group("name")
        item = Item.item_cache.get(name)
        if item and item.description:
            return f'<div class="tooltip">{name}<span class="tooltiptext">{item.description}</span></div>'
        return name
