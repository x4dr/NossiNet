"""Tests for the local markdown demo page rendering."""

from playwright.sync_api import Page, expect


def test_localmarkdown_rendering(page: Page, app_server: str) -> None:
    """Local markdown page displays correct title and expected headings."""
    # Navigate to localmarkdown demo page
    page.goto(f"{app_server}/localmarkdown")

    # Capture and print content to diagnose the empty rendering issue
    content = page.content()
    print(f"DEBUG: Page HTML content length: {len(content)}")
    print(f"DEBUG: Page preview: {content[:500]}")

    # Check if the title is correct
    expect(page).to_have_title("Local Markdown Demo")

    # Look for expected headings
    expect(page.get_by_role("heading", name="Local Markdown Features")).to_be_visible()
