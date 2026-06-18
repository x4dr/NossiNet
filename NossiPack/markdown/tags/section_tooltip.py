import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.WikiPage import WikiPage
from NossiPack.markdown.tags.transclude import TranscludeTag


class SectionTooltipTag(NossiTag):
    """
    Section tooltip: `[!t:pagename]`, `[!t:pagename#heading]`, `[!t:pagename|Text]`, `[!t:pagename#heading|Text]`

    Renders a hover tooltip showing transcluded page / section content on hover.
    Built-in cycle detection prevents infinite recursion.

    Examples:
      [!t:demo#transclusion]
      [!t:demo#transclusion|See transclusion]
    """

    priority = 25

    tooltip_re = re.compile(r"\[!t:(?P<spec>[^\]]+?)\]", re.IGNORECASE)
    _rendering: set[str] = set()

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.tooltip_re.sub(self._render, html)

    def _render(self, match: re.Match) -> str:
        spec = match.group("spec")
        page_name, heading, text = self._parse_spec(spec)

        if page_name in SectionTooltipTag._rendering:
            return text or heading.capitalize() if heading else page_name

        SectionTooltipTag._rendering.add(page_name)
        try:
            page = WikiPage.load_locate(page_name)
            if page is None:
                return match.group(0)

            body = page.body
            tc = TranscludeTag()

            if heading:
                extracted = tc._extract_section(body, heading)
                if extracted is None:
                    return match.group(0)
                body = extracted
                if text is None:
                    found = self._extract_heading_text(page.body, heading)
                    text = found or heading.capitalize()
            else:
                if text is None:
                    text = page.title or page_name

            from NossiPack.markdown import NossiMarkdownProcessor

            proc = NossiMarkdownProcessor()
            rendered = proc.render(body, page_name)
            return (
                f'<span class="tooltip">{text}'
                f'<div class="tooltiptext">{rendered}</div></span>'
            )
        except Exception:
            return match.group(0)
        finally:
            SectionTooltipTag._rendering.discard(page_name)

    def _parse_spec(self, spec: str) -> tuple[str, str | None, str | None]:
        text = None
        page_spec = spec
        if "|" in page_spec:
            page_spec, text = page_spec.rsplit("|", 1)
            page_spec = page_spec.strip()
            text = text.strip()

        heading = None
        if "#" in page_spec:
            page_name, heading = page_spec.rsplit("#", 1)
            page_name = page_name.strip()
            heading = heading.strip()
        else:
            page_name = page_spec.strip()

        return page_name, heading, text

    def _extract_heading_text(self, body: str, fragment: str) -> str | None:
        target = fragment.lower().replace("-", " ")
        heading_re = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$", re.MULTILINE)
        for line in body.split("\n"):
            m = heading_re.match(line)
            if m:
                text = m.group(2).strip()
                text = re.sub(r"^!\s*", "", text)
                if text.lower() == target:
                    return text
        return None
