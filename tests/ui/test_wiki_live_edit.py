"""Tests for the TipTap wiki live editor (open, edit, save, round-trip)."""

import re

from playwright.sync_api import ConsoleMessage, Page, expect


def wait_for_validation(page: Page) -> None:
    """Block until the tag validator has reached a verdict on every tag.

    Tags render as ``.tag-dirty`` until ``/tag-validate`` returns, then become
    ``.tag-valid`` or ``.tag-invalid``. Each settled request re-dispatches a
    transaction to force re-decoration, so typing before this point moves the
    caret out from under the user.

    Args:
        page: Playwright page showing the open editor.
    """
    page.wait_for_function(
        """() => {
            const root = document.querySelector('#tip-editor .ProseMirror')
            if (!root) return false
            const resolved = root.querySelectorAll('.tag-valid, .tag-invalid').length
            return resolved > 0 && root.querySelectorAll('.tag-dirty').length === 0
        }""",
        timeout=15000,
    )


def read_source(page: Page) -> str:
    """Switch the editor into source mode and return the raw markdown.

    Waits for the textarea to be populated rather than sleeping for a fixed time.

    Args:
        page: Playwright page showing the open editor.

    Returns:
        The editor contents as markdown source.
    """
    page.locator("#tip-source-toggle").click()
    area = page.locator("#tip-source-area")
    expect(area).to_be_visible(timeout=10000)
    expect(area).not_to_have_value(re.compile(r"^$"), timeout=10000)
    return area.input_value()


def back_to_wysiwyg(page: Page) -> None:
    """Switch the editor back to the WYSIWYG view and wait for it to be ready.

    Args:
        page: Playwright page showing the open editor.
    """
    page.locator("#tip-source-toggle").click()
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible(timeout=10000)
    expect(page.locator("#tip-source-area")).not_to_be_visible(timeout=10000)


def test_tip_wiki_editor_opens_and_closes(page: Page, editor_page_url: str) -> None:
    """Double-click opens the TipTap overlay, Cancel closes it."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    page.locator("#tip-close").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_tip_wiki_editor_save_roundtrip(page: Page, editor_page_url: str) -> None:
    """Save button persists content and reloads the page."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
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
    assert "Editor Fixture" in editor_text, f"Expected original content after round-trip, got: {editor_text[:200]}"


def test_checkbox_roundtrip(page: Page, editor_page_url: str) -> None:
    """Checkbox task list syntax survives a TipTap edit/save round-trip."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    # Verify checkboxes render in the static wiki view
    checkboxes = page.locator("#wikibody input[type=checkbox]")
    expect(checkboxes.first).to_be_visible(timeout=5000)

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Checkboxes should still render after the round-trip
    checkboxes = page.locator("#wikibody input[type=checkbox]")
    expect(checkboxes.first).to_be_visible(timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_glitch_and_strikethrough_survive_roundtrip(page: Page, editor_page_url: str) -> None:
    """Glitch syntax (g~text~g) and strikethrough (~~text~~) survive save roundtrip without corrupting each other."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    # Toggle to source mode to check raw markdown before save
    source_text = read_source(page)
    # Disabled marked's del tokenizer, so single-tilde glitch syntax is preserved as-is
    # (the markdown serializer escapes ~ as \~ for roundtrip stability)
    assert "g~text~g" in source_text, f"Glitch simple syntax lost before save: {source_text[:300]}"
    assert "g~text~replacement~g" in source_text, f"Glitch 3-part syntax lost before save: {source_text[:300]}"
    assert "~~strikethrough~~" in source_text, f"Strikethrough syntax lost before save: {source_text[:300]}"

    # Toggle back to WYSIWYG and save
    back_to_wysiwyg(page)
    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Re-open editor and check source mode again
    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    source_text = read_source(page)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
    assert "g~text~g" in source_text, f"Glitch simple syntax lost after roundtrip: {source_text[:300]}"
    assert "~~strikethrough~~" in source_text, f"Strikethrough syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_clock_roundtrip(page: Page, editor_page_url: str) -> None:
    """Clock syntax [clock|name|current|total] survives a TipTap save roundtrip."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    # Check clock is present in source mode
    source_text = read_source(page)
    assert "[clock|progress|3|8]" in source_text, f"Clock syntax lost before save: {source_text[:300]}"

    # Save and reload
    back_to_wysiwyg(page)
    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Re-open and verify clock survived
    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    source_text = read_source(page)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
    assert "[clock|progress|3|8]" in source_text, f"Clock syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_decorations_applied_without_errors(page: Page, editor_page_url: str) -> None:
    """Every tag in the editor reaches a validated or invalid verdict, without console errors."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    wait_for_validation(page)

    # The transclude of a nonexistent page must be rejected.
    expect(page.locator(".ProseMirror .tag-invalid").first).to_be_visible(timeout=10000)

    # The glitch, strikethrough, clock and checkbox tags all resolve.
    valid_count = page.locator(".ProseMirror .tag-valid").count()
    assert valid_count > 0, f"Expected .tag-valid elements in editor, found {valid_count}"

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"

    page.locator("#tip-close").click()


def test_source_mode_toggle(page: Page, editor_page_url: str) -> None:
    """Source mode toggle switches between WYSIWYG and raw textarea."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()
    expect(page.locator("#tip-source-area")).not_to_be_visible()

    page.locator("#tip-source-toggle").click()
    expect(page.locator("#tip-editor .ProseMirror")).not_to_be_visible()
    expect(page.locator("#tip-source-area")).to_be_visible()
    expect(page.locator("#tip-source-toggle")).to_have_text("</> WYSIWYG")

    area = page.locator("#tip-source-area")
    expect(area).not_to_have_value(re.compile(r"^$"), timeout=10000)
    source_text = area.input_value()
    assert source_text.strip(), f"Expected non-empty content in source view, got: {source_text[:200]}"

    back_to_wysiwyg(page)
    expect(page.locator("#tip-source-toggle")).to_have_text("</> Source")

    page.locator("#tip-close").click()

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_live_link_conversion(page: Page, editor_page_url: str) -> None:
    """Typing [text](url) in the editor creates a link mark immediately."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(editor_page_url)
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()

    # Every settled /tag-validate re-dispatches a transaction to force
    # re-decoration, which moves the caret. Wait for validation to actually
    # finish rather than guessing with a timeout.
    wait_for_validation(page)

    # Click a real paragraph, not the centre of .ProseMirror: the container's
    # geometric centre lands in the gap between blocks, which focuses the editor
    # without placing a caret, and the typed text then goes nowhere.
    page.locator("#tip-editor .ProseMirror p").last.click()
    page.keyboard.type("[Aurier](aurier)")

    link = page.locator("#tip-editor .ProseMirror a").first
    expect(link).to_be_visible(timeout=5000)

    href = link.get_attribute("href")
    assert href == "aurier", f"Expected href='aurier', got '{href}'"

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"

    page.locator("#tip-close").click()
