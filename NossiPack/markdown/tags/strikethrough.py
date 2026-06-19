"""Strikethrough support via ~~text~~ syntax."""

import re

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class StrikethroughTag(NossiTag):
    """Convert ~~text~~ to <del>text</del> in rendered HTML."""

    priority = 5
    tag_id = "strikethrough"
    syntax = "~~text~~"
    description = "Strikethrough text via ~~text~~"
    example = "~~deleted~~"
    category = "text"
    pattern = r"~~.+?~~"
    re_strikethrough = re.compile(r"~~(.+?)~~")

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace ~~text~~ with <del>text</del> in safe HTML."""
        return self.re_strikethrough.sub(r"<del>\1</del>", html)
