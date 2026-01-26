import asyncio
from playwright.async_api import async_playwright


async def run_test():
    async with async_playwright() as p:
        try:
            # Ignore HTTPS errors for local dev
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            # Capture console logs
            page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
            page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

            print("Opening page...")
            # We use a long timeout because the server might be slow to start
            await page.goto("https://127.0.0.1:5000/sheet/mechtest", timeout=60000)

            print(f"Page Title: {await page.title()}")

            # Wait for HTMX to load systems
            print("Waiting for systems to load...")
            await asyncio.sleep(5)

            # Check for visible systems
            systems = await page.query_selector_all(".system-card")
            print(f"Found {len(systems)} system cards.")

            await browser.close()
            return True
        except Exception as e:
            print(f"Test failed: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(run_test())
