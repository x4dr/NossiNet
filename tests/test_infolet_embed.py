"""Tests for the infolet embed syntax: [[info]], ![[info]] and [name[[info]]].

Covers the ``specific:`` locator and its heading selector, the three container
forms, and the marker used for locator types that have no resolver yet.

Every test renders against a throwaway wiki so the real ``~/wiki`` is untouched.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from gamepack.WikiPage import WikiPage

from NossiPack.markdown import NossiMarkdownProcessor

SOURCE_PAGE = """---
tags: []
title: Source
---
# Source

Intro paragraph.

## Feuer

Fire spell body.

### Detail

Nested detail body.

## Wasser

Water body.
"""

CURRENT_PAGE = """---
tags: []
title: Current
---
# Current

## Wasser

Local body.
"""


@pytest.fixture
def render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    """Install a throwaway wiki and return a markdown rendering callable.

    Args:
        tmp_path: pytest-provided temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Callable taking markdown and an optional page name.
    """
    (tmp_path / "sourcepage.md").write_text(SOURCE_PAGE, encoding="utf8")
    (tmp_path / "currentpage.md").write_text(CURRENT_PAGE, encoding="utf8")
    monkeypatch.setattr(WikiPage, "_wikipath", tmp_path)
    monkeypatch.setattr(WikiPage, "page_cache", {})

    processor = NossiMarkdownProcessor()

    def _render(markdown_text: str, page: str = "currentpage") -> str:
        return processor.process(markdown_text, page=page)

    return _render


def test_headed_embed_uses_name_as_summary(render: Callable[..., str]) -> None:
    """[name[[info]]] renders a details block summarised by name."""
    out = render("[Feuer[[specific:sourcepage:Feuer:-]]]")
    assert '<details class="infolet-fold">' in out
    assert "<summary>Feuer</summary>" in out
    assert "Fire spell body." in out


def test_headed_embed_without_colon_keeps_heading(render: Callable[..., str]) -> None:
    """A selector without a trailing ``:-`` keeps the heading itself."""
    out = render("[Feuer[[specific:sourcepage:Feuer]]]")
    assert "<summary>Feuer</summary>" in out
    assert "Feuer</h2>" in out
    assert "Fire spell body." in out


def test_triple_bracket_embed_has_empty_summary(render: Callable[..., str]) -> None:
    """[[[info]]] is the empty-name form and renders no summary text."""
    out = render("[[[specific:sourcepage:Wasser]]]")
    assert '<details class="infolet-fold">' in out
    assert "<summary></summary>" in out
    assert "Water body." in out


def test_bare_embed_inserts_inline(render: Callable[..., str]) -> None:
    """[[info]] inserts the resolved content without a details wrapper."""
    out = render("[[specific:sourcepage:Wasser:-]]")
    assert "<details" not in out
    assert "<p>Water body.</p>" in out


def test_inline_embed_is_not_nested_in_a_paragraph(render: Callable[..., str]) -> None:
    """Block content substituted inline must not end up inside a wrapping <p>."""
    out = render("[[specific:sourcepage:Wasser:-]]")
    assert "<p><p>" not in out
    assert "</p></p>" not in out


def test_bang_embed_summarises_with_the_resolved_heading(render: Callable[..., str]) -> None:
    """![[info]] folds the content and names the summary after the heading."""
    out = render("![[specific:sourcepage:Wasser]]")
    assert "<summary>Wasser</summary>" in out
    assert "Water body." in out


def test_nested_selector_looks_inside_the_parent_heading(render: Callable[..., str]) -> None:
    """``a:b:c`` selects c within b rather than anywhere on the page."""
    out = render("[[specific:sourcepage:Feuer:Detail:-]]")
    assert "Nested detail body." in out
    assert "Fire spell body." not in out


def test_section_stops_at_the_next_heading_of_same_or_higher_level(render: Callable[..., str]) -> None:
    """A section runs up to the next heading of the same or a higher level."""
    out = render("[[specific:sourcepage:Feuer:-]]")
    assert "Fire spell body." in out
    # h3 Detail is a lower level, so it belongs to the Feuer section.
    assert "Nested detail body." in out
    # h2 Wasser is the same level, so it must not.
    assert "Water body." not in out


def test_dash_page_searches_the_current_page_first(render: Callable[..., str]) -> None:
    """A page of ``-`` resolves against the page being rendered."""
    out = render("[[specific:-:Wasser:-]]")
    assert "Local body." in out


def test_heading_match_ignores_case_and_foldable_prefix(render: Callable[..., str]) -> None:
    """Heading lookup is case insensitive and ignores the foldable ``!``."""
    out = render("[[specific:sourcepage:WASSER:-]]")
    assert "Water body." in out


@pytest.mark.parametrize(
    "locator",
    [
        "weapon:Dolch:L10HSCB",
        "armor:Brustplatte:",
        "q:sourcepage:Wasser",
    ],
)
def test_locator_types_without_a_resolver_render_a_marker(render: Callable[..., str], locator: str) -> None:
    """weapon:, armor: and q: have no resolver and say so instead of vanishing.

    Args:
        render: Markdown rendering callable.
        locator: Locator with no resolver.
    """
    out = render(f"[[{locator}]]")
    assert 'class="infolet-unresolved"' in out
    assert locator in out


def test_missing_page_renders_a_marker(render: Callable[..., str]) -> None:
    """A specific: locator naming a page that does not exist says so."""
    out = render("[[specific:nosuchpage:Wasser]]")
    assert 'class="infolet-unresolved"' in out


def test_missing_heading_renders_a_marker(render: Callable[..., str]) -> None:
    """A specific: locator naming a heading that does not exist says so."""
    out = render("[[specific:sourcepage:Nope]]")
    assert 'class="infolet-unresolved"' in out


def test_multiple_embeds_on_one_page_all_resolve(render: Callable[..., str]) -> None:
    """Placeholder bookkeeping survives several embeds in one document."""
    out = render(
        "[Feuer[[specific:sourcepage:Feuer:-]]]\n\n[Wasser[[specific:sourcepage:Wasser:-]]]\n\n[[specific:sourcepage:Nope]]",
    )
    assert "Fire spell body." in out
    assert "Water body." in out
    assert out.count('class="infolet-unresolved"') == 1
    assert "nossiInfoletEmbedTOKEN" not in out


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("[Feuer[[specific:sourcepage:Feuer:-]]]", "specific:sourcepage:Feuer:-"),
        ("[[[weapon:Dolch]]]", "weapon:Dolch"),
        ("[[weapon:Dolch:]]", "weapon:Dolch:"),
        ("![[specific:sourcepage:Wasser]]", "specific:sourcepage:Wasser"),
        ("[[specific:sourcepage:Wasser:-]]", "specific:sourcepage:Wasser:-"),
    ],
)
def test_extract_locator_reads_every_container_form(raw: str, expected: str) -> None:
    """The inner locator is recovered from each of the container syntaxes.

    Args:
        raw: Full matched text as the editor sends it.
        expected: Locator that should be extracted.
    """
    from NossiPack.markdown.tags.infolet_embed import InfoletEmbedTag

    processor = NossiMarkdownProcessor()
    tag = next(t for t in processor.tags if isinstance(t, InfoletEmbedTag))
    assert tag.extract_locator(raw) == expected


def test_extract_locator_rejects_non_embeds() -> None:
    """Text that is not an infolet embed yields no locator."""
    from NossiPack.markdown.tags.infolet_embed import InfoletEmbedTag

    processor = NossiMarkdownProcessor()
    tag = next(t for t in processor.tags if isinstance(t, InfoletEmbedTag))
    assert tag.extract_locator("just some text") is None
    assert tag.extract_locator("[!page#heading]") is None


WEAPON_PAGE = """---
tags: []
title: Weapons
---
# Weapons

