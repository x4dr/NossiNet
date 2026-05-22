import re

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
import NossiPack.markdown.tags.section_tooltip  # noqa: F401


class NossiMarkdownProcessor:
    _code_pre_re = re.compile(r"<code[^>]*>.*?</code>|<pre[^>]*>.*?</pre>", re.DOTALL)

    def __init__(self):
        self.tags = NossiTag.registry

    @classmethod
    def _protect_code(cls, html: str) -> tuple[str, dict[str, str]]:
        protected: dict[str, str] = {}
        counter = 0

        def _stash(match):
            nonlocal counter
            counter += 1
            key = f"\x00CODE_{counter}_\x00"
            protected[key] = match.group(0)
            return key

        return cls._code_pre_re.sub(_stash, html), protected

    @staticmethod
    def _restore_code(html: str, protected: dict[str, str]) -> str:
        for key, original in protected.items():
            html = html.replace(key, original)
        return html

    _cross_line_emphasis_re = re.compile(r"(?<!\*)\*([^* \n][^*]*?\n[^*]*?)\*(?!\*)")

    @classmethod
    def _escape_cross_line_emphasis(cls, text: str) -> str:
        return cls._cross_line_emphasis_re.sub(lambda m: f"\\*{m.group(1)}\\*", text)

    def render(self, raw_text: str, page_name: str) -> str:
        env = WikiEnvironment(page_name, raw_text)

        # 1. Run Pre-processors
        text = raw_text
        for tag in self.tags:
            text = tag.pre_process(text, env)

        # 1.5. Escape cross-line emphasis
        text = self._escape_cross_line_emphasis(text)

        # 2. Markdown Core
        html = markdown.markdown(text, extensions=["nl2br", "tables", "toc"])

        env.html_content = html

        # 3. Protect code/pre blocks from post-processors
        html, protected = self._protect_code(html)

        # 4. Run Post-processors
        for tag in self.tags:
            html = tag.post_process(html, env)

        # 5. Restore code/pre blocks
        html = self._restore_code(html, protected)

        return html

    def process(self, text: str, page: str) -> str:
        return self.render(text, page)
