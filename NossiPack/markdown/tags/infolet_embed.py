"""Infolet embeds: ``[[info]]``, ``![[info]]`` and ``[name[[info]]]``.

Implements the infolet syntax documented in the wiki's ``conventions.md``:

======================================  ==========================================
``[[info]]``                            inserts the resolved content inline
``![[info]]``                           inserts it as a collapsible ``<details>``
``[name[[info]]]``                      collapsible with ``name`` as the summary
``[[[info]]]``                          collapsible with an empty summary
======================================  ==========================================

The inner locator is typed:

* ``specific:page:selector`` — a heading on another page, with the section read
  up to the next heading of the same or higher level
* ``weapon:name:mods`` — a weapon's damage table from the ``weapons`` page
* ``q:...`` — no resolver exists yet

A ``specific:`` selector is ``a:b`` to find heading ``b`` on the page, or
``a:b:c`` to find ``b`` first and then ``c`` within it. A trailing ``:-`` drops
the heading itself, keeping only the body. A page of ``-`` searches the current
page, then ``prices``, then ``items``.

Weapon mods follow ``conventions.md``: ``L<count><codes>`` counts from the left
and ``R<count><codes>`` from the right, both clamped to the table's real length.
``<codes>`` is any of ``H`` (Hacken), ``S`` (Stechen), ``C`` (Schneiden) and
``B`` (Schlagen). Several mods are comma separated. Only the selected damage
rows are rendered, with the selected column marked.

Locators that cannot be resolved render as a visible ``.infolet-unresolved``
marker rather than being left as literal text, so the gap is visible instead of
silent.
"""

import re
from functools import partial
from html import escape
from typing import ClassVar

from gamepack.WikiPage import WikiPage

from NossiPack.markdown.base import NossiTag, WikiEnvironment

#: Page search order used when a ``specific:`` locator names the page ``-``.
FALLBACK_PAGES = ("prices", "items")

#: Locator types that have no resolver yet. Kept explicit so ``/tag-validate``
#: and this tag agree on what counts as unresolved.
UNRESOLVED_TYPES = ("q",)

#: Locator types that have a resolver.
RESOLVABLE_TYPES = ("specific", "weapon")

#: Page holding the weapon damage tables.
WEAPON_PAGE = "weapons"

#: Damage code to the row label it selects, in the order conventions.md uses.
DAMAGE_CODES = {"H": "Hacken", "S": "Stechen", "C": "Schneiden", "B": "Schlagen"}

#: A single weapon mod, e.g. ``L10HSCB`` or ``R2B``.
_MOD_RE = re.compile(r"(?P<direction>[LR])(?P<count>\d+)(?P<codes>[HSCB]+)")

#: Placeholder swapped in before the markdown converter runs. The resolved HTML
#: is substituted afterwards, so a section made of block level elements does not
#: end up nested inside the paragraph the markdown converter wrapped it in.
#: Plain alphanumerics on purpose: control characters get stripped in transit.
_TOKEN_PREFIX = "nossiInfoletEmbedTOKEN"
_TOKEN_SUFFIX = "ENDTOKEN"
_TOKEN = _TOKEN_PREFIX + "{}" + _TOKEN_SUFFIX

# A paragraph whose entire content is the placeholder loses the paragraph, since
# the substituted HTML brings its own block structure. Built from the escaped
# prefix/suffix rather than the template, whose braces are not a valid regex.
_TOKEN_PARAGRAPH = re.compile(
    rf"<p>\s*{re.escape(_TOKEN_PREFIX)}\d+{re.escape(_TOKEN_SUFFIX)}\s*</p>",
)


