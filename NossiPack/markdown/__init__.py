import markdown
from NossiPack.markdown.base import WikiEnvironment, NossiTag
import NossiPack.markdown.tags.glitch  # noqa: F401
import NossiPack.markdown.tags.transclude  # noqa: F401
import NossiPack.markdown.tags.checkbox  # noqa: F401
import NossiPack.markdown.tags.infolet  # noqa: F401
import NossiPack.markdown.tags.foldable  # noqa: F401
import NossiPack.markdown.tags.header_fix  # noqa: F401
import NossiPack.markdown.tags.clock  # noqa: F401
import NossiPack.markdown.tags.links  # noqa: F401


class NossiMarkdownProcessor:
    def __init__(self):
        self.tags = NossiTag.registry

    def render(self, raw_text: str, page_name: str) -> str:
        env = WikiEnvironment(page_name, raw_text)

        # 1. Run Pre-processors
        text = raw_text
        for tag in self.tags:
            text = tag.pre_process(text, env)

        # 2. Markdown Core
        html = markdown.markdown(text, extensions=["nl2br", "tables", "toc"])

        env.html_content = html

        # 3. Run Post-processors
        for tag in self.tags:
            html = tag.post_process(html, env)

        return html

    def process(self, text: str, page: str) -> str:
        return self.render(text, page)
