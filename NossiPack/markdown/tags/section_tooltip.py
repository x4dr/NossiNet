import re

from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.WikiPage import WikiPage

TOOLTIP_EMBED_THRESHOLD = 500


class SectionTooltipTag(NossiTag):
    priority = 25
    tag_id = "section-tooltip"
    syntax = "[!t:pagename] or [!t:pagename#heading|Text]"
    description = "Hover tooltip showing content from another page or section"
    example = "[!t:demo#transclusion|See transclusion]"
    category = "content"
    pattern = r"\[!t:(?P<spec>[^\]]+?)\]"
    flags = "i"

    tooltip_re = re.compile(r"\[!t:(?P<spec>[^\]]+?)\]", re.IGNORECASE)
    _rendering: set[str] = set()
    _content_stack: list[list[tuple[str, str]]] = []
    _counter: int = 0

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        self._content_stack.append([])
        html = self.tooltip_re.sub(self._render_trigger, html)

        pending = self._content_stack.pop()
        if pending:
            tips = "\n".join(
                f'<div class="tip-content" id="tip-{tid}" hidden>{content}</div>'
                for tid, content in pending
            )
            html = html + "\n" + tips
        return html

    def _render_trigger(self, match: re.Match) -> str:
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
        self, page_name: str, heading: str | None, text: str | None, match: re.Match
    ) -> str:
        locator = page_name
        if heading:
            locator = f"{page_name}#{heading}"

        raw_markdown = WikiPage.resolve_address(locator)
        if raw_markdown is None:
            return match.group(0)

        if text is None:
            page = WikiPage.load_locate(page_name)
            if page:
                text = page.title or page_name
            else:
                text = page_name

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
