from bs4 import BeautifulSoup
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.WikiPage import WikiPage
from urllib.parse import urlparse


class LinkValidatorTag(NossiTag):
    """
    Validates wiki links, marking broken ones and fixing internal paths.
    """

    priority = 80

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            parsed = urlparse(href)
            # Only validate relative internal links
            if not parsed.scheme and not href.startswith("#"):
                target = href.rsplit("#")[0]
                if target and not WikiPage.locate(target):
                    a["class"] = a.get("class", []) + ["missing"]
                else:
                    a["href"] = "/wiki/" + href
        return str(soup)
