import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from NossiSite.socks import generate_clock
from gamepack.WikiPage import WikiPage


class ClockTag(NossiTag):
    """
    Inline progress clock: `[clock|name|current|total]` or `[clock|name@pagename]`

    Renders a clickable HTMX-powered progress clock element.
    Linked clocks reference another page's clock by name.

    Examples:
      [clock|progress|3|8]
      [clock|health|5|6]
    """

    priority = 70
    clock_re = re.compile(r"\[clock\|(?P<name>.*?)\|(?P<current>\d+)\|(?P<total>\d+)]")
    linked_clock_re = re.compile(r"\[clock\|(?P<name>.*?)@(?P<page>.*?)]")

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        html = self.linked_clock_re.sub(lambda m: self._replace_linked(m, env), html)
        return self.clock_re.sub(
            lambda m: generate_clock(
                m.group("current"),
                m.group("total"),
                m.group("name"),
                env.page_name,
                initial=True,
            ),
            html,
        )

    def _replace_linked(self, match: re.Match, env: WikiEnvironment) -> str:
        try:
            wiki_page = WikiPage.load_locate(match.group("page"))
        except Exception:
            wiki_page = None

        if wiki_page:
            clock = wiki_page.get_clock(match.group("name"))
            if clock:
                return generate_clock(
                    clock.group("current"),
                    clock.group("maximum"),
                    match.group("name"),
                    match.group("page"),
                    initial=True,
                )

        return generate_clock(
            0,
            1,
            match.group("name"),
            match.group("page"),
            initial=True,
        )
