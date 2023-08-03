from pathlib import Path
from typing import Self

import bleach
from gamepack.FenCharacter import FenCharacter

from NossiPack.WikiPage import WikiPage


class WikiCharacterSheet(WikiPage):
    def __init__(
        self, title: str, tags: list[str], body: str, links: list[str], meta: list[str]
    ):
        super().__init__(title, tags, body, links, meta)
        self.char = FenCharacter.from_md(bleach.clean(self.body))

    @classmethod
    def from_wikipage(cls, page: WikiPage) -> Self:
        return cls(page.title, page.tags, page.body, page.links, page.meta)

    @classmethod
    def load(cls, page: [str | Path]) -> Self:
        p = WikiPage.load(page)
        if isinstance(p, WikiCharacterSheet):
            return p
        elif p:
            WikiPage.page_cache[page] = cls.from_wikipage(p)
            return WikiPage.page_cache[page]
