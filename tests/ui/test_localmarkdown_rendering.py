"""Tests for the local markdown demo page rendering."""

import pytest
from typing import Any

from playwright.sync_api import Page, expect


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, bool]:
    """Configure Playwright to ignore HTTPS errors for local testing."""
    return {**browser_context_args, "ignore_https_errors": True}


def test_localmarkdown_rendering(page: Page) -> None:
    """Local markdown page displays correct title and expected headings."""
    # Navigate to localmarkdown demo page
    page.goto("https://127.0.0.1:5000/localmarkdown")

    # Capture and print content to diagnose the empty rendering issue
    content = page.content()
    print(f"DEBUG: Page HTML content length: {len(content)}")
    print(f"DEBUG: Page preview: {content[:500]}")

    # Check if the title is correct
    expect(page).to_have_title("Local Markdown Demo")

    # Look for expected headings
    expect(page.get_by_role("heading", name="Local Markdown Features")).to_be_visible()
