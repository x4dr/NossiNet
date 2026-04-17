from pathlib import Path
from gamepack.WikiPage import WikiPage


def setup_module(module):
    # Setup dummy wiki structure for testing
    wiki_root = Path("/tmp/test_wiki")
    wiki_root.mkdir(parents=True, exist_ok=True)
    test_page = wiki_root / "test.md"
    test_page.write_text("---\ntitle: Test\ntags: []\n---\n[clock|TestClock|5|10]")
    WikiPage.set_wikipath(wiki_root)


def teardown_module(module):
    # Clean up
    import shutil

    shutil.rmtree("/tmp/test_wiki")


def test_cache_persistence_across_loading_methods():
    WikiPage.page_cache.clear()

    # 1. Load using load_locate (stem)
    page1 = WikiPage.load_locate("test", cache=True)
    assert page1 is not None

    # 2. Modify clock in memory (no save)
    page1.change_clock("TestClock", 1)
    # Ensure body is actually changed
    assert "TestClock|6|10" in page1.body
    page1.cacheupdate()

    # 3. Load using load_locate (stem again)
    page2 = WikiPage.load_locate("test", cache=True)
    assert "TestClock|6|10" in page2.body
    assert page2.get_clock("TestClock").group("current") == "6"

    # 4. Load using load_locate (full path with .md)
    page3 = WikiPage.load_locate("test.md", cache=True)
    assert page3.get_clock("TestClock").group("current") == "6"

    # 5. Load using load(Path)
    path = WikiPage.locate("test")
    page4 = WikiPage.load(path, cache=True)
    assert page4.get_clock("TestClock").group("current") == "6"

    # Verify object identity (all should be same instance)
    assert page1 is page2 is page3 is page4


def test_cache_with_and_without_md():
    WikiPage.page_cache.clear()

    # Load without .md
    page_no_md = WikiPage.load_locate("test", cache=True)
    page_no_md.change_clock("TestClock", -1)
    page_no_md.cacheupdate()

    # Load with .md
    page_with_md = WikiPage.load_locate("test.md", cache=True)
    assert page_with_md.get_clock("TestClock").group("current") == "4"
    assert page_with_md is page_no_md
