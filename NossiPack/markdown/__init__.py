"""Custom markdown processing pipeline with NossiNet-specific tag extensions."""

import re

import markdown

import NossiPack.markdown.tags.checkbox
import NossiPack.markdown.tags.clock
import NossiPack.markdown.tags.foldable
import NossiPack.markdown.tags.glitch
import NossiPack.markdown.tags.header_fix
import NossiPack.markdown.tags.infolet
import NossiPack.markdown.tags.invert
import NossiPack.markdown.tags.links
import NossiPack.markdown.tags.section_tooltip
import NossiPack.markdown.tags.transclude  # noqa: F401
from NossiPack.markdown.base import NossiTag, WikiEnvironment


class NossiMarkdownProcessor:
    """Orchestrates the full wiki markdown rendering pipeline.

    Applies tag pre-processors, runs the core markdown converter, then
    applies tag post-processors. Code and fenced blocks are protected
    from accidental modification at each stage.
    """

    _code_pre_re = re.compile(r"<code[^>]*>.*?</code>|<pre[^>]*>.*?</pre>", re.DOTALL)
    _fenced_block_re = re.compile(r"^```\w*\s*\n.*?^```\s*$", re.MULTILINE | re.DOTALL)

    def __init__(self) -> None:
        """Initialize the processor with the global NossiTag registry."""
        self.tags = NossiTag.registry

    @classmethod
    def _protect_code(cls, html: str) -> tuple[str, dict[str, str]]:
        protected: dict[str, str] = {}
        counter = 0

        def _stash(match: re.Match[str]) -> str:
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

    @classmethod
    def _protect_fenced(cls, text: str) -> tuple[str, dict[str, str]]:
        protected: dict[str, str] = {}
        counter = 0

        def _stash(match: re.Match[str]) -> str:
            nonlocal counter
            counter += 1
            key = f"\x00FENCED_{counter}_\x00"
            protected[key] = match.group(0)
            return key

        return cls._fenced_block_re.sub(_stash, text), protected

    @staticmethod
    def _restore_fenced(text: str, protected: dict[str, str]) -> str:
        for key, original in protected.items():
            text = text.replace(key, original)
        return text

    _cross_line_emphasis_re = re.compile(r"(?<!\*)\*([^* \n][^*]*?\n[^*]*?)\*(?!\*)")

    @classmethod
    def _escape_cross_line_emphasis(cls, text: str) -> str:
        return cls._cross_line_emphasis_re.sub(lambda m: f"\\*{m.group(1)}\\*", text)

    def render(self, raw_text: str, page_name: str) -> str:
        """Render wiki markdown through the full tag and markdown pipeline.

        Args:
            raw_text: The raw markdown source text.
            page_name: The name of the page being rendered (used for
                       environment context and link resolution).

        Returns:
            Fully rendered HTML with all tag extensions applied.
        """
        env = WikiEnvironment(page_name, raw_text)

        # 0. Protect fenced code blocks from pre-processors and cross-line emphasis
        text, fenced_protected = self._protect_fenced(raw_text)

        # 1. Run Pre-processors
        for tag in self.tags:
            text = tag.pre_process(text, env)

        # 1.5. Escape cross-line emphasis
        text = self._escape_cross_line_emphasis(text)

        # 1.6. Restore fenced code blocks
        text = self._restore_fenced(text, fenced_protected)

        # 2. Markdown Core
        html = markdown.markdown(
            text,
            extensions=["nl2br", "tables", "toc", "fenced_code"],
        )

        env.html_content = html

        # 3. Protect code/pre blocks from post-processors
        html, protected = self._protect_code(html)

        # 4. Run Post-processors
        for tag in self.tags:
            html = tag.post_process(html, env)

        # 5. Restore code/pre blocks
        return self._restore_code(html, protected)

    def process(self, text: str, page: str) -> str:
        """Render wiki markdown through the full pipeline.

        Convenience wrapper around ``render``.

        Args:
            text: The raw markdown source text.
            page: The name of the page being rendered.

        Returns:
            Fully rendered HTML.
        """
        return self.render(text, page)
