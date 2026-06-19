"""Tests for local markdown rendering without console errors."""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import ConsoleMessage, Page


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, bool]:
    """Configure Playwright to ignore HTTPS errors for local testing."""
    return {**browser_context_args, "ignore_https_errors": True}


def test_localmarkdown_renders_without_errors(page: Page) -> None:
    """Local markdown page loads without browser console errors or 404s."""
    errors = []

    def log_error(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)
        print(f"BROWSER LOG: {msg.text}")

    page.on("console", log_error)
    page.on(
        "response",
        lambda response: (errors.append(f"404 on {response.url}") if response.status == 404 else None),
    )

    page.goto("https://127.0.0.1:5000/localmarkdown")

    page.wait_for_timeout(2000)

    assert len(errors) == 0, f"Found errors during rendering: {errors}"
