import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class HeaderFixTag(NossiTag):
    """
    Multi-line header fix (automatic).

    If a heading tag spans multiple lines in the HTML (e.g. from long content
    with line-breaks), only the first line stays inside the <h...> tag.
    The remaining lines are moved outside.
    """

    priority = 60
    # Match headers with content that spans multiple lines
    header_re = re.compile(
        r"<(?P<h>h\d*)\b(?P<extra>[^>]*)>(?P<content>.*?)</(?P=h)\b[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.header_re.sub(self._fix_header, html)

    def _fix_header(self, match: re.Match):
        content = match.group("content")
        if "\n" not in content:
            return match.group(0)

        # Keep only the first line in the header, append the rest after
        lines = content.splitlines()
        return (
            f"<{match.group('h')} {match.group('extra')}>"
            f"{lines[0]}</{match.group('h')}>" + "\n".join(lines[1:])
        )
