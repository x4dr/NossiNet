"""Section-based hover tooltips for wiki markdown."""

import re
from typing import ClassVar

from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment

TOOLTIP_EMBED_THRESHOLD = 500


class SectionTooltipTag(NossiTag):
    """Section tooltip: ``[!t:pagename]`` or ``[!t:pagename#heading|Text]``.

    Renders a hover tooltip showing rendered content from another page
    or a specific section within a page. Short content is embedded inline;
    longer content uses a deferred tooltip lookup.
    """

    priority = 25
    tag_id = "section-tooltip"
    syntax = "[!t:pagename] or [!t:pagename#heading|Text]"
    description = "Hover tooltip showing content from another page or section"
    example = "[!t:demo#transclusion|See transclusion]"
    category = "content"
    pattern = r"\[!t:(?P<spec>[^\]]+?)\]"
    flags = "i"

    tooltip_re = re.compile(r"\[!t:(?P<spec>[^\]]+?)\]", re.IGNORECASE)
    _rendering: ClassVar[set[str]] = set()
    _content_stack: ClassVar[list[list[tuple[str, str]]]] = []
    _counter: int = 0

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace section tooltip syntax with tooltip trigger HTML.

        Renders tooltip triggers and appends hidden tip-content divs
        at the end of the HTML.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with section tooltip placeholders replaced by triggers.
        """
        self._content_stack.append([])
        html = self.tooltip_re.sub(self._render_trigger, html)

        pending = self._content_stack.pop()
        if pending:
            tips = "\n".join(
                f'<div class="tip-content" id="tip-{tid}" hidden>{content}</div>' for tid, content in pending
            )
            html = html + "\n" + tips
        return html

    def _render_trigger(self, match: re.Match[str]) -> str:
        """Render a single section tooltip match.

        Handles static embedded content, circular-reference protection,
        and delegates to ``_render_locator`` for page-based tooltips.

        Args:
            match: The regex match for a section tooltip pattern.

        Returns:
            HTML for the tooltip trigger, or the original match text
            if rendering fails.
        """
        spec = match.group("spec")
        page_name, heading, text, is_static = self._parse_spec(spec)

        if is_static:
            result = self._embed_static(page_name, text)
            return result if result is not None else match.group(0)

        if page_name in SectionTooltipTag._rendering:
            return text or heading.capitalize() if heading else page_name

        SectionTooltipTag._rendering.add(page_name)
        try:
            return self._render_locator(page_name, heading, text, match)
        finally:
            SectionTooltipTag._rendering.discard(page_name)

    def _embed_static(self, content: str, text: str | None) -> str | None:
        """Render statically embedded content as an inline tooltip.

        Processes the content through the full markdown pipeline and
        stores it as a hidden tip-content div.

        Args:
            content: The raw markdown content to render.
            text: Optional display text for the trigger element.

        Returns:
            HTML for the tooltip trigger, or None if the content
            is empty.
        """
        from NossiPack.markdown import NossiMarkdownProcessor

        if text is None:
            text = content
        proc = NossiMarkdownProcessor()
        rendered = proc.render(content, "tooltip")
        tip_id = f"stip-{SectionTooltipTag._counter}"
        SectionTooltipTag._counter += 1
        self._content_stack[-1].append((tip_id, rendered))
        return f'<span class="tip-trigger" data-tip="{tip_id}">{text}</span>'

    def _render_locator(
        self,
        page_name: str,
        heading: str | None,
        text: str | None,
        match: re.Match[str],
    ) -> str:
        """Render a page-based tooltip, embedding or deferring based on length.

        Args:
            page_name: The wiki page to pull content from.
            heading: Optional section heading within the page.
            text: Optional display text for the trigger element.
            match: The original regex match (returned on failure).

        Returns:
            HTML for the tooltip trigger element, or the original
            match text if the page cannot be found.
        """
        locator = page_name
        if heading:
            locator = f"{page_name}#{heading}"

        raw_markdown = WikiPage.resolve_address(locator)
        if raw_markdown is None:
            return match.group(0)

        if text is None:
            page = WikiPage.load_locate(page_name)
            text = page.title or page_name if page else page_name

        if len(raw_markdown) <= TOOLTIP_EMBED_THRESHOLD:
            from NossiPack.markdown import NossiMarkdownProcessor

            proc = NossiMarkdownProcessor()
            rendered = proc.render(raw_markdown, page_name)
            tip_id = f"stip-{SectionTooltipTag._counter}"
            SectionTooltipTag._counter += 1
            self._content_stack[-1].append((tip_id, rendered))
            return f'<span class="tip-trigger" data-tip="{tip_id}">{text}</span>'

        return f'<span class="tip-trigger" data-tooltip="{locator}">{text}</span>'

    def _parse_spec(self, spec: str) -> tuple[str, str | None, str | None, bool]:
        """Parse a tooltip specification string into its components.

        Handles formats:
        - ``pagename``
        - ``pagename#heading``
        - ``pagename#heading|Text``
        - ``"static content"`` (quoted = static embed)

        Args:
            spec: The raw specification string from inside ``[!t:...]``.

        Returns:
            A tuple of ``(page_or_content, heading, text, is_static)``.
        """
        text = None
        page_spec = spec

        if "|" in page_spec:
            page_spec, text = page_spec.rsplit("|", 1)
            page_spec = page_spec.strip()
            text = text.strip()

        if page_spec.startswith('"') and page_spec.endswith('"'):
            return page_spec[1:-1], None, text, True

        heading = None
        if "#" in page_spec:
            page_name, heading = page_spec.rsplit("#", 1)
            page_name = page_name.strip()
            heading = heading.strip()
        else:
            page_name = page_spec.strip()

        return page_name, heading, text, False
