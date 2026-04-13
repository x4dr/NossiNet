import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.WikiPage import WikiPage


class TranscludeTag(NossiTag):
    """
    Handles transclusion syntax: ![text](page)
    Fetches content from another wiki page and inserts it.
    """

    priority = 20

    transclude_re = re.compile(r"!\[(?P<text>.*?)]\((?P<link>.*?)\)", re.IGNORECASE)

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        return self.transclude_re.sub(self._transclude, text)

    def _transclude(self, match: re.Match):
        pagename = match.group("link")
        try:
            page = WikiPage.load_locate(pagename)
            return page.body
        except:
            return match.group(0)
