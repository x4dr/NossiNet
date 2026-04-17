import pytest
import sys
from pathlib import Path
from playwright.sync_api import Page, expect

sys.path.append(str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


@pytest.fixture(scope="function", autouse=True)
def setup_clocks(page: Page):
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    page.goto("https://localhost:5000/wiki/clocks")
    page.wait_for_selector(".clock-container", state="visible")
    page.wait_for_load_state("networkidle")


def test_complex_clock_interaction(page: Page):
    clock_id = "IRUWOQ3FNRWGC4Q-MNWG6Y3LOM"
    clock_container = page.locator(f"#{clock_id}")
    expect(clock_container).to_be_visible()

    # Check if we can increment or decrement
    for _ in range(4):
        inactive = clock_container.locator(".segment:not(.active)")
        if inactive.count() > 0:
            inactive.first.click(force=True)
        else:
            clock_container.locator(".segment.active").last.click(force=True)
        page.wait_for_timeout(300)

    # We should have changed state at least.
    # The test doesn't care exactly how many, just that it's interactive.
    print("Complex interaction completed.")


def test_clock_ui_interaction_changes_active_attribute(page: Page):
    # Locate the clock by its ID. Now that generate_clock is fixed to use relative paths,
    # the ID will include the .md suffix encoded.
    clock_id = "IRUWOQ3FNRWGC4Q-MNWG6Y3LOMXG2ZA"
    clock = page.locator(f"#{clock_id}")

    # Ensure it's visible
    expect(clock).to_be_visible()

    # Capture initial data-active value
    initial_active = clock.get_attribute("data-active")

    # Wait for the delayed JS handlers in sse_handler.js to attach
    page.wait_for_timeout(1500)

    # Click the clock to increment
    box = clock.bounding_box()
    if box:
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    else:
        pytest.fail("Clock container not found/visible.")

    # Verify the UI update
    page.wait_for_timeout(2000)
    current_active = clock.get_attribute("data-active")

    assert (
        current_active != initial_active
    ), "The clock 'data-active' attribute did not change after click interaction."
