import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class FoldableTag(NossiTag):
    """
    Collapsible sections: prefix a heading with `!`: `## !Heading`

    The content following the heading is hidden by default.
    Click the heading to expand / collapse.
    Foldables are scoped to end at the next heading of the same or higher level.
    Multiple foldables with identical heading text get unique IDs.

    Examples:
      ## !Demo Foldable
      This content starts collapsed.
    """

    priority = 50
    headline_re = re.compile(r"(<h(\d)[^>]*)>\s*!(.*?)\s*(</h\d+>)", re.IGNORECASE)
    _counter = 0

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        result = []
        last_end = 0

        for match in self.headline_re.finditer(html):
            result.append(html[last_end : match.start()])

            h_open, level_str, text, h_close = match.groups()
            level = int(level_str)
            FoldableTag._counter += 1
            header_id = f"id-{hash(text)}-{FoldableTag._counter}"

            result.append(
                f'{h_open} class="hider" data-for="{header_id}">{text}{h_close}'
                f'<div id="{header_id}" class="hiding">'
            )

            rest = html[match.end() :]
            next_boundary = re.search(rf"<h[1-{level}][^>]*>", rest, re.I)
            if next_boundary:
                result.append(rest[: next_boundary.start()])
                result.append("</div>")
                last_end = match.end() + next_boundary.start()
            else:
                result.append(rest)
                result.append("</div>")
                last_end = len(html)

        result.append(html[last_end:])
        return "".join(result)
