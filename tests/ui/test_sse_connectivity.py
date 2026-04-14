from playwright.sync_api import sync_playwright


def test_sse_connection():
    print("TEST START")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        page.goto("https://127.0.0.1:5000/sse_test_ui")

        # Monitor the timer element to see it changing
        for i in range(5):
            page.wait_for_timeout(1100)
            print(f"Time: {page.locator('#timer').inner_text()}")

        browser.close()
    print("TEST END")


if __name__ == "__main__":
    test_sse_connection()
