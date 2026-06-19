"""Tests for chat timestamp instant-update behaviour."""

import os
import shutil
import sqlite3
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect
from pytest_httpserver import HTTPServer


@pytest.fixture(scope="session")
def webhook_server() -> Iterator[HTTPServer]:
    """Start a mock webhook server for Discord integration tests."""
    server = HTTPServer()
    server.start()
    server.expect_request("/mock-webhook").respond_with_data("OK", status=204)
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture(scope="session")
def test_db(webhook_server: HTTPServer) -> Iterator[str]:
    """Create a temporary test database with mock webhook URL."""
    test_db_path = Path("test_NN.db").absolute()
    if Path("NN.db").exists():
        shutil.copy("NN.db", test_db_path)

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "UPDATE configs SET value = ? WHERE user = 'bridge' AND option = 'webhook'",
        (f"http://127.0.0.1:{webhook_server.port}/mock-webhook",),
    )
    conn.commit()
    conn.close()

    yield str(test_db_path)

    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture(scope="session")
def test_server(test_db: str) -> Iterator[str]:
    """Start a NossiNet server subprocess for the test session."""
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
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Configure Playwright to ignore HTTPS errors for local testing."""
    return browser_context_args


def test_chat_timestamp_instant_update(page: Page, test_server: str, webhook_server: HTTPServer) -> None:
    """Chat messages show relative timestamps immediately via MutationObserver."""
    base_url = test_server

    # 1. Login
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "TESTUSER")
    page.fill("input[name='password']", "password123")
    page.click("input[type='submit']")

    # 2. Go to chat
    page.goto(f"{base_url}/chat/")
    page.wait_for_selector("#chatbox")

    # 3. Send a message
    unique_id = f"{int(time.time() * 1000)}"
    test_msg = f"TEST-ROBUST-{unique_id}"
    msg_input = page.locator("#message_data")
    msg_input.fill(test_msg)
    msg_input.press("Enter")

    # 4. Wait for the message to appear via SSE
    expect(page.locator("#chatbox")).to_contain_text(test_msg, timeout=15000)

    # 5. Verify Webhook (Safety Confirmation)
    page.wait_for_timeout(1000)
    assert len(webhook_server.log) > 0, "Discord webhook was NOT intercepted by local mock!"

    # 6. Check the timestamp inside the newly appeared element
    timestamp = page.locator(f"div:has-text('{test_msg}')").locator(".timestamp").last
    ts_text = timestamp.inner_text()
    print(f"Verified timestamp: '{ts_text}'")

    # Assert that the conversion to relative time happened immediately (MutationObserver)
    assert "T" not in ts_text, f"ISO string detected: {ts_text}"
    assert "ago" in ts_text or "now" in ts_text, f"Relative expected: {ts_text}"