### Dolch

| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hacken](damage#h-Hacken)        | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 4 | 6 |
| [Stechen](damage#p-stechen)      | 1 | 1;1 | 1;2 | 1;3 | 1;4 | 1;6 | 5;5 | 6;5 | 7;6 | 8;8 |
| [Schneiden](weapons#c-schneiden) | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 8 |
| [Schlagen](damage#b-stumpf)      | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 5 |

### Hammer

| Wert                             | 1 | 2 |
|---|:---:|:---:|
| [Hacken](damage#h-Hacken)        | 2 | 4 |
| [Schlagen](damage#b-stumpf)      | 3 | 7 |
"""


@pytest.fixture
def weapon_wiki(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    """Install a throwaway wiki holding a weapons page and return a renderer.

    Args:
        tmp_path: pytest-provided temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Callable taking markdown and an optional page name.
    """
    (tmp_path / "weapons.md").write_text(WEAPON_PAGE, encoding="utf8")
    monkeypatch.setattr(WikiPage, "_wikipath", tmp_path)
    monkeypatch.setattr(WikiPage, "page_cache", {})

    processor = NossiMarkdownProcessor()

    def _render(markdown_text: str, page: str = "current") -> str:
        return processor.process(markdown_text, page=page)

    return _render


def _selected_cells(html: str) -> tuple[list[str], list[str]]:
    """Return the selected column headers and cell values from rendered HTML.

    Args:
        html: Rendered HTML.

    Returns:
        Tuple of (selected column headers, selected cell values).
    """
    headers = re.findall(r'<th class="waffenmod-selected">([^<]*)</th>', html)
    values = re.findall(r'<td class="waffenmod-selected">([^<]*)</td>', html)
    return headers, values


def test_weapon_locator_renders_the_damage_table(weapon_wiki: Callable[..., str]) -> None:
    """[[weapon:name:mods]] renders the weapon's table with the selection marked."""
    html = weapon_wiki("[[weapon:Dolch:L10HSCB]]")
    assert '<div class="waffenmod">' in html
    assert "Dolch" in html
    assert _selected_cells(html) == (["10"], ["6", "8;8", "8", "5"])


def test_weapon_mods_select_only_the_named_damage_codes(weapon_wiki: Callable[..., str]) -> None:
    """Only the rows named by the codes are rendered."""
    html = weapon_wiki("[[weapon:Dolch:L10B]]")
    assert "Schlagen" in html
    assert "Hacken" not in html
    assert _selected_cells(html) == (["10"], ["5"])


def test_weapon_left_count_indexes_from_the_left(weapon_wiki: Callable[..., str]) -> None:
    """L<count> selects column <count> counting from the left."""
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:L1H]]")) == (["1"], ["1"])
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:L5H]]")) == (["5"], ["2"])


def test_weapon_right_count_indexes_from_the_right(weapon_wiki: Callable[..., str]) -> None:
    """R<count> selects the column <count> places from the right."""
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:R1H]]")) == (["10"], ["6"])
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:R2H]]")) == (["9"], ["4"])


