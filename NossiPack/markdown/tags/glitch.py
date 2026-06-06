import re
from html import escape
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class GlitchTag(NossiTag):
    """
    Glitch text effect: `g~text~g` or `g~text~replacement~g`

    Wraps text in a cyberpunk-style glitch animation.
    The second form sets a different replacement text on hover / data attribute.

    Examples:
      g~hello~g
      g~world~W0RLD~g
    """

    priority = 10
    re_glitch = re.compile(r"g~([^~]+)~(?:(?:([^~]+)~g)|g)")

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.re_glitch.sub(
            lambda m: (
                f'<span class="glitch" data-text="{escape(m.group(2) or m.group(1))}">'
                f"{m.group(1)}</span>"
            ),
            html,
        )
