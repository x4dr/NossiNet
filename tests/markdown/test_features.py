import re
from unittest.mock import MagicMock, patch
from NossiPack.markdown import NossiMarkdownProcessor


def test_transclude():
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


def test_transclude_scoping():
    """Transcluded content is wrapped, parent content stays outside."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## Transcluded\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Before\nstuff\n\n[!page]\n\n### After\nmore", "testpage"
        )
        assert '<div class="transcluded">' in result
        assert "<h3>Before" in result or '<h3 id="before">Before' in result
        assert "<h3>After" in result or '<h3 id="after">After' in result
        assert (
            "<h2>Transcluded" in result or '<h2 id="transcluded">Transcluded' in result
        )


def test_transclude_h2_in_h3_context():
    """Transcluded h2 inside parent h3 should be scoped to wrapper."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## Subpage\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Parent\nbefore\n\n[!subpage]\n\nmore", "testpage"
        )
        before_wrapper = result.split('<div class="transcluded">')[0]
        assert "<h3" in before_wrapper or '<h3 id="parent">Parent' in result


def test_transclude_h1_in_h3_context():
    """Transcluded h1 inside parent h3 section."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "# Big Heading\ncontent"
        mock_load.return_value = mock_page

        result = processor.render(
            "### Small\nbefore\n\n[!page]\n\n### After\nmore", "testpage"
        )
        assert '<div class="transcluded">' in result
        assert "<h1" in result or '<h1 id="big-heading">Big Heading' in result


def test_transclude_foldable_scoped():
    """Foldable inside transcluded content should close inside wrapper."""
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "## !Hidden\nfolded content\n\nmore\n\n## Next\noutside"
        mock_load.return_value = mock_page

        result = processor.render(
            "Parent before\n\n[!page]\n\nParent after", "testpage"
        )
        # The foldable div should close before the wrapper </div>
        transcluded_section = result.split('<div class="transcluded">')[1].split(
            "</div>"
        )[0]
        assert '<div class="hiding"' in transcluded_section
        assert "Parent after" not in transcluded_section


def test_multiple_transcludes():
    """Multiple transclusions each get their own wrapper."""
    processor = NossiMarkdownProcessor()
    bodies = {"alpha": "## Alpha\ncontent", "beta": "## Beta\ncontent"}
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.side_effect = lambda name: MagicMock(body=bodies.get(name, ""))
        result = processor.render("[!alpha]\n\nbetween\n\n[!beta]", "testpage")
        assert result.count('<div class="transcluded">') == 2


def test_transclude_section():
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


def test_transclude_section_rename():
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


def test_transclude_section_nonexistent():
    """If fragment doesn't match, transclude syntax is left as-is."""
    processor = NossiMarkdownProcessor()
    body = "# Main\n\n## Details\ninfo"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body)
        result = processor.render("[!page#nope|text]", "testpage")
        assert '<div class="transcluded">' not in result


def test_transclude_section_top_level():
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


def test_transclude_section_with_foldable():
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


def test_section_tooltip():
    processor = NossiMarkdownProcessor()
    body = "# Source\n\ncontent\n\n## Details\nsecret"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Source")
        result = processor.render("[!t:Source]", "test")
        assert 'class="tooltip"' in result
        assert 'class="tooltiptext"' in result
        assert "Source" in result
        assert "secret" in result


def test_section_tooltip_fragment():
    processor = NossiMarkdownProcessor()
    body = "# Page\n\n## Details\nhidden\n\n## Other\nvisible"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#details]", "test")
        assert "hidden" in result
        assert "visible" not in result


def test_section_tooltip_rename():
    processor = NossiMarkdownProcessor()
    body = "## Details\ninfo"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#details|Fun Fact]", "test")
        assert "Fun Fact" in result
        assert "info" in result


def test_section_tooltip_self_reference():
    """Tooltip referencing the current page must not loop."""
    processor = NossiMarkdownProcessor()
    body = "## Section\ncontent [!t:Page] more [!t:Page#section]"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render(body, "Page")
        assert "[!t:" not in result
        assert "TIP_PLACEHOLDER_" not in result


