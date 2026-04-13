import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class FoldableTag(NossiTag):
    """
    Handles foldable header syntax: ## !hidden
    """

    priority = 50
    headline_re = re.compile(r"(<h\d+.*?>)\s*!(.*?)\s*(</h\d+>)", re.IGNORECASE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        # Simple replacement for foldable headers
        def _replace(match):
            h_open, text, h_close = match.groups()
            header_id = f"id-{hash(text)}"
            return f'{h_open} class="hider" data-for="{header_id}">{text}{h_close}<div id="{header_id}" class="hiding">'

        return self.headline_re.sub(_replace, html)
