from playwright.sync_api import sync_playwright


def test_localmarkdown_renders_without_errors():
    errors = []

    def log_error(msg):
        if msg.type == "error":
            errors.append(msg.text)
        print(f"BROWSER LOG: {msg.text}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Track 404s and errors
        page.on("console", log_error)
        page.on(
            "response",
            lambda response: (
                errors.append(f"404 on {response.url}")
                if response.status == 404
                else None
            ),
        )

        page.goto("https://127.0.0.1:5000/localmarkdown")

        # Wait for potential HTMX requests to trigger
        page.wait_for_timeout(2000)

        assert len(errors) == 0, f"Found errors during rendering: {errors}"
        browser.close()


if __name__ == "__main__":
    test_localmarkdown_renders_without_errors()
