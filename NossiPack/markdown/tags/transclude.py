"""Page transclusion and section inclusion for wiki markdown."""

import re

from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment


class TranscludeTag(NossiTag):
    """Include content from another page: `[!pagename]`.

    Fetches a wiki page and inserts it inline, rendered through the full
    markdown pipeline. Transcluded content wraps in a `.transcluded` div.

    Section transclusion: `[!pagename#heading]`
      Includes only content under a specific heading (matched case-insensitively).
      The foldable `!` prefix on headings is ignored for matching.

    Heading rename: `[!pagename#heading|New Name]`
      Renames the extracted heading. Use `[!pagename#heading]` (no `|`) to keep original.

    Display text: `[!pagename|Text]`
      Sets display text for the transclusion link (only meaningful with `#heading`).

    Recursion protection: depth counter with a hard limit of 5 nested levels.

    Examples:
      [!endworld/mecha/systems/tables#heavy-shield|Heavy Shield Table]
      [!demo#demo-foldable]

    """

    priority = 20
    _depth: int = 0
    _max_depth: int = 5
    tag_id = "transclude"
    syntax = "[!pagename] or [!pagename#heading|Text]"
    description = "Include content from another wiki page inline"
    example = "[!endworld/mecha/systems#heavy-shield|Heavy Shield Table]"
    category = "content"
    pattern = r"\[!(?![tq]:)(?P<page>[^#|\]]+?)(?:#(?P<fragment>[^|\]]*?))?(?:\|(?P<text>[^\]]*?))?\]"

    transclude_re = re.compile(
        r"\[!(?![tq]:)(?P<page>[^#|\]]+?)(?:#(?P<fragment>[^|\]]*?))?(?:\|(?P<text>[^\]]*?))?\]",
    )
    heading_re = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$", re.MULTILINE)

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Replace transclusion syntax with inline rendered page content.

        Processes ``[!pagename]``, ``[!pagename#heading|Text]`` patterns.

        Args:
            html: The rendered HTML content.
            env: The current rendering environment (unused).

        Returns:
            HTML with transclusion placeholders replaced by rendered
            page content wrapped in ``.transcluded`` divs.
        """
        return self.transclude_re.sub(self._transclude, html)

    def _extract_section(self, body: str, fragment: str) -> str | None:
        """Extract content under a specific heading from a page body.

        Headings are matched case-insensitively; the foldable ``!``
        prefix is stripped for comparison.

        Args:
            body: The full markdown body of the source page.
            fragment: The heading text to locate.

        Returns:
            The markdown content of the matching section, or None
            if no matching heading is found.
        """
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

    def _transclude(self, match: re.Match[str]) -> str:
        """Render a single transclusion match.

        Loads the target page, optionally extracts a section, renames
        the heading if requested, and renders through the full markdown
        pipeline. Includes recursion depth protection.

        Args:
            match: The regex match for a transclusion pattern.

        Returns:
            Rendered HTML wrapped in a ``.transcluded`` div, or the
            original match text on failure.
        """
        TranscludeTag._depth += 1
        try:
            if TranscludeTag._depth > TranscludeTag._max_depth:
                return ""

            pagename = match.group("page").strip()
            fragment = match.group("fragment")
            text = match.group("text")

            if not pagename:
                return match.group(0)

            if fragment:
                fragment = fragment.strip()
            if text:
                text = text.strip()

            page = WikiPage.load_locate(pagename)
            if page is None:
                return match.group(0)
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
        finally:
            TranscludeTag._depth -= 1
