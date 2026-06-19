"""Inline progress clock tags for wiki markdown."""

import re

from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment
from NossiSite.socks import generate_clock


class ClockTag(NossiTag):
    """Inline progress clock: `[clock|name|current|total]` or `[clock|name@pagename]`.

    Renders a clickable HTMX-powered progress clock element.
    Linked clocks reference another page's clock by name.

    Examples:
      [clock|progress|3|8]
      [clock|health|5|6]

    """

    priority = 70
    tag_id = "clock"
    syntax = "[clock|name|current|total] or [clock|name@pagename]"
    description = "Interactive progress clock with clickable segments"
    example = "[clock|progress|3|8]"
    category = "interactive"
    clock_re = re.compile(r"\[clock\|(?P<name>.*?)\|(?P<current>\d+)\|(?P<total>\d+)]")
    linked_clock_re = re.compile(r"\[clock\|(?P<name>.*?)@(?P<page>.*?)]")

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        """Replace clock syntax with rendered progress clock HTML.

        Processes both inline clocks ``[clock|name|current|total]`` and
        linked clocks ``[clock|name@pagename]``.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment.

        Returns:
            HTML with clock placeholders replaced by clickable clock elements.
        """
        html = self.linked_clock_re.sub(lambda m: self._replace_linked(m, env), html)
        return self.clock_re.sub(
            lambda m: generate_clock(
                int(m.group("current")),
                int(m.group("total")),
                m.group("name"),
                env.page_name,
                initial=True,
            ),
            html,
        )

    def _replace_linked(self, match: re.Match[str], env: WikiEnvironment) -> str:  # noqa: ARG002
        """Resolve a linked clock reference from another page.

        Args:
            match: The regex match for the linked clock pattern.
            env: The current rendering environment (unused).

        Returns:
            HTML for the rendered linked clock, or a default empty clock
            if the source page or clock cannot be found.
        """
        try:
            wiki_page = WikiPage.load_locate(match.group("page"))
        except Exception:
            wiki_page = None

        if wiki_page:
            clock = wiki_page.get_clock(match.group("name"))
            if clock:
                return generate_clock(
                    int(clock.group("current")),
                    int(clock.group("maximum")),
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
