import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from NossiSite.socks import generate_clock
from gamepack.WikiPage import WikiPage


class ClockTag(NossiTag):
    """
    Handles clock syntax: [clock|name|current|total] or [clock|name@page]
    Injects HTMX-powered clock elements.
    """

    priority = 70
    clock_re = re.compile(r"\[clock\|(?P<name>.*?)\|(?P<current>\d+)\|(?P<total>\d+)]")
    linked_clock_re = re.compile(r"\[clock\|(?P<name>.*?)@(?P<page>.*?)]")

    placeholder_re = re.compile(r"CLOCK_PLACEHOLDER_(\d+)")
    _placeholders = {}
    _counter = 0

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        self.env = env
        # Placeholder injection in pre-process
        text = self.linked_clock_re.sub(self._replace_placeholder_linked, text)
        return self.clock_re.sub(self._replace_placeholder, text)

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        # Replace placeholders with actual HTML
        return self.placeholder_re.sub(self._replace_final, html)

    def _replace_placeholder(self, match: re.Match):
        ClockTag._counter += 1
        placeholder = f"CLOCK_PLACEHOLDER_{ClockTag._counter}"
        ClockTag._placeholders[placeholder] = generate_clock(
            match.group("current"),
            match.group("total"),
            match.group("name"),
            self.env.page_name,
            initial=True,
        )
        return placeholder

    def _replace_placeholder_linked(self, match: re.Match):
        ClockTag._counter += 1
        placeholder = f"CLOCK_PLACEHOLDER_{ClockTag._counter}"
        # Resolve linked clock
        wiki_page = WikiPage.load_locate(match.group("page"))
        if wiki_page:
            clock = wiki_page.get_clock(match.group("name"))
            if clock:
                ClockTag._placeholders[placeholder] = generate_clock(
                    clock.group("current"),
                    clock.group("maximum"),
                    match.group("name"),
                    match.group("page"),
                    initial=True,
                )
            else:
                ClockTag._placeholders[placeholder] = generate_clock(
                    0, 1, match.group("name"), match.group("page"), initial=True
                )
        else:
            ClockTag._placeholders[placeholder] = generate_clock(
                0, 1, match.group("name"), match.group("page"), initial=True
            )
        return placeholder

    def _replace_final(self, match: re.Match):
        return ClockTag._placeholders.get(match.group(0), "")
