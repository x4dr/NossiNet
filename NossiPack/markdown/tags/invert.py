import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class InvertTag(NossiTag):
    """
    Invert text colors: `i~text~i`

    Wraps text in a span that inverts the foreground and background colors.

    Examples:
      i~this text is inverted~i
    """

    priority = 15
    tag_id = "invert"
    syntax = "i~text~i"
    description = "Invert foreground and background colors for text"
    example = "i~this text is inverted~i"
    category = "text"
    pattern = r"i(~{1,2})([^~]+)\1i"
    re_invert = re.compile(r"i(~{1,2})([^~]+)\1i")

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.re_invert.sub(
            lambda m: f'<span class="invert">{m.group(2)}</span>',
            html,
        )
