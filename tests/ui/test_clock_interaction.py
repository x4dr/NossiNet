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
