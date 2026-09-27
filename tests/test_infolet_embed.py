"""Tests for the infolet embed syntax: [[info]], ![[info]] and [name[[info]]].

Covers the ``specific:`` locator and its heading selector, the three container
forms, and the marker used for locator types that have no resolver yet.

Every test renders against a throwaway wiki so the real ``~/wiki`` is untouched.
"""

from __future__ import annotations

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
