"""Tests for the NossiMarkdownProcessor and NossiTag priority system."""

import re
from pathlib import Path

import pytest
from gamepack.WikiPage import WikiPage

from NossiPack.markdown import NossiMarkdownProcessor
from NossiPack.markdown.base import NossiTag, WikiEnvironment

# Fixture page backing the transclusion and tooltip assertions. Written to a
# throwaway wiki root so the real ~/wiki is never read, let alone written.
FIXTURE_PAGE = """---
tags: []
title: Fixture
---
# Transclusion

## Target Section

Target body text.
"""

# Covers every tag type the wiki is expected to render.
FIXTURE_MARKDOWN = """# Fixture

## Glitch Text

g~hello~g and g~world~W0RLD~g

## Section Tooltip

Hover [!t:fixture#Target Section] here.

## Transclusion

Body: [!fixture#Target Section]

## Infolet

[!q:itemname]

## Clock

[clock|progress|3|8]

## Checkbox

- [ ] unfinished
- [x] completed

## Strikethrough

~~struck~~ text.

## !Foldable Section

collapsed body
"""


def test_nossi_markdown_processor() -> None:
    """Verify custom pre-processing and post-processing tags are applied during rendering."""

    # Define tags inside the test so they don't get imported globally by accident
    # but they still trigger __init_subclass__
    class ReverseTag(NossiTag):
        priority = 999

        def pre_process(self, text: str, env: WikiEnvironment) -> str:  # noqa: ARG002
            return text[::-1]

    class AppendTag(NossiTag):
        priority = 1000

        def post_process(self, html: str, env: WikiEnvironment) -> str:  # noqa: ARG002
            return html + "<p>appended</p>"

    try:
        processor = NossiMarkdownProcessor()
        # "Hello" reversed is "olleH", which is a valid MD string
        # Then processed into <p>olleH</p>
        # Then appended
        result = processor.render("Hello", "testpage")
        assert "olleH" in result
        assert "<p>appended</p>" in result
    finally:
        # Clean up global registry to not break other tests
        NossiTag.registry[:] = [t for t in NossiTag.registry if not isinstance(t, (ReverseTag, AppendTag))]


def test_priority_conflict() -> None:
    """Verify that registering two tags with the same priority raises ValueError."""
    chosen = 1234
    occupied = [t.priority for t in NossiTag.registry]
    assert chosen not in occupied, f"Priority {chosen} is already taken by a real tag; pick another"

    class ConflictTag1(NossiTag):
        priority = chosen

    try:
        with pytest.raises(ValueError, match="Priority conflict"):

            class ConflictTag2(NossiTag):
                priority = chosen

    finally:
        NossiTag.registry[:] = [t for t in NossiTag.registry if not isinstance(t, ConflictTag1)]


@pytest.fixture
def rendered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Render the fixture markdown against a throwaway wiki.

    Writes the fixture page into a temporary directory and redirects
    ``_wikipath`` plus the page cache at it, so the test neither reads nor
    writes the developer's real ``~/wiki``. ``monkeypatch`` restores both
    attributes afterwards.

    Args:
        tmp_path: pytest-provided temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Rendered HTML for ``FIXTURE_MARKDOWN``.
    """
    (tmp_path / "fixture.md").write_text(FIXTURE_PAGE, encoding="utf8")
    monkeypatch.setattr(WikiPage, "_wikipath", tmp_path)
    monkeypatch.setattr(WikiPage, "page_cache", {})
    return NossiMarkdownProcessor().process(FIXTURE_MARKDOWN, page="fixture")


def test_glitch_tag_renders_data_text(rendered: str) -> None:
    """Both glitch syntaxes produce span.glitch carrying the data-text attribute."""
    glitches = re.findall(r'<span class="glitch" data-text="([^"]*)">([^<]*)</span>', rendered)
    assert len(glitches) == 2, f"Expected 2 glitch spans, found {len(glitches)} in {rendered}"
    assert sorted(text for _, text in glitches) == ["hello", "world"]
    assert sorted(data for data, _ in glitches) == ["W0RLD", "hello"]


def test_section_tooltip_renders_locator_trigger(rendered: str) -> None:
    """A page-based tooltip renders a tip-trigger pointing at its locator."""
    trigger = re.search(r'<span class="tip-trigger" data-tip="([^"]*)">([^<]*)</span>', rendered)
    assert trigger is not None, f"No tip-trigger span rendered in {rendered}"
    assert trigger.group(1) == "fixture#Target Section"
    assert "Target section" in trigger.group(2)
    assert "[!t:" not in rendered


def test_transclusion_renders_nested_div(rendered: str) -> None:
    """A section transclusion inlines the target page's content in a .transcluded div."""
    assert '<div class="transcluded">' in rendered
    assert '<h2 id="target-section">Target Section</h2>' in rendered
    assert "Target body text." in rendered
    assert "[!fixture" not in rendered


def test_infolet_falls_back_to_plain_name(rendered: str) -> None:
    """An item missing from the database degrades to its bare name."""
    assert "itemname" in rendered
    assert "[!q:" not in rendered


def test_clock_tag_renders_progress(rendered: str) -> None:
    """An inline clock renders one container carrying the current/total values."""
    clocks = re.findall(
        r'<div class="clock-container" data-active="(\d+)"[^>]*data-total="(\d+)"',
        rendered,
    )
    assert clocks == [("3", "8")], f"Unexpected clock values: {clocks}"


def test_checkbox_tag_renders_task_list(rendered: str) -> None:
    """Task list items render as checkbox inputs, with the done one pre-checked."""
    boxes = re.findall(r"<input[^>]*type=\"checkbox\"[^>]*/?>", rendered)
    assert len(boxes) == 2, f"Expected 2 checkboxes, found {len(boxes)}"
    assert sum('checked=""' in box for box in boxes) == 1, "Exactly one checkbox should be pre-checked"


def test_strikethrough_tag_renders_del(rendered: str) -> None:
    """The ~~strikethrough~~ syntax renders a <del> element."""
    assert "<del>struck</del>" in rendered
    assert "~~" not in rendered


def test_foldable_heading_renders_hider(rendered: str) -> None:
    """A heading prefixed with ! renders as a collapsible .hider."""
    assert re.search(r'<h2 class="hider"[^>]*>Foldable Section</h2>', rendered) is not None
    assert '<div class="hiding"' in rendered
