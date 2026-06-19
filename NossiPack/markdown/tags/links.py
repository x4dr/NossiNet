"""Automatic wiki link validation and prefixing."""

from urllib.parse import urlparse

from bs4 import BeautifulSoup
from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class LinkValidatorTag(NossiTag):
    """Wiki link validation (automatic).

    Internal `<a href="pagename">` links get a /wiki/ prefix.
    If the target page does not exist the link gets a missing CSS class.
    External links and anchor-only links are left unchanged.
    """

    priority = 80
    tag_id = "link-validator"
    syntax = "(automatic)"
    description = "Validate wiki links and apply missing/valid classes"
    example = ""
    category = "internal"

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Validate wiki links and add appropriate CSS classes.

        Internal links get a ``/wiki/`` prefix. Links to non-existent
        pages get a ``missing`` CSS class. External and anchor-only
        links are left unchanged. Internal links also get a ``data-tip``
        attribute for hover preview tooltips.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with validated and prefixed wiki links.
        """
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            parsed = urlparse(href)
            # Only validate relative internal links
            if not parsed.scheme and isinstance(href, str) and not href.startswith("#"):
                target = href.rsplit("#")[0]
                if target and not WikiPage.locate(target):
                    a["class"] = [*a.get("class", []), "missing"]
                else:
                    a["href"] = "/wiki/" + href
                a["data-tip"] = href
        return str(soup)
