import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


def test_localmarkdown_rendering(page: Page):
    # Navigate to localmarkdown demo page
    page.goto("https://127.0.0.1:5000/localmarkdown")

    # Capture and print content to diagnose the empty rendering issue
    content = page.content()
    print(f"DEBUG: Page HTML content length: {len(content)}")
    print(f"DEBUG: Page preview: {content[:500]}")

    # Check if the title is correct
    expect(page).to_have_title("Local Markdown Demo")

    # Check if some markdown features rendered
    # Look for expected headings
    expect(page.locator("h1")).to_have_text("Local Markdown Features")
