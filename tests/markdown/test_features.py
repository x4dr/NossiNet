from unittest.mock import MagicMock, patch
from NossiPack.markdown import NossiMarkdownProcessor

# Feature Tests


def test_transclude():
    processor = NossiMarkdownProcessor()
    # Mocking WikiPage.load_locate
    with patch("gamepack.WikiPage.WikiPage.load_locate") as mock_load:
        mock_page = MagicMock()
        mock_page.body = "# Transcluded Content"
        mock_load.return_value = mock_page

        result = processor.render("![text](page)", "testpage")
        assert "Transcluded Content" in result


def test_glitch():

    processor = NossiMarkdownProcessor()
    result = processor.render("g~hello~g", "testpage")
    assert 'class="glitch"' in result
    assert 'data-text="hello"' in result


def test_checkbox():
    processor = NossiMarkdownProcessor()
    result = processor.render("- [x] done", "testpage")
    # Current behavior is to render an HTML input
    assert 'type="checkbox"' in result
    assert "checked" in result


def test_infolet():
    processor = NossiMarkdownProcessor()
    # Mocking Item.item_cache
    with patch(
        "gamepack.Item.Item.item_cache", {"test": MagicMock(description="desc")}
    ):
        result = processor.render("[!q:test]", "testpage")
        assert 'class="tooltip"' in result
        assert "desc" in result


def test_foldable_spans():
    processor = NossiMarkdownProcessor()
    # This requires specific HTML structure matching, which we need to mock or emulate
    content = "# Main\n## !hidden\ncontent"
    result = processor.render(content, "testpage")
    assert 'class="hider"' in result
    assert 'class="hiding"' in result


def test_link_validation():
    processor = NossiMarkdownProcessor()
    with patch("gamepack.WikiPage.WikiPage.locate") as mock_locate:
        # Case 1: Existing link
        mock_locate.return_value = True
        result = processor.render('<a href="exists">Link</a>', "testpage")
        assert 'href="/wiki/exists"' in result

        # Case 2: Broken link
        mock_locate.return_value = False
        result = processor.render('<a href="broken">Link</a>', "testpage")
        assert 'class="missing"' in result


def test_clock():
    processor = NossiMarkdownProcessor()
    result = processor.render("[clock|name@page]", "testpage")
    # result should contain the clock container with encoded IDs
    assert 'class="clock-container' in result
    assert 'data-total="1"' in result
