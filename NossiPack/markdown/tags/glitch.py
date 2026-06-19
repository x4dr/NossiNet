"""Glitch text effect tags for wiki markdown."""

import re
from html import escape

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class GlitchTag(NossiTag):
    """Glitch text effect: `g~text~g` or `g~text~replacement~g`.

    Wraps text in a cyberpunk-style glitch animation.
    The second form sets a different replacement text on hover / data attribute.

    Examples:
      g~hello~g
      g~world~W0RLD~g

    """

    priority = 10
    tag_id = "glitch"
    syntax = "g~text~g"
    description = "Glitch text effect with optional replacement text"
    example = "g~hello~g or g~world~W0RLD~g"
    category = "text"
    pattern = r"g(~{1,2})([^~]+)\1(?:g|([^~]+)\1g)"
    re_glitch = re.compile(r"g(~{1,2})([^~]+)\1(?:g|([^~]+)\1g)")

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace glitch syntax with styled span elements.

        Transforms ``g~text~g`` and ``g~text~replacement~g`` patterns
        into ``<span class="glitch">`` elements with a data-text attribute.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with glitch placeholders replaced by styled spans.
        """
        return self.re_glitch.sub(
            lambda m: (f'<span class="glitch" data-text="{escape(m.group(3) or m.group(2))}">' f"{m.group(2)}</span>"),
            html,
        )
