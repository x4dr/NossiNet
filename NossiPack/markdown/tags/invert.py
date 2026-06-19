"""Inverted text color tags for wiki markdown."""

import re

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class InvertTag(NossiTag):
    """Invert text colors: `i~text~i`.

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

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace invert syntax with styled span elements.

        Transforms ``i~text~i`` patterns into
        ``<span class="invert">`` elements.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with invert placeholders replaced by styled spans.
        """
        return self.re_invert.sub(
            lambda m: f'<span class="invert">{m.group(2)}</span>',
            html,
        )
