"""Tests that the chat page does not wedge when LiveKit is unreachable.

Pre-fix behaviour: ``chat.js`` revealed the call wrapper and hid the Join
button *before* awaiting ``room.connect()``, and the catch block restored only
``disabled`` and ``innerText``. With no LiveKit server listening, ``connect()``
rejected, so the button label changed while invisible and the mic/cam/leave
handlers -- assigned after the throw -- were never bound. The user was left with
an empty room panel showing "Participants 0" and no way back but a page reload.

The server-side ping hides the Join control entirely while LiveKit is down, so in
a default test environment these tests would find nothing to click and pass
vacuously. Each test therefore forces the control into the DOM first, which
reproduces the real failure window: LiveKit was up when the page loaded, then
stopped answering before the user clicked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Rebuild the hidden call controls exactly as chat.html renders them when the
# ping reported the server up.
FORCE_JOIN_UI = """
() => {
    let start = document.getElementById("livekit-start");
    if (!start) {
        start = document.createElement("div");
        start.id = "livekit-start";
        start.style.display = "flex";
        const wrapper = document.getElementById("wrapper");
        wrapper.insertBefore(start, wrapper.firstChild);
    }
    start.style.display = "flex";

    if (!document.getElementById("room-code-input")) {
        const input = document.createElement("input");
        input.type = "text";
        input.id = "room-code-input";
        start.appendChild(input);
    }

    let btn = document.getElementById("join-video-btn");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "join-video-btn";
        start.appendChild(btn);
    }
    btn.style.display = "block";
    btn.disabled = false;
    btn.textContent = "Join Video Call";
    btn.onclick = null;

    if (!document.getElementById("call-failure-notice")) {
        const notice = document.createElement("div");
        notice.id = "call-failure-notice";
        notice.style.display = "none";
        start.parentElement.insertBefore(notice, start.nextSibling);
    }

    // Re-attach the real handler, since chat.js bound it at DOMContentLoaded.
    const fresh = new Event("DOMContentLoaded");
    document.dispatchEvent(fresh);
    btn.style.display = "block";
}
"""


def _open_chat_with_forced_join(page: Page, base_url: str) -> None:
    """Log in, load chat, and guarantee the Join control exists and is clickable."""
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "TESTUSER")
    page.fill("input[name='password']", "password123")
    page.click("input[type='submit']")

    page.goto(f"{base_url}/chat/")
    page.wait_for_selector("#messageform")
    page.evaluate(FORCE_JOIN_UI)
    page.wait_for_selector("#join-video-btn")


def _attempt_join(page: Page) -> None:
    """Click Join and wait for the attempt to settle either way."""
    page.click("#join-video-btn")
    page.wait_for_timeout(5000)


def test_no_wedged_ui_when_livekit_unreachable(page: Page, app_server: str) -> None:
    """A failed connect leaves the chat page fully usable."""
    _open_chat_with_forced_join(page, app_server)

    join_btn = page.locator("#join-video-btn")
    _attempt_join(page)

    assert join_btn.is_visible(), "Join button stayed hidden after a failed connect"
    assert not join_btn.is_disabled(), "Join button stayed disabled after a failed connect"
    assert page.locator("#livekit-container").inner_html() == "", "stale video tiles left behind"
    assert page.locator("#participant-count").inner_text() == "0"
    assert page.locator("#participant-list").inner_html() == ""
    assert page.locator("#messageform").is_visible(), "chat input unusable after failed call"


def test_failure_is_explained_to_the_user(page: Page, app_server: str) -> None:
    """The failure surfaces a readable message, not just a console error."""
    _open_chat_with_forced_join(page, app_server)
    _attempt_join(page)

    notice = page.locator("#call-failure-notice")
    assert notice.is_visible(), "no user-visible failure message"
    text = notice.inner_text().strip()
    assert text, "failure message is empty"
    assert "undefined" not in text, f"unsubstituted message key: {text!r}"


def test_leave_button_works_after_failed_connect(page: Page, app_server: str) -> None:
    """The leave control is usable even when the connection attempt failed."""
    _open_chat_with_forced_join(page, app_server)
    _attempt_join(page)

    wrapper = page.locator("#livekit-wrapper")
    if wrapper.is_visible():
        page.click("#leave-video-btn")
        assert not wrapper.is_visible(), "leave did not tear the wrapper down"
        assert page.locator("#join-video-btn").is_visible()


def test_chat_usable_when_cdn_script_missing(page: Page, app_server: str) -> None:
    """An unreachable CDN yields a message, not a wedged page."""
    page.route("**/livekit-client*", lambda route: route.abort())
    _open_chat_with_forced_join(page, app_server)
    _attempt_join(page)

    assert page.locator("#join-video-btn").is_visible()
    assert page.locator("#messageform").is_visible()
