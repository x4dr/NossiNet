"""Tests for NossiNet markdown processing features."""

import re
from unittest.mock import MagicMock, patch

from NossiPack.markdown import NossiMarkdownProcessor


def test_transclude() -> None:
    """Basic page transclusion renders the wrapped content."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "# Transcluded Content"
        mock_load.return_value = mock_page

        result = processor.render("before\n\n[!page]\n\nafter", "testpage")
        assert '<div class="transcluded">' in result
        assert "Transcluded Content" in result
        assert "before" in result
        assert "after" in result


def test_transclude_scoping() -> None:
    """Transcluded content is wrapped, parent content stays outside."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## Transcluded\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Before\nstuff\n\n[!page]\n\n### After\nmore",
            "testpage",
        )
        assert '<div class="transcluded">' in result
        assert "<h3>Before" in result or '<h3 id="before">Before' in result
        assert "<h3>After" in result or '<h3 id="after">After' in result
        assert "<h2>Transcluded" in result or '<h2 id="transcluded">Transcluded' in result


def test_transclude_h2_in_h3_context() -> None:
    """Transcluded h2 inside parent h3 should be scoped to wrapper."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## Subpage\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Parent\nbefore\n\n[!subpage]\n\nmore",
            "testpage",
        )
        before_wrapper = result.split('<div class="transcluded">')[0]
        assert "<h3" in before_wrapper or '<h3 id="parent">Parent' in result


def test_transclude_h1_in_h3_context() -> None:
    """Transcluded h1 inside parent h3 section."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "# Big Heading\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Small\nbefore\n\n[!page]\n\n### After\nmore",
            "testpage",
        )
        assert '<div class="transcluded">' in result
        assert "<h1" in result or '<h1 id="big-heading">Big Heading' in result


def test_transclude_foldable_scoped() -> None:
    """Foldable inside transcluded content should close inside wrapper."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## !Hidden\nfolded content\n\nmore\n\n## Next\noutside"
        mock_load.return_value = mock_page

        result = processor.render(
            "Parent before\n\n[!page]\n\nParent after",
            "testpage",
        )
        # The foldable div should close before the wrapper </div>
        transcluded_section = result.split('<div class="transcluded">')[1].split(
            "</div>",
        )[0]
        assert '<div class="hiding"' in transcluded_section
        assert "Parent after" not in transcluded_section


def test_multiple_transcludes() -> None:
    """Multiple transclusions each get their own wrapper."""
    processor = NossiMarkdownProcessor()
    bodies = {"alpha": "## Alpha\ncontent", "beta": "## Beta\ncontent"}
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.side_effect = lambda name: MagicMock(body=bodies.get(name, ""))
        result = processor.render("[!alpha]\n\nbetween\n\n[!beta]", "testpage")
        assert result.count('<div class="transcluded">') == 2


def test_transclude_section() -> None:
    """Transclude a specific section via #fragment."""
    processor = NossiMarkdownProcessor()
    body = """# Main
content

## Details
secret info

## Other
stuff"""
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("before\n\n[!page#details|text]\n\nafter", "testpage")
        assert '<div class="transcluded">' in result
        assert "secret info" in result
        assert "stuff" not in result


def test_transclude_section_rename() -> None:
    """Transclude a section and rename its heading via alt text."""
    processor = NossiMarkdownProcessor()
    body = """# Main

## Details
secret info"""
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("[!page#details|Fun Fact]", "testpage")
        assert "Fun Fact" in result
        assert "secret info" in result


def test_transclude_section_nonexistent() -> None:
    """If fragment doesn't match, transclude syntax is left as-is."""
    processor = NossiMarkdownProcessor()
    body = "# Main\n\n## Details\ninfo"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("[!page#nope|text]", "testpage")
        assert '<div class="transcluded">' not in result


def test_transclude_section_top_level() -> None:
    """Transclude a top-level # heading section."""
    processor = NossiMarkdownProcessor()
    body = """# Top
top content

## Sub
sub content"""
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("[!page#top|text]", "testpage")
        assert "top content" in result
        assert "sub content" in result


def test_transclude_section_with_foldable() -> None:
    """Section transclusion with a foldable heading inside."""
    processor = NossiMarkdownProcessor()
    body = """## !Hidden
folded

## Other
visible"""
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("[!page#hidden]", "testpage")
        assert 'class="hider"' in result
        assert "folded" in result
        assert "visible" not in result


def test_section_tooltip() -> None:
    """Section tooltip renders trigger span with data-tip locator."""
    processor = NossiMarkdownProcessor()
    body = "# Source\n\ncontent\n\n## Details\nsecret"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Source")
        result = processor.render("[!t:Source]", "test")
        assert 'class="tip-trigger"' in result
        assert 'data-tip="Source"' in result
        assert "Source" in result
        assert 'class="tip-content"' not in result


def test_section_tooltip_fragment() -> None:
    """Section tooltip with fragment uses data-tip with locator."""
    processor = NossiMarkdownProcessor()
    body = "# Page\n\n## Details\nhidden\n\n## Other\nvisible"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#details]", "test")
        assert 'data-tip="Page#details"' in result
        assert "hidden" not in result


