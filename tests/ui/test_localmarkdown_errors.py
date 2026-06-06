import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


def test_localmarkdown_renders_without_errors(page: Page):
    errors = []

    def log_error(msg):
        if msg.type == "error":
            errors.append(msg.text)
        print(f"BROWSER LOG: {msg.text}")

    page.on("console", log_error)
    page.on(
        "response",
        lambda response: (
            errors.append(f"404 on {response.url}") if response.status == 404 else None
        ),
    )

    page.goto("https://127.0.0.1:5000/localmarkdown")

    page.wait_for_timeout(2000)

    assert len(errors) == 0, f"Found errors during rendering: {errors}"
