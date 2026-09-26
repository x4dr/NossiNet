"""Tests for clock widget UI interaction."""

import pytest
from playwright.sync_api import Page, expect


def test_complex_clock_interaction(page: Page, app_server: str) -> None:
    """Clicking a clock widget repeatedly leaves it interactive and error-free."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.goto(f"{app_server}/wiki/clocks")
    clock = page.locator(".clock-container").first
    expect(clock).to_be_visible(timeout=10000)

    box = clock.bounding_box()
    if not box:
        pytest.fail("Clock container has no bounding box.")

    for _ in range(4):
        page.mouse.click(box["x"] + box["width"] * 0.75, box["y"] + box["height"] * 0.5)
        page.wait_for_timeout(300)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_clock_ui_interaction_changes_active_attribute(page: Page, app_server: str) -> None:
    """Clicking a clock changes its data-active attribute."""
    page.goto(f"{app_server}/wiki/clocks")
    clock = page.locator(".clock-container").first
    expect(clock).to_be_visible(timeout=10000)

    initial_active = clock.get_attribute("data-active")
    assert initial_active is not None, "Clock container has no data-active attribute"

    # Wait for the delayed JS handlers in sse_handler.js to attach
    page.wait_for_timeout(1500)

    box = clock.bounding_box()
    if not box:
        pytest.fail("Clock container has no bounding box.")
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    expect(clock).not_to_have_attribute("data-active", initial_active, timeout=10000)
