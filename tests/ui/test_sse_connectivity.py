"""Tests for SSE (Server-Sent Events) connectivity."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


def test_sse_connection(page: Page, app_server: str) -> None:
    """SSE test UI page loads and updates the timer via server-sent events."""
    print("TEST START")
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

    page.goto(f"{app_server}/sse_test_ui")

    for _i in range(5):
        page.wait_for_timeout(1100)
        print(f"Time: {page.locator('#timer').inner_text()}")

    print("TEST END")