def test_section_tooltip_rename() -> None:
    """Section tooltip with alt text renames the heading."""
    processor = NossiMarkdownProcessor()
    body = "## Details\ninfo"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#details|Fun Fact]", "test")
        assert "Fun Fact" in result
        assert "info" not in result


def test_section_tooltip_self_reference() -> None:
    """Tooltip referencing the current page must not loop."""
    processor = NossiMarkdownProcessor()
    body = "## Section\ncontent [!t:Page] more [!t:Page#section]"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render(body, "Page")
        assert "[!t:" not in result
        assert "TIP_PLACEHOLDER_" not in result


def test_section_tooltip_placeholder_does_not_wipe_outer() -> None:
    """Nested tooltip renders must not destroy outer placeholders."""
    processor = NossiMarkdownProcessor()
    inner_body = "inner content [!t:OtherPage]"
    outer_body = "outer [!t:InnerPage]"
    pages = {
        "OuterPage": MagicMock(body=outer_body, title="OuterPage"),
        "InnerPage": MagicMock(body=inner_body, title="InnerPage"),
        "OtherPage": MagicMock(body="target", title="OtherPage"),
    }
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.side_effect = lambda name: pages.get(name)
        result = processor.render("[!t:OuterPage]", "test")
        assert "[!t:" not in result
        assert 'data-tip="OuterPage"' in result


def test_section_tooltip_cycle() -> None:
    """A→B→A cycle must not loop or produce raw syntax."""
    processor = NossiMarkdownProcessor()
    a_body = "Page A has [!t:PageB]"
    b_body = "Page B has [!t:PageA]"
    pages = {
        "PageA": MagicMock(body=a_body, title="PageA"),
        "PageB": MagicMock(body=b_body, title="PageB"),
    }
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.side_effect = lambda name: pages.get(name)
        result = processor.render("[!t:PageA]", "test")
        assert "[!t:" not in result
        assert 'data-tip="PageA"' in result


def test_transclude_recursion_limit() -> None:
    """Recursive transclusion must not produce raw syntax or infinite nesting.

    PageA has [!PageB], PageB has [!PageA]. The depth limit of 5 must:
    1. Not produce raw [! syntax in output
    2. Produce at most 5 levels of transclusion divs
    """
    processor = NossiMarkdownProcessor()
    from NossiPack.markdown.tags.transclude import TranscludeTag

    TranscludeTag._depth = 0

    pages = {
        "PageA": MagicMock(body="PageA has [!PageB]"),
        "PageB": MagicMock(body="PageB has [!PageA]"),
    }
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.side_effect = lambda name: pages.get(name)
        result = processor.render("[!PageA]", "test")

    assert "[!Page" not in result, "No raw transclude syntax should be visible"
    count = result.count('<div class="transcluded">')
    assert count <= 5, f"Expected ≤5 transclusion divs, got {count}"


def test_glitch() -> None:
    """Glitch syntax renders a span with glitch class and data-text."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="hello"' in result


def test_checkbox() -> None:
    """Checkbox syntax renders an HTML checkbox input."""
    processor = NossiMarkdownProcessor()
    result = processor.render("- [x] done", "testpage")
    assert 'type="checkbox"' in result
    assert "checked" in result


def test_infolet() -> None:
    """Infolet tag renders an item tooltip with description."""
    processor = NossiMarkdownProcessor()
    with patch(
        "gamepack.Item.Item.item_cache",
        {"test": MagicMock(description="desc")},
    ):
        result = processor.render("[!q:test]", "testpage")
        assert 'class="tip-trigger"' in result
        assert 'data-tip="iq-' in result
        assert "desc" in result


def test_foldable_spans() -> None:
    """Foldable headings produce hider and hiding span classes."""
    processor = NossiMarkdownProcessor()
    content = "# Main\n## !hidden\ncontent"
    result = processor.render(content, "testpage")
    assert 'class="hider"' in result
    assert 'class="hiding"' in result


def test_link_validation() -> None:
    """Existing wiki links are resolved; broken links get a missing class."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.locate") as mock_locate:
        mock_locate.return_value = True
        result = processor.render('<a href="exists">Link</a>', "testpage")
        assert 'href="/wiki/exists"' in result

        mock_locate.return_value = False
        result = processor.render('<a href="broken">Link</a>', "testpage")
        assert 'class="missing"' in result


def test_clock() -> None:
    """Clock syntax renders a clock container with data attributes."""
    processor = NossiMarkdownProcessor()
    result = processor.render("[clock|name@page]", "testpage")
    assert 'class="clock-container' in result
    assert 'data-total="1"' in result


def test_foldable_id_unique() -> None:
    """Two foldables with same heading text must have different IDs."""
    processor = NossiMarkdownProcessor()
    from NossiPack.markdown.tags.foldable import FoldableTag

    FoldableTag._counter = 0
    result = processor.render("## !Foldable\ncontent\n\n## !Foldable\nmore", "testpage")
    ids = re.findall(r'data-for="([^"]+)"', result)
    assert len(ids) == 2
    assert ids[0] != ids[1]