class InfoletEmbedTag(NossiTag):
    """Infolet embeds that inline or fold a section of another wiki page.

    See the module docstring for the accepted syntax.
    """

    priority = 22
    tag_id = "infolet-embed"
    syntax = "[[info]] / [name[[info]]]"
    description = "Insert a wiki section inline or as a collapsible block"
    example = "[Herz stoppen[[specific:ideas/lifemagic:Herz stoppen:-]]]"
    category = "content"
    # Mirrors the three container regexes exactly, so the text the editor
    # decorates is the same text extract_locator can parse. Group-free so it is
    # also a valid JavaScript RegExp in the editor's decorator.
    pattern = (
        r"\[[^[\]]*\[\[(?:specific|weapon|q):[^[\]]*\]\]\]"
        r"|!\[\[(?:specific|weapon|q):[^[\]]*\]\]"
        r"|\[\[(?:specific|weapon|q):[^[\]]*\]\]"
    )

    # Ordered most specific first. A bare [[info]] would otherwise be carved out
    # of [name[[info]]] or [[[info]]], leaving a stray bracket behind.
    headed_re = re.compile(r"\[(?P<name>[^\[\]]*)\[\[(?P<info>[^\[\]]*)\]\]\]")
    bang_re = re.compile(r"!\[\[(?P<info>[^\[\]]*)\]\]")
    bare_re = re.compile(r"\[\[(?P<info>[^\[\]]*)\]\]")

    heading_re = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$", re.MULTILINE)
    # Pre-rendered replacements, one frame per processor run. Strictly LIFO
    # because a nested render reuses this same tag instance.
    _pending: ClassVar[list[list[str]]] = []
    _depth: int = 0
    _max_depth: int = 5

    def pre_process(self, text: str, env: WikiEnvironment) -> str:
        """Swap infolet embeds for placeholders and render their content.

        Runs before the markdown converter so the resolved HTML is inserted
        after conversion, which keeps block level output from being nested
        inside an auto-generated paragraph.

        Args:
            text: Raw markdown source.
            env: The current rendering environment.

        Returns:
            Markdown with embeds replaced by placeholders.
        """
        frame: list[str] = []
        InfoletEmbedTag._pending.append(frame)
        for regex, style in (
            (self.headed_re, "headed"),
            (self.bang_re, "bang"),
            (self.bare_re, "bare"),
        ):
            substitute = partial(self._placeholder, env=env, style=style, frame=frame)
            text = regex.sub(substitute, text)
        return text

    def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
        """Put rendered embeds back in place of their placeholders.

        Args:
            html: HTML produced by the markdown converter.
            env: The current rendering environment (unused).

        Returns:
            HTML with embeds replaced by inline content or ``<details>`` blocks.
        """
        frame = InfoletEmbedTag._pending.pop() if InfoletEmbedTag._pending else []
        for index, replacement in enumerate(frame):
            placeholder = _TOKEN.format(index)

            def whole_paragraph(_match: re.Match[str], value: str = replacement) -> str:
                return value

            html = _TOKEN_PARAGRAPH.sub(whole_paragraph, html, count=1)
            html = html.replace(placeholder, replacement)
        return html

    def _placeholder(
        self,
        match: re.Match[str],
        *,
        env: WikiEnvironment,
        style: str,
        frame: list[str],
    ) -> str:
        """Record a rendered embed and return its placeholder.

        Args:
            match: The regex match for an infolet embed.
            env: The current rendering environment.
            style: One of ``headed``, ``bang`` or ``bare``.
            frame: Collects rendered replacements for this processor run.

        Returns:
            The placeholder string to substitute into the markdown.
        """
        info = match.group("info").strip()
        resolved = self._resolve(info, env.page_name)
        if resolved is None:
            frame.append(self._unresolved(info))
        else:
            heading, rendered = resolved
            if style == "bare":
                frame.append(rendered)
            else:
                label = match.group("name").strip() if style == "headed" else heading
                frame.append(f'<details class="infolet-fold"><summary>{escape(label)}</summary>{rendered}</details>')
        return _TOKEN.format(len(frame) - 1)

    def extract_locator(self, raw: str) -> str | None:
        """Pull the inner locator out of a full infolet embed match.

        Used by ``/tag-validate``, which receives the whole matched text from
        the editor rather than the locator on its own.

        Args:
            raw: Full matched text, e.g. ``[Name[[specific:page:Heading:-]]]``.

        Returns:
            The inner locator, or None if the text is not an infolet embed.
        """
        for regex in (self.headed_re, self.bang_re, self.bare_re):
            match = regex.fullmatch(raw.strip())
            if match:
                return match.group("info").strip()
        return None

    def can_resolve(self, info: str, current_page: str) -> bool:
        """Report whether a locator resolves, without rendering it.

        Used by ``/tag-validate`` to flag unresolvable locators in the editor.

        Args:
            info: Raw locator text.
            current_page: Page being rendered, for the ``-`` page fallback.

        Returns:
            True if the locator resolves to a section.
        """
        return self._resolve(info, current_page) is not None

    def _resolve(self, info: str, current_page: str) -> tuple[str, str] | None:
        """Resolve a typed locator to its heading and rendered content.

        Args:
            info: Raw locator text, e.g. ``specific:ideas/lifemagic:Herz stoppen:-``.
            current_page: Page being rendered, for the ``-`` page fallback.

        Returns:
            Tuple of (heading text, rendered HTML), or None when the locator type
            has no resolver or the target could not be found.
        """
        if InfoletEmbedTag._depth > InfoletEmbedTag._max_depth:
            return None

        kind, separator, rest = info.partition(":")
        if not separator:
            return None
        kind = kind.strip().lower()
        if kind in UNRESOLVED_TYPES or kind not in RESOLVABLE_TYPES:
            return None

        InfoletEmbedTag._depth += 1
        try:
            if kind == "specific":
                return self._resolve_specific(rest, current_page)
            return self._resolve_weapon(rest)
        finally:
            InfoletEmbedTag._depth -= 1

    def _resolve_weapon(self, rest: str) -> tuple[str, str] | None:
        """Resolve a ``weapon:name:mods`` locator against the weapons page.

        Args:
            rest: Everything after ``weapon:``, i.e. ``name:mods``.

        Returns:
            Tuple of (weapon name, rendered damage table), or None if the weapon
            or its table is missing.
        """
        name, _, mods = rest.partition(":")
        name = name.strip()
        if not name:
            return None

        loaded = WikiPage.load_locate(WEAPON_PAGE)
        if loaded is None:
            return None
        found = self._find_section(loaded.body, name)
        if found is None:
            return None
        _, section = found

        table = self._parse_damage_table(section)
        if table is None:
            return None

        headers, rows = table
        if mods.strip():
            selected = self._parse_mods(mods, headers)
            if selected is None:
                return None
            columns, codes = selected
        else:
            columns = {len(headers) - 1}
            codes = set(DAMAGE_CODES)

        return name, self._render_damage_table(name, headers, rows, columns, codes)

    def _parse_damage_table(self, section: str) -> tuple[list[str], list[tuple[str, list[str]]]] | None:
        """Parse a weapon's damage table out of its wiki section.

        The table has a ``Wert`` header row of column numbers and one row per
        damage type, e.g. ``| [Hacken](damage#h-Hacken) | 1 | 2 | ... |``.

        Args:
            section: Markdown section of the weapon.

        Returns:
            Tuple of (column headers, [(row label, cell values)]), or None when
            the section holds no recognisable damage table.
        """
        headers: list[str] = []
        rows: list[tuple[str, list[str]]] = []

        for line in section.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells:
                continue
            first = cells[0]
            if first.lower() == "wert":
                headers = cells[1:]
                continue
            if set(first) <= set(":- "):
                continue
            rows.append((re.sub(r"\[([^\]]*)]\([^)]*\)", r"\1", first), cells[1:]))

        if not headers or not rows:
            return None
        return headers, rows

    def _parse_mods(self, mods: str, headers: list[str]) -> tuple[set[int], set[str]] | None:
        """Parse comma separated weapon mods into selected columns and codes.

        ``L<count><codes>`` counts from the left as ``[count]`` and
        ``R<count><codes>`` from the right as ``[-count]``, both clamped to the
        table's real length.

        Args:
            mods: Raw mod text, e.g. ``L10HSCB`` or ``L10HSCB,R2B``.
            headers: Column headers of the table being addressed.

        Returns:
            Tuple of (selected column indices, selected codes), or None if any
            mod is malformed.
        """
        length = len(headers)
        columns: set[int] = set()
        codes: set[str] = set()

        for part in mods.split(","):
            match = _MOD_RE.fullmatch(part.strip())
            if not match:
                return None
            count = int(match.group("count"))
            # L is [count] and R is [-count] in Python index terms, both clamped
            # to the table's real length.
            index = count - 1 if match.group("direction") == "L" else length - count
            columns.add(max(0, min(index, length - 1)))
            codes.update(match.group("codes"))

        if not columns or not codes:
            return None
        return columns, codes

    def _render_damage_table(
        self,
        name: str,
        headers: list[str],
        rows: list[tuple[str, list[str]]],
        columns: set[int],
        codes: set[str],
    ) -> str:
        """Render the selected damage rows, marking the selected column.

        Args:
            name: Weapon name, used as the caption.
            headers: Column headers of the source table.
            rows: Row label and cell values of the source table.
            columns: Selected column indices.
            codes: Selected damage codes.

        Returns:
            HTML for the trimmed damage table.
        """
        wanted = {DAMAGE_CODES[code] for code in codes if code in DAMAGE_CODES}
        parts = [f'<div class="waffenmod"><div class="waffenmod-name">{escape(name)}</div><table>']
        parts.append("<thead><tr><th></th>")
        for index, header in enumerate(headers):
            marker = ' class="waffenmod-selected"' if index in columns else ""
            parts.append(f"<th{marker}>{escape(header)}</th>")
        parts.append("</tr></thead><tbody>")

        for label, values in rows:
            if wanted and label not in wanted:
                continue
            parts.append(f"<tr><th>{escape(label)}</th>")
            for index in range(len(headers)):
                value = values[index] if index < len(values) else ""
                marker = ' class="waffenmod-selected"' if index in columns else ""
                parts.append(f"<td{marker}>{escape(value)}</td>")
            parts.append("</tr>")

        parts.append("</tbody></table></div>")
        return "".join(parts)

    def _resolve_specific(self, rest: str, current_page: str) -> tuple[str, str] | None:
        """Resolve a ``specific:`` locator.

        Args:
            rest: Everything after ``specific:``, i.e. ``page:selector``.
            current_page: Page being rendered, used when the page is ``-``.

        Returns:
            Tuple of (heading text, rendered HTML), or None if not found.
        """
        page, separator, selector = rest.partition(":")
        if not separator:
            return None
        page = page.strip()
        selector = selector.strip()
        if not page or not selector:
            return None

        drop_heading = False
        if selector.endswith(":-"):
            selector = selector[:-2].strip()
            drop_heading = True
        if not selector:
            return None

        candidates = (current_page, *FALLBACK_PAGES) if page == "-" else (page,)
        for candidate in candidates:
            loaded = WikiPage.load_locate(candidate)
            if loaded is None:
                continue
            found = self._extract_section(loaded.body, selector)
            if found is None:
                continue
            heading_line, section = found
            if drop_heading:
                _, _, section = section.partition("\n")
            match = self.heading_re.match(heading_line)
            heading = re.sub(r"^!\s*", "", match.group(2).strip()) if match else selector
            return heading, self._render_section(section, candidate)
        return None

    def _extract_section(self, body: str, selector: str) -> tuple[str, str] | None:
        """Find a (possibly nested) heading and return its section.

        Args:
            body: Markdown body of the source page.
            selector: Colon separated heading names, outermost first.

        Returns:
            Tuple of (heading line, section body including that heading), or None
            if any selector step is missing.
        """
        section = body
        heading = ""
        # Empty components are tolerated so ``zauber::-`` (drop the heading, no
        # nested selector) behaves the same as ``zauber:-``.
        for part in (p for p in selector.split(":") if p.strip()):
            found = self._find_section(section, part.strip())
            if found is None:
                return None
            heading, section = found
        if not heading:
            return None
        return heading, section

    def _find_section(self, body: str, heading_text: str) -> tuple[str, str] | None:
        """Locate the first heading matching ``heading_text`` and take its section.

        The section runs from the heading to the next heading of the same or a
        higher level. Matching ignores case and the foldable ``!`` prefix, and
        treats ``-`` as a space, matching the transclusion rules.

        Args:
            body: Markdown body to search.
            heading_text: Heading to find.

        Returns:
            Tuple of (heading line, section including the heading), or None.
        """
        target = self._normalise(heading_text)
        lines = body.split("\n")

        for i, line in enumerate(lines):
            m = self.heading_re.match(line)
            if not m:
                continue
            level = len(m.group(1))
            if self._normalise(m.group(2)) != target:
                continue
            section_lines = [line]
            for j in range(i + 1, len(lines)):
                next_m = self.heading_re.match(lines[j])
                if next_m and len(next_m.group(1)) <= level:
                    break
                section_lines.append(lines[j])
            return line, "\n".join(section_lines)
        return None

    def _normalise(self, text: str) -> str:
        """Normalise a heading for comparison.

        Args:
            text: Raw heading text, possibly with a foldable ``!`` prefix.

        Returns:
            Lowercased text with the prefix removed and ``-`` folded to spaces.
        """
        return re.sub(r"^!\s*", "", text.strip()).lower().replace("-", " ").strip()

    def _render_section(self, section: str, page_name: str) -> str:
        """Render extracted markdown through the full processor.

        Args:
            section: Markdown to render.
            page_name: Page name handed to the renderer for nested lookups.

        Returns:
            Rendered HTML.
        """
        from NossiPack.markdown import NossiMarkdownProcessor

        return NossiMarkdownProcessor().render(section, page_name)

    def _unresolved(self, info: str) -> str:
        """Render a locator that has no resolver.

        Args:
            info: The raw locator text.

        Returns:
            HTML marker naming the locator that could not be resolved.
        """
        return f'<span class="infolet-unresolved" title="No resolver for this infolet type">{escape(info)}</span>'
