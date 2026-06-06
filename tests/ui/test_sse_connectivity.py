import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


def test_sse_connection(page: Page):
    print("TEST START")
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

    page.goto("https://127.0.0.1:5000/sse_test_ui")

    for i in range(5):
        page.wait_for_timeout(1100)
        print(f"Time: {page.locator('#timer').inner_text()}")

    print("TEST END")
