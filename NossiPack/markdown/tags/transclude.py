import re
from NossiPack.markdown.base import NossiTag, WikiEnvironment
from gamepack.WikiPage import WikiPage


class TranscludeTag(NossiTag):
    """
    Include content from another page: `[!pagename]`

    Fetches a wiki page and inserts it inline, rendered through the full
    markdown pipeline. Transcluded content wraps in a `.transcluded` div.

    Section transclusion: `[!pagename#heading]`
      Includes only content under a specific heading (matched case-insensitively).
      The foldable `!` prefix on headings is ignored for matching.

    Heading rename: `[!pagename#heading|New Name]`
      Renames the extracted heading. Use `[!pagename#heading]` (no `|`) to keep original.

    Display text: `[!pagename|Text]`
      Sets display text for the transclusion link (only meaningful with `#heading`).

    Examples:
      [!endworld/mecha/systems/tables#heavy-shield|Heavy Shield Table]
      [!demo#demo-foldable]
    """

    priority = 20

    transclude_re = re.compile(
        r"\[!(?![tq]:)(?P<page>[^#|\]]+?)(?:#(?P<fragment>[^|\]]*?))?(?:\|(?P<text>[^\]]*?))?\]"
    )
    heading_re = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$", re.MULTILINE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:
        return self.transclude_re.sub(self._transclude, html)

    def _extract_section(self, body: str, fragment: str) -> str | None:
        target = fragment.lower().replace("-", " ")
        lines = body.split("\n")

        for i, line in enumerate(lines):
            m = self.heading_re.match(line)
            if not m:
                continue
            level = len(m.group(1))
            text = m.group(2).strip()
            text = re.sub(r"^!\s*", "", text).lower()
            if text == target:
                section_lines = [line]
                for j in range(i + 1, len(lines)):
                    next_m = self.heading_re.match(lines[j])
                    if next_m and len(next_m.group(1)) <= level:
                        break
                    section_lines.append(lines[j])
                return "\n".join(section_lines)
        return None

    def _rename_heading(self, body: str, new_title: str) -> str:
        return self.heading_re.sub(lambda m: f"{m.group(1)} {new_title}", body, count=1)

    def _transclude(self, match: re.Match):
        pagename = match.group("page").strip()
        fragment = match.group("fragment")
        text = match.group("text")

        if not pagename:
            return match.group(0)

        if fragment:
            fragment = fragment.strip()
        if text:
            text = text.strip()

        try:
            page = WikiPage.load_locate(pagename)
            body = page.body

            if fragment:
                body = self._extract_section(body, fragment)
                if body is None:
                    return match.group(0)

            if text and fragment:
                body = self._rename_heading(body, text)

            from NossiPack.markdown import NossiMarkdownProcessor

            proc = NossiMarkdownProcessor()
            rendered = proc.render(body, pagename)
            return f'\n<div class="transcluded">\n{rendered}\n</div>\n'
        except Exception:
            return match.group(0)
