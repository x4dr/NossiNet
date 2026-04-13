import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class GlitchTag(NossiTag):
    """
    Handles glitch effect syntax: g~text~g or g~text~g~replacement~g
    Wraps content in a span with the .glitch class.
    """

    priority = 10
    re_glitch = re.compile(r"\bg~(.+?)(~(?P<text>.+?))?~g\b")

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.re_glitch.sub(
            lambda m: (
                f'<span class="glitch" data-text="{m.group("text") or m.group(1)}">{m.group(1)}</span>'
            ),
            html,
        )
