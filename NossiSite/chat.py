"""Chat module providing real-time messaging, LiveKit voice, and Discord integration."""

import os
import re
import threading
import time
from datetime import UTC, datetime
from typing import Any

import requests
from flask import Blueprint, render_template, request, session
from jinja2 import Environment, PackageLoader, select_autoescape
from livekit import api

from Data import connect_db
from NossiPack.Chatrooms import Chatroom
from NossiPack.User import Userlist
from NossiSite.base import log
from NossiSite.helpers import checklogin
from NossiSite.socks import broadcast_to_hub

views = Blueprint("chat", __name__)

env = Environment(loader=PackageLoader("NossiSite"), autoescape=select_autoescape())
history_template = env.get_template("base/chathistory.html")

ROOM_NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
LIVEKIT_PING_INTERVAL = 60.0
LIVEKIT_PING_TIMEOUT = 2.0


# Reachability cache, guarded by _livekit_lock. A single mutable holder keeps
# the timestamp and the answer in one assignable slot for the monitor thread.
class _LiveKitState:
    """Cached LiveKit reachability, shared by the monitor thread and request path."""

    def __init__(self) -> None:
        """Start out unchecked and unavailable."""
        self.checked_at: float = 0.0
        self.reachable: bool = False


_livekit_state = _LiveKitState()
_livekit_lock = threading.Lock()

data: dict[str, Any] = {
    "webhook": "",
    "channelid": "",
    "botname": "Okysa",
    "thread": None,
}


def load_chat(after: int) -> tuple[dict[int, dict[str, str]], int]:
    """Load chat messages after a given line number.

    Args:
        after: Line number to load messages after.

    Returns:
        A tuple of (messages dict keyed by line number, latest line number).
    """
    with connect_db("loadchatlog") as db:
        rows = db.execute(
            "SELECT line, time, linenr FROM chatlogs WHERE linenr > ? " "ORDER BY linenr DESC LIMIT 100",
            [after],
        ).fetchall()
        return {
            row[2]: {
                "line": row[0],
                "time": datetime.fromtimestamp(row[1], UTC).isoformat(),
            }
            for row in reversed(rows)
        }, (rows[0][2] if rows else after)


def init() -> None:
    """Load bridge configuration (webhook, channel, bot name) from the database."""
    db = connect_db("init chat")
    webhook = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'webhook'",
    ).fetchone()
    channelid = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'channelid'",
    ).fetchone()
    botname = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'botname'",
    ).fetchone()
    data["webhook"] = webhook[0] if webhook else ""
    data["channelid"] = channelid[0] if channelid else ""
    data["botname"] = botname[0] if botname else "Okysa"


def sync_chat(
    username: str,
    message_content: str,
    mention: str | None = None,
    *,
    broadcast: bool = True,
) -> None:
    """Synchronize a message to the local chat and Discord."""
    ul = Userlist()
    u = ul.loaduserbyname(username)

    display_name = username
    if not mention and u:
        discord_config = u.config("discord", "")
        discord_id_match = re.match(r"(\d+)", discord_config or "")
        discord_id = discord_id_match.group(1) if discord_id_match else ""
        mention = f"<@{discord_id}>" if discord_id else username
    elif not mention:
        mention = username

    try:
        formatted_line = f"{display_name}\n{message_content}"
        room_id = data.get("channelid")
        if not room_id:
            log.warning(
                "Chat sync: No 'channelid' configured for 'bridge' user. Local chat logging skipped.",
            )

        cr = Chatroom(room_id) if room_id else None
        if cr:
            cr.addlinetolog(formatted_line, time.time())

        if broadcast:
            resolved_content = cr.resolve_mentions(message_content) if cr else message_content
            timestamp = datetime.now(UTC).isoformat()
            broadcast_to_hub(
                {
                    "type": "chat",
                    "line": resolved_content,
                    "user": display_name,
                    "time": timestamp,
                    "html": render_template(
                        "base/single_chat_msg.html",
                        user=display_name,
                        line=resolved_content,
                        time=timestamp,
                    ),
                },
            )
    except Exception as e:
        log.error(f"Local chat save failed: {e}")

    if data["webhook"]:
        message_data = {
            "content": message_content,
            "username": username,
        }
        try:
            requests.post(data["webhook"], json=message_data, timeout=5)
        except Exception as e:
            log.error(f"Discord sync failed: {e}")
    else:
        log.warning(
            "Chat sync: No 'webhook' configured for 'bridge' user. Discord sync skipped.",
        )


@views.route("/chat/history")
def chat_history() -> str:
    """Render the full chat history page."""
    checklogin()
    messages, _ = load_chat(0)
    return history_template.render(
        messages=messages,
        now=datetime.now(UTC).isoformat(),
    )


