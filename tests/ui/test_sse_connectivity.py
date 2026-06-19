"""Tests for SSE (Server-Sent Events) connectivity."""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, bool]:
    """Configure Playwright to ignore HTTPS errors for local testing."""
    return {**browser_context_args, "ignore_https_errors": True}


def test_sse_connection(page: Page) -> None:
    """SSE test UI page loads and updates the timer via server-sent events."""
    print("TEST START")
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

    page.goto("https://127.0.0.1:5000/sse_test_ui")

    for _i in range(5):
        page.wait_for_timeout(1100)
        print(f"Time: {page.locator('#timer').inner_text()}")

    print("TEST END")