def test_weapon_count_clamps_to_the_table_length(weapon_wiki: Callable[..., str]) -> None:
    """Counts past either end clamp rather than erroring."""
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:L99H]]")) == (["10"], ["6"])
    assert _selected_cells(weapon_wiki("[[weapon:Dolch:R99H]]")) == (["1"], ["1"])


def test_weapon_count_clamps_to_a_short_table(weapon_wiki: Callable[..., str]) -> None:
    """Clamping uses the table's real length, not a fixed ten columns."""
    assert _selected_cells(weapon_wiki("[[weapon:Hammer:L10H]]")) == (["2"], ["4"])
    assert _selected_cells(weapon_wiki("[[weapon:Hammer:R1H]]")) == (["2"], ["4"])


def test_weapon_without_mods_shows_the_last_column(weapon_wiki: Callable[..., str]) -> None:
    """An empty mod string selects the last column and every damage code."""
    html = weapon_wiki("[[weapon:Dolch:]]")
    assert _selected_cells(html) == (["10"], ["6", "8;8", "8", "5"])


def test_weapon_comma_separated_mods(weapon_wiki: Callable[..., str]) -> None:
    """Several mods select several columns at once."""
    html = weapon_wiki("[[weapon:Dolch:L1H,L10H]]")
    assert _selected_cells(html) == (["1", "10"], ["1", "6"])


def test_unknown_weapon_renders_a_marker(weapon_wiki: Callable[..., str]) -> None:
    """A weapon with no table is reported rather than silently dropped."""
    html = weapon_wiki("[[weapon:NoSuchWeapon:L10H]]")
    assert 'class="infolet-unresolved"' in html


def test_malformed_weapon_mod_renders_a_marker(weapon_wiki: Callable[..., str]) -> None:
    """A mod that does not match the documented shape is reported."""
    html = weapon_wiki("[[weapon:Dolch:XYZ]]")
    assert 'class="infolet-unresolved"' in html


def test_selector_tolerates_an_empty_trailing_component(render: Callable[..., str]) -> None:
    """``zauber::-`` drops the heading with no nested selector, like ``zauber:-``."""
    out = render("[[specific:sourcepage:Wasser::-]]")
    assert "<p>Water body.</p>" in out
    assert "Wasser</h2>" not in out
