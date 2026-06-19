"""Tests for the TipTap wiki live editor (open, edit, save, round-trip)."""

from typing import Any

import pytest
from playwright.sync_api import ConsoleMessage, Page, expect


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, bool]:
    """Configure Playwright to ignore HTTPS errors for local testing."""
    return {**browser_context_args, "ignore_https_errors": True}


def test_tip_wiki_editor_opens_and_closes(page: Page) -> None:
    """Double-click opens the TipTap overlay, Cancel closes it."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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


def test_tip_wiki_editor_save_roundtrip(page: Page) -> None:
    """Save button persists content and reloads the page."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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
    assert "Markdown Demo" in editor_text, f"Expected original content after round-trip, got: {editor_text[:200]}"


def test_checkbox_roundtrip(page: Page) -> None:
    """Checkbox task list syntax survives a TipTap edit/save round-trip."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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


def test_glitch_and_strikethrough_survive_roundtrip(page: Page) -> None:
    """Glitch syntax (g~text~g) and strikethrough (~~text~~) survive save roundtrip without corrupting each other."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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
    assert "g~text~g" in source_text, f"Glitch simple syntax lost before save: {source_text[:300]}"
    assert "g~text~replacement~g" in source_text, f"Glitch 3-part syntax lost before save: {source_text[:300]}"
    assert "~~strikethrough~~" in source_text, f"Strikethrough syntax lost before save: {source_text[:300]}"

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
    assert "g~text~g" in source_text, f"Glitch simple syntax lost after roundtrip: {source_text[:300]}"
    assert "~~strikethrough~~" in source_text, f"Strikethrough syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_clock_roundtrip(page: Page) -> None:
    """Clock syntax [clock|name|current|total] survives a TipTap save roundtrip."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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
    assert "[clock|progress|3|8]" in source_text, f"Clock syntax lost before save: {source_text[:300]}"

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
    assert "[clock|progress|3|8]" in source_text, f"Clock syntax lost after roundtrip: {source_text[:300]}"

    page.locator("#tip-close").click()


def test_decorations_applied_without_errors(page: Page) -> None:
    """Tag decorations appear as .tag-dirty spans in the editor without console errors."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto("https://127.0.0.1:5000/wiki/demo")
    expect(page.locator("#wikibody")).to_be_visible()

    page.locator("#wikibody").dblclick()
    page.wait_for_selector(".tip-overlay", state="visible", timeout=5000)

    # Wait for validator to start observing the editor
    page.wait_for_function(
        "document.documentElement.dataset.wikiTagValidator === 'ready'",
        timeout=10000,
    )

    # Decorations applied — at least one .tag-dirty exists
    dirty_count = page.locator(".ProseMirror .tag-dirty").count()
    assert dirty_count > 0, f"Expected .tag-dirty elements in editor, found {dirty_count}"

    # Wait for validator to resolve at least one tag (valid or invalid)
    page.wait_for_selector(
        ".ProseMirror .tag-valid, .ProseMirror .tag-invalid",
        timeout=10000,
    )

    # The transclude [!pagename] doesn't exist → should be .tag-invalid
    invalid_count = page.locator(".ProseMirror .tag-invalid").count()
    assert invalid_count > 0, f"Expected at least one .tag-invalid element, found {invalid_count}"

    # Console still clean
    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"

    page.locator("#tip-close").click()


def test_source_mode_toggle(page: Page) -> None:
    """Source mode toggle switches between WYSIWYG and raw textarea."""
    errors = []

    def on_console(msg: ConsoleMessage) -> None:
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
    assert source_text.strip(), f"Expected non-empty content in source view, got: {source_text[:200]}"

    page.locator("#tip-source-toggle").click()
    page.wait_for_timeout(1000)
    expect(page.locator("#tip-editor .ProseMirror")).to_be_visible()
    expect(page.locator("#tip-source-area")).not_to_be_visible()
    expect(page.locator("#tip-source-toggle")).to_have_text("</> Source")

    page.locator("#tip-close").click()

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_wiki_page_renders_tags_correctly(page: Page) -> None:
    """Verify server-side wiki page renders all tag types correctly."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text))

    page.goto("https://127.0.0.1:5000/wiki/demo")
    page.wait_for_selector("#wikibody", state="visible", timeout=10000)

    body = page.locator("#wikibody")

    # Glitch — both syntaxes produce <span class="glitch"> with data-text
    assert body.locator("span.glitch").count() == 2
    data_texts = body.locator("span.glitch").all()
    texts = sorted(text for t in data_texts if (text := t.get_attribute("data-text")) is not None)
    assert texts == ["replacement", "text"], f"Unexpected data-text values: {texts}"

    # Section tooltip: span.tip-trigger inside <p>, div.tip-content with rich HTML
    tip_struct = page.evaluate(
        """() => {
        const trigger = document.querySelector('span.tip-trigger');
        if (!trigger) return { error: 'no span.tip-trigger' };

        const tipId = trigger.getAttribute('data-tip');
        if (!tipId) return { error: 'no data-tip attr' };

        const content = document.getElementById('tip-' + tipId);
        if (!content) return { error: 'no div#tip-' + tipId };

        const parentP = trigger.closest('p');
        if (!parentP) return { error: 'trigger not inside <p>' };

        const prevH2 = parentP.previousElementSibling;
        if (!prevH2 || prevH2.tagName !== 'H2' || !prevH2.textContent.includes('Section Tooltip'))
            return { error: 'paragraph not under Section Tooltip heading',
                     prevTag: prevH2?.tagName, prevText: prevH2?.textContent };

        return {
            triggerText: trigger.textContent,
            contentHtml: content.innerHTML.substring(0, 300),
            parentPTag: parentP.tagName,
            headingAbove: prevH2.textContent,
            contentHidden: content.hasAttribute('hidden'),
            nestedTranscludes: content.querySelectorAll('.transcluded').length,
        };
    }""",
    )
    assert "error" not in tip_struct, f"DOM structure error: {tip_struct.get('error')}"
    assert "Transclusion" in tip_struct["triggerText"]
    assert tip_struct["contentHidden"], "Tooltip content div should be hidden"
    assert (
        tip_struct["nestedTranscludes"] > 0
    ), f"Expected nested transcludes in tooltip content, got {tip_struct['nestedTranscludes']}"
    assert (
        "Include content from another page" in tip_struct["contentHtml"]
    ), f"Tooltip content should contain transcluded text, got: {tip_struct['contentHtml']}"

    # Transclude: recursive transclusion produces nested .transcluded divs
    transcluded_count = body.locator(".transcluded").count()
    assert transcluded_count > 0, f"Expected .transcluded elements, found {transcluded_count}"

    # Infolet: item not in cache, falls back to plain name
    assert "itemname" in (body.text_content() or "")

    # Foldable
    assert body.locator(".hider").count() == 1

    # Clock
    assert body.locator(".clock-container").count() == 1

    # Checkbox
    assert body.locator('input[type="checkbox"]').count() == 2

    # Strikethrough via standard markdown
    assert "~~strikethrough~~" in (body.text_content() or "")

    # No console errors
    non_sse = [e for e in errors if "SSE" not in e and "favicon" not in e.lower()]
    assert not non_sse, f"Console errors: {non_sse}"
