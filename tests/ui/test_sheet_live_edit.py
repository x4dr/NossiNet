"""Tests for the sheet live-edit overlay (open and close via the Close button)."""

import shutil
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from playwright.sync_api import ConsoleMessage, Page, expect

# Must match the port map documented in tests/ui/conftest.py.
PORT_SHEET = 5002

SHEET = "character/testcharacter"


@pytest.fixture(scope="session")
def test_db() -> Iterator[str]:
    """Copy the real database and point TESTUSER at the test character sheet."""
    test_db_path = Path("test_sheet_edit_NN.db").absolute()
    shutil.copy("NN.db", test_db_path)

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "UPDATE configs SET value = ? WHERE user = 'TESTUSER' AND option = 'character_sheet'",
        (SHEET,),
    )
    conn.commit()
    conn.close()

    yield str(test_db_path)

    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture(scope="session")
def test_server(test_db: str, nossi_server: Callable[..., str]) -> str:
    """Start a NossiNet server subprocess for the test session."""
    return nossi_server(PORT_SHEET, database=Path(test_db))


def test_sheet_edit_overlay_closes(page: Page, test_server: str) -> None:
    """Double-clicking an editable section opens the overlay and Close dismisses it."""
    errors: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)

    page.goto(f"{test_server}/login")
    page.fill("input[name='username']", "TESTUSER")
    page.fill("input[name='password']", "password123")
    page.click("input[type='submit']")

    page.goto(f"{test_server}/sheet/{SHEET}")
    editable = page.locator(".editable[data-path]").first
    expect(editable).to_be_visible(timeout=10000)
    editable.dblclick()

    expect(page.locator("#editfield.activeedit")).to_be_visible(timeout=10000)
    page.locator("#editfield [name='closebutton']").click()
    expect(page.locator("#editfield")).not_to_have_class("editfield activeedit", timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"


def test_sheet_table_edit_overlay_closes(page: Page, test_server: str) -> None:
    """Double-clicking an editable table opens the table editor and Close dismisses it."""
    errors: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))

    page.goto(f"{test_server}/login")
    page.fill("input[name='username']", "TESTUSER")
    page.fill("input[name='password']", "password123")
    page.click("input[type='submit']")

    page.goto(f"{test_server}/sheet/{SHEET}")
    table = page.locator(".editable[data-type='table'][data-path]").first
    expect(table).to_be_attached(timeout=10000)
    table.dispatch_event("dblclick")

    expect(page.locator("div#table_editor.activeedit")).to_be_visible(timeout=10000)
    page.locator("#editform_table [name='closebutton']").click()
    expect(page.locator("div#table_editor")).not_to_have_class("editfield_table activeedit", timeout=5000)

    non_sse_errors = [e for e in errors if "SSE" not in e]
    assert not non_sse_errors, f"Unexpected console errors: {non_sse_errors}"