def test_glitch_dual_text_not_side_by_side() -> None:
    """g~Text A~Text B~g must NOT show both texts as visible content."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~Text A~Text B~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="Text B"' in result
    assert "Text A" in result
    assert ">Text B<" not in result


def test_glitch_separate_spans() -> None:
    """g~hello~g — g~world~W0RLD~g must produce two separate spans."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g — g~world~W0RLD~g", "testpage")
    spans = re.findall(r'<span class="glitch"', result)
    assert len(spans) == 2
    assert 'data-text="hello"' in result
    assert 'data-text="W0RLD"' in result
    assert "hello" in result
    assert "world" in result


def test_checkbox_in_code_block() -> None:
    """Checkbox syntax inside inline code must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`- [ ] unfinished`", "testpage")
    assert 'type="checkbox"' not in result
    assert "- [ ] unfinished" in result


def test_checkbox_in_code_block_x() -> None:
    """Checkbox done syntax inside inline code must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`- [x] done`", "testpage")
    assert 'type="checkbox"' not in result
    assert "- [x] done" in result


def test_checkbox_outside_code_block() -> None:
    """Checkbox syntax outside code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("- [x] done", "testpage")
    assert 'type="checkbox"' in result
    assert "checked" in result


def test_glitch_inside_code() -> None:
    """Glitch syntax inside code blocks must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`g~hello~g`", "testpage")
    assert 'class="glitch"' not in result
    assert "&gt;" not in result  # no HTML-escaped brackets from failed matching


def test_glitch_outside_code() -> None:
    """Glitch syntax outside code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="hello"' in result


def test_fenced_code_block() -> None:
    """Triple-backtick fenced code blocks render as <pre><code>."""
    processor = NossiMarkdownProcessor()
    result = processor.render("```\ncode here\n```", "testpage")
    assert "<pre>" in result
    assert "<code>" in result
    assert "code here" in result


def test_fenced_code_protects_invert() -> None:
    """i~text~i inside fenced code block must not be inverted."""
    processor = NossiMarkdownProcessor()
    result = processor.render("```\ni~not inverted~i\n```", "testpage")
    assert 'class="invert"' not in result
    assert "i~not inverted~i" in result


def test_fenced_code_protects_glitch() -> None:
    """g~text~g inside fenced code block must not be glitched."""
    processor = NossiMarkdownProcessor()
    result = processor.render("```\ng~not glitched~g\n```", "testpage")
    assert 'class="glitch"' not in result


def test_invert() -> None:
    """i~text~i renders as <span class='invert'>."""
    processor = NossiMarkdownProcessor()
    result = processor.render("i~hello~i", "testpage")
    assert 'class="invert"' in result
    assert "hello" in result


def test_invert_inside_code() -> None:
    """i~text~i inside inline code must not be inverted."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`i~hello~i`", "testpage")
    assert 'class="invert"' not in result


def test_invert_outside_code() -> None:
    """i~text~i outside code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("i~hello~i", "testpage")
    assert 'class="invert"' in result


def test_fenced_code_adjacent_to_invert() -> None:
    """Fenced code block next to invert text must both render correctly."""
    processor = NossiMarkdownProcessor()
    result = processor.render("```\ncode\n```\n\ni~inverted~i", "testpage")
    assert "<pre>" in result
    assert 'class="invert"' in result


def test_fenced_code_protects_checkbox() -> None:
    """Checkbox syntax inside fenced code block must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("```\n- [ ] unfinished\n- [x] done\n```", "testpage")
    assert 'type="checkbox"' not in result
    assert "- [ ] unfinished" in result
    assert "- [x] done" in result


def test_checkbox_outside_fenced() -> None:
    """Checkbox syntax outside fenced code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("- [ ] task\n```\ncode\n```", "testpage")
    assert result.count('type="checkbox"') == 1


def test_tooltip_html_structure() -> None:
    """Tooltip must render trigger span with data-tip locator, no embedded content."""
    processor = NossiMarkdownProcessor()
    body = "## Section\ninner content"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#section]", "test")
        assert '<span class="tip-trigger"' in result
        assert 'data-tip="Page#section"' in result
        assert 'class="tip-content"' not in result


def test_transclude_missing_page_returns_original_syntax() -> None:
    """When WikiPage.load_locate returns None, the original syntax must be preserved.

    This guards against the None-path bug where .body is accessed without
    an explicit None check, relying on a broad except Exception instead.
    """
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = None

        result = processor.render("before\n\n[!nonexistent]\n\nafter", "testpage")

    assert "[!nonexistent]" in result
    assert '<div class="transcluded">' not in result


def test_strikethrough() -> None:
    """~~text~~ is converted to <del>text</del>."""
    processor = NossiMarkdownProcessor()
    result = processor.render("This is ~~deleted~~ text.", "testpage")
    assert "<del>deleted</del>" in result
    assert "~~deleted~~" not in result


def test_strikethrough_inside_markdown() -> None:
    """~~text~~ works inside bold/italic markdown formatting."""
    processor = NossiMarkdownProcessor()
    result = processor.render("**bold ~~strikethrough~~ text**", "testpage")
    assert "<del>strikethrough</del>" in result
    assert "<strong>" in result
