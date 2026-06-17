import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


def test_tip_wiki_editor_opens_and_closes(page: Page):
    """Double-click opens the TipTap overlay, Cancel closes it."""
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    page.locator("#tip-close").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_tip_wiki_editor_save_roundtrip(page: Page):
    """Save button persists content and reloads the page."""
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Open editor again to verify content survived the round-trip
    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    editor_text = page.locator("#tip-editor .ProseMirror").inner_text()
    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
    assert (
        "Markdown Demo" in editor_text
    ), f"Expected original content after round-trip, got: {editor_text[:200]}"
