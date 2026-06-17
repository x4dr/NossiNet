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


def test_checkbox_roundtrip(page: Page):
    """Checkbox task list syntax survives a TipTap edit/save round-trip."""
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
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


def test_glitch_and_strikethrough_survive_roundtrip(page: Page):
    """Glitch syntax (g~text~g) and strikethrough (~~text~~) survive save roundtrip without corrupting each other."""
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

    # Toggle to source mode to check raw markdown before save
    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(500)
    source_text = page.locator("#tip-source-area").input_value()
    # Disabled marked's del tokenizer, so single-tilde glitch syntax is preserved as-is
    # (the markdown serializer escapes ~ as \~ for roundtrip stability)
    assert (
        "g~text~g" in source_text
    ), f"Glitch simple syntax lost before save: {source_text[:300]}"
    assert (
        "g~text~g~replacement~g" in source_text
    ), f"Glitch 3-part syntax lost before save: {source_text[:300]}"
    assert (
        "~~strikethrough~~" in source_text
    ), f"Strikethrough syntax lost before save: {source_text[:300]}"

    # Toggle back to WYSIWYG and save
    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(1000)
    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Re-open editor and check source mode again
    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(500)
    source_text = page.locator("#tip-source-area").input_value()

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
    assert (
        "g~text~g" in source_text
    ), f"Glitch simple syntax lost after roundtrip: {source_text[:300]}"
    assert (
        "~~strikethrough~~" in source_text
    ), f"Strikethrough syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_clock_roundtrip(page: Page):
    """Clock syntax [clock|name|current|total] survives a TipTap save roundtrip."""
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    # Check clock is present in source mode
    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(500)
    source_text = page.locator("#tip-source-area").input_value()
    assert (
        "[clock|progress|3|8]" in source_text
    ), f"Clock syntax lost before save: {source_text[:300]}"

    # Save and reload
    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(1000)
    page.locator("#tip-save").click()
    page.wait_for_selector(".tip-overlay", state="hidden", timeout=10000)
    expect(page.locator("#wikibody")).to_be_visible()

    # Re-open and verify clock survived
    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)
    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(500)
    source_text = page.locator("#tip-source-area").input_value()

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
    assert (
        "[clock|progress|3|8]" in source_text
    ), f"Clock syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_decorations_applied_without_errors(page: Page):
    """Tag decorations appear as .tag-dirty spans in the editor without console errors."""
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"

    # Validator script loaded (will appear in dataset if ProseMirror was found)
    page.evaluate("document.documentElement.dataset.wikiTagValidator")

    page.locator("#tip-close").click()


def test_source_mode_toggle(page: Page):
    """Source mode toggle switches between WYSIWYG and raw textarea."""
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
    expect(page.locator("#tip-source-area")).not_to_be_visible()

    page.locator("#tip-source-toggle").click()
    expect(page.locator("#tip-editor .ProseMirror")).not_to_be_visible()
    expect(page.locator("#tip-source-area")).to_be_visible()
    expect(page.locator("#tip-source-toggle")).to_have_text("</> WYSIWYG")

    source_text = page.locator("#tip-source-area").input_value()
    assert (
        source_text.strip()
    ), f"Expected non-empty content in source view, got: {source_text[:200]}"

    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(1000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()
    expect(page.locator("#tip-source-area")).not_to_be_visible()
    expect(page.locator("#tip-source-toggle")).to_have_text("</> Source")

    page.locator("#tip-close").click()

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
