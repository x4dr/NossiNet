import pytest
import subprocess
import time
import os
import sqlite3
import shutil
from pathlib import Path
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def test_db():
    # 1. Create a isolated test database
    test_db_path = Path("test_NN.db").absolute()
    if Path("NN.db").exists():
        shutil.copy("NN.db", test_db_path)

    # 2. Point the Discord webhook to our mock server port (5002)
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "UPDATE configs SET value = 'http://127.0.0.1:5002/mock-webhook' "
        "WHERE user = 'bridge' AND option = 'webhook'"
    )
    conn.commit()
    conn.close()

    yield str(test_db_path)

    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture(scope="session")
def test_server(test_db):
    # Start the server as a true subprocess
    env = os.environ.copy()
    env["DATABASE"] = test_db
    env["PYTHONPATH"] = "."

    port = 5001
    proc = subprocess.Popen(
        ["python", "NossiNet.py", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to be responsive
    time.sleep(8)
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        pytest.fail(f"Server failed to start!\nSTDOUT: {stdout}\nSTDERR: {stderr}")

    yield f"https://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "ignore_https_errors": True}


def test_chat_timestamp_instant_update(page: Page, test_server, httpserver):
    # 1. Setup Mock Discord Webhook on port 5002
    httpserver.expect_request("/mock-webhook").respond_with_data("OK", status=204)
    base_url = test_server

    # 2. Login
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "TESTUSER")
    page.fill("input[name='password']", "password123")
    page.click("input[type='submit']")

    # 3. Go to chat
    page.goto(f"{base_url}/chat/")
    page.wait_for_selector("#chatbox")

    # 4. Send a message
    unique_id = f"{int(time.time() * 1000)}"
    test_msg = f"TEST-ROBUST-{unique_id}"
    msg_input = page.locator("#message_data")
    msg_input.fill(test_msg)
    msg_input.press("Enter")

    # 5. Wait for the message to appear via SSE
    # Use to_contain_text on chatbox for better resilience
    expect(page.locator("#chatbox")).to_contain_text(test_msg, timeout=15000)

    # 6. Verify Webhook (Safety Confirmation)
    # The httpserver log should record the request
    page.wait_for_timeout(1000)
    assert len(httpserver.log) > 0, "Discord webhook was NOT intercepted by local mock!"

    # 7. Check the timestamp inside the newly appeared element
    timestamp = page.locator(f"div:has-text('{test_msg}')").locator(".timestamp").last
    ts_text = timestamp.inner_text()
    print(f"Verified timestamp: '{ts_text}'")

    # Assert that the conversion to relative time happened immediately (MutationObserver)
    assert "T" not in ts_text, f"ISO string detected: {ts_text}"
    assert "ago" in ts_text or "now" in ts_text, f"Relative expected: {ts_text}"