def test_section_tooltip_placeholder_does_not_wipe_outer():
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
        assert "TIP_PLACEHOLDER_" not in result
        assert "[!t:" not in result
        assert "outer" in result
        assert "inner content" in result
        assert "target" in result


def test_section_tooltip_cycle():
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
        assert "TIP_PLACEHOLDER_" not in result
        assert "Page A has" in result


def test_glitch():

    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="hello"' in result


def test_checkbox():
    processor = NossiMarkdownProcessor()
    result = processor.render("- [x] done", "testpage")
    assert 'type="checkbox"' in result
    assert "checked" in result


def test_infolet():
    processor = NossiMarkdownProcessor()
    with patch(
        "gamepack.Item.Item.item_cache", {"test": MagicMock(description="desc")}
    ):
        result = processor.render("[!q:test]", "testpage")
        assert 'class="tooltip"' in result
        assert "desc" in result


def test_foldable_spans():
    processor = NossiMarkdownProcessor()
    content = "# Main\n## !hidden\ncontent"
    result = processor.render(content, "testpage")
    assert 'class="hider"' in result
    assert 'class="hiding"' in result


def test_link_validation():
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.locate") as mock_locate:
        mock_locate.return_value = True
        result = processor.render('<a href="exists">Link</a>', "testpage")
        assert 'href="/wiki/exists"' in result

        mock_locate.return_value = False
        result = processor.render('<a href="broken">Link</a>', "testpage")
        assert 'class="missing"' in result


def test_clock():
    processor = NossiMarkdownProcessor()
    result = processor.render("[clock|name@page]", "testpage")
    assert 'class="clock-container' in result
    assert 'data-total="1"' in result


def test_foldable_id_unique():
    """Two foldables with same heading text must have different IDs."""
    processor = NossiMarkdownProcessor()
    from NossiPack.markdown.tags.foldable import FoldableTag

    FoldableTag._counter = 0
    result = processor.render("## !Foldable\ncontent\n\n## !Foldable\nmore", "testpage")
    ids = re.findall(r'data-for="([^"]+)"', result)
    assert len(ids) == 2
    assert ids[0] != ids[1]


def test_glitch_separate_spans():
    """g~hello~g — g~world~g~W0RLD~g must produce two separate spans."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g — g~world~g~W0RLD~g", "testpage")
    spans = re.findall(r'<span class="glitch"', result)
    assert len(spans) == 2
    assert 'data-text="hello"' in result
    assert 'data-text="W0RLD"' in result
    assert "hello" in result
    assert "world" in result


def test_checkbox_in_code_block():
    """Checkbox syntax inside inline code must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`- [ ] unfinished`", "testpage")
    assert 'type="checkbox"' not in result
    assert "- [ ] unfinished" in result


def test_checkbox_in_code_block_x():
    """Checkbox done syntax inside inline code must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`- [x] done`", "testpage")
    assert 'type="checkbox"' not in result
    assert "- [x] done" in result


def test_checkbox_outside_code_block():
    """Checkbox syntax outside code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("- [x] done", "testpage")
    assert 'type="checkbox"' in result
    assert "checked" in result


def test_glitch_inside_code():
    """Glitch syntax inside code blocks must not be processed."""
    processor = NossiMarkdownProcessor()
    result = processor.render("`g~hello~g`", "testpage")
    assert 'class="glitch"' not in result
    assert "&gt;" not in result  # no HTML-escaped brackets from failed matching


def test_glitch_outside_code():
    """Glitch syntax outside code blocks still works."""
    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="hello"' in result


def test_tooltip_html_structure():
    """Tooltip must render trigger text and content span."""
    processor = NossiMarkdownProcessor()
    body = "## Section\ninner content"
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_load.return_value = MagicMock(body=body, title="Page")
        result = processor.render("[!t:Page#section]", "test")
        assert '<span class="tooltip">' in result
        assert '<span class="tooltiptext">' in result
        assert "inner content" in result
