"""Tests for local markdown rendering without console errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import ConsoleMessage, Page


def test_localmarkdown_renders_without_errors(page: Page, app_server: str) -> None:
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

    page.goto(f"{app_server}/localmarkdown")

    page.wait_for_timeout(2000)

    assert len(errors) == 0, f"Found errors during rendering: {errors}"
