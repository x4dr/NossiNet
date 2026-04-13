import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class ClockTag(NossiTag):
    """
    Handles clock syntax: [clock|name@page]
    Injects HTMX-powered clock elements.
    """

    priority = 70
    clock_re = re.compile(r"\[clock\|(?P<name>.*?)@(?P<page>.*?)]")

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        return self.clock_re.sub(self._replace_clock, text)

    def _replace_clock(self, match: re.Match):
        name = match.group("name")
        page = match.group("page")
        # In a real scenario, use encode_id from base_ext if necessary
        return (
            f'<div id="parent-{name}-{page}" '
            f'hx-ws="connect:/ws_active_element?name={name}&page={page}" >'
            f'<div id="{name}-{page}">Loading {name}</div></div>'
        )
