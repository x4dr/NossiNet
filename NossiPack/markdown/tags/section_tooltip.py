"""Section-based hover tooltips for wiki markdown."""

import re
from typing import ClassVar

from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment

TOOLTIP_EMBED_THRESHOLD = 500


class DirectTooltipTag(NossiTag):
    r"""Direct tooltip: ``[!t:"content"|text]``.

    Renders a hover tooltip trigger with inline static content, no
    page/section lookup required.
    """

    priority = 24
    tag_id = "direct-tooltip"
    syntax = '[!t:"content"|text]'
    description = "Hover tooltip with direct inline text content"
    example = '[!t:"This is the tooltip text"|hover me]'
    category = "content"

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """No-op — ``LinkedTooltipTag`` handles all ``[!t:...]`` processing."""
        return html


class LinkedTooltipTag(NossiTag):
    """Linked tooltip: ``[!t:pagename]`` or ``[!t:pagename#heading|Text]``.

    Renders a hover tooltip trigger that fetches content from another
    page or section via ``/render/<locator>`` at runtime.
    """

    priority = 25
    tag_id = "linked-tooltip"
    syntax = "[!t:pagename] or [!t:pagename#heading|Text]"
    description = "Hover tooltip showing content from a linked page or section"
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

        Page-based tooltips use ``data-tip="{locator}"`` for runtime
        loading via ``/render/<locator>``. Static quoted tooltips are
        embedded inline.

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
        """Render a single section tooltip match."""
        spec = match.group("spec")
        page_name, heading, text, is_static = self._parse_spec(spec)

        if is_static:
            result = self._embed_static(page_name, text)
            return result if result is not None else match.group(0)

        if page_name in LinkedTooltipTag._rendering:
            return text or heading.capitalize() if heading else page_name

        LinkedTooltipTag._rendering.add(page_name)
        try:
            return self._render_locator(page_name, heading, text, match)
        finally:
            LinkedTooltipTag._rendering.discard(page_name)

    def _embed_static(self, content: str, text: str | None) -> str | None:
        """Render statically embedded content as an inline tooltip."""
        from NossiPack.markdown import NossiMarkdownProcessor

        if text is None:
            text = content
        proc = NossiMarkdownProcessor()
        rendered = proc.render(content, "tooltip")
        tip_id = f"stip-{LinkedTooltipTag._counter}"
        LinkedTooltipTag._counter += 1
        self._content_stack[-1].append((tip_id, rendered))
        return f'<span class="tip-trigger" data-tip="{tip_id}">{text}</span>'

    def _render_locator(
        self,
        page_name: str,
        heading: str | None,
        text: str | None,
        match: re.Match[str],
    ) -> str:
        """Render a page-based tooltip trigger with dynamic content loading.

        Always uses ``data-tip="{locator}"`` so the client-side
        tooltip system fetches rendered content from
        ``/render/<locator>`` at runtime.

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
            if heading:
                text = heading.capitalize()
            else:
                page = WikiPage.load_locate(page_name)
                text = page.title or page_name if page else page_name

        return f'<span class="tip-trigger" data-tip="{locator}">{text}</span>'

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