@views.route("/chat/send", methods=["POST"])
def chat_send() -> tuple[str, int]:
    """Accept a chat message POST and sync it to local storage and Discord."""
    checklogin()
    message_content = request.form.get("message_data")
    if not message_content:
        return "", 204

    sync_chat(str(session.get("user") or ""), message_content)

    return "", 204


def _livekit_configured() -> bool:
    """Report whether all three LiveKit environment variables are present."""
    return bool(
        os.environ.get("LIVEKIT_URL") and os.environ.get("LIVEKIT_API_KEY") and os.environ.get("LIVEKIT_API_SECRET"),
    )


def _ping_livekit() -> bool:
    """Probe whether the LiveKit server answers an HTTP request.

    Returns:
        True when the configured server responded, False when it is
        unconfigured, unreachable or slow. Never raises.
    """
    lk_url = os.environ.get("LIVEKIT_URL")
    if not lk_url:
        return False

    url = lk_url.replace("ws://", "http://").replace("wss://", "https://")
    if not url.startswith("http"):
        url = "http://" + url

    try:
        with requests.Session() as s:
            s.trust_env = False
            s.get(url, timeout=LIVEKIT_PING_TIMEOUT)
    except requests.RequestException:
        return False
    except Exception as e:  # pragma: no cover - defensive
        log.debug(f"LiveKit ping raised unexpectedly: {e}")
        return False
    return True


def _livekit_reachable() -> bool:
    """Report current LiveKit reachability, refreshing the cache if it is stale.

    The cache is refreshed at most every ``LIVEKIT_PING_INTERVAL`` seconds. When
    the last known state was "down" the wait is skipped once so that starting a
    session flips the UI to available on the next page load rather than after a
    full interval.

    Returns:
        True when LiveKit appears to be running.
    """
    with _livekit_lock:
        now = time.time()
        never_checked = _livekit_state.checked_at == 0.0
        stale = now - _livekit_state.checked_at > LIVEKIT_PING_INTERVAL
        # Re-probe promptly when the last answer was "down", so a session that
        # starts mid-interval shows up on the next page load.
        if never_checked or (stale and not _livekit_state.reachable):
            _livekit_state.checked_at = now
            _livekit_state.reachable = _ping_livekit()
        return _livekit_state.reachable


def _livekit_monitor() -> None:
    """Poll LiveKit on an interval for the lifetime of the process."""
    while True:
        try:
            reachable = _ping_livekit()
            with _livekit_lock:
                _livekit_state.checked_at = time.time()
                _livekit_state.reachable = reachable
        except Exception as e:  # pragma: no cover - defensive
            log.debug(f"LiveKit monitor iteration failed: {e}")
        time.sleep(LIVEKIT_PING_INTERVAL)


threading.Thread(target=_livekit_monitor, daemon=True, name="livekit-monitor").start()


@views.route("/chat/livekit-token/<room_name>")
def livekit_token(room_name: str) -> tuple[dict[str, str], int]:
    """Generate a LiveKit access token for a given room.

    Requires a logged-in user: anyone unauthenticated could otherwise mint a
    room-join credential for an arbitrary room name. Room access itself stays
    open to any logged-in user, by design.

    Args:
        room_name: The LiveKit room to join.

    Returns:
        A JSON dict with the JWT token and server URL and status 200, or a JSON
        error message with status 400, 401 or 503.
    """
    checklogin()

    if not ROOM_NAME_RE.fullmatch(room_name):
        log.warning(f"Rejected LiveKit room name: {room_name[:40]!r}")
        return _token_error("Invalid room name", 400)

    user = session.get("user")
    if not user:
        # checklogin() passed, so this should not be reachable; refuse rather
        # than mint a token under a placeholder identity.
        return _token_error("Not logged in", 401)

    key = os.environ.get("LIVEKIT_API_KEY")
    secret = os.environ.get("LIVEKIT_API_SECRET")
    url = os.environ.get("LIVEKIT_URL")
    if not key or not secret or not url:
        log.warning("LiveKit variables missing in environment")
        return _token_error("LiveKit is not configured", 503)

    token = (
        api.AccessToken(key, secret)
        .with_identity(str(user))
        .with_name(str(user))
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    return {"token": token.to_jwt(), "url": url}, 200


def _token_error(message: str, status: int) -> tuple[dict[str, str], int]:
    """Build a JSON error response for a refused token request."""
    return {"error": message}, status


@views.route("/chat/")
def chatsite() -> str:
    """Render the main chat page, conditionally enabling LiveKit features.

    LiveKit is offered only when it is both configured and actually answering.
    Credentials alone are not enough: the server usually runs only for the
    duration of a scheduled session, so the Join control is hidden while it is
    down rather than inviting a click that cannot succeed.
    """
    checklogin()

    livekit_available = _livekit_configured() and _livekit_reachable()

    if _livekit_configured() and not livekit_available:
        log.info("LiveKit configured but not answering; hiding call controls")

    return render_template("base/chat.html", livekit_available=livekit_available)


init()
