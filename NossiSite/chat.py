"""Chat module providing real-time messaging, LiveKit voice, and Discord integration."""

import os
import re
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


@views.route("/chat/livekit-token/<room_name>")
def livekit_token(room_name: str) -> dict[str, str | None]:
    """Generate a LiveKit access token for a given room.

    Args:
        room_name: The LiveKit room to join.

    Returns:
        A dict with the JWT token and server URL.
    """
    user = session.get("user", "Anonymous")
    token = (
        api.AccessToken(
            os.environ.get("LIVEKIT_API_KEY"),
            os.environ.get("LIVEKIT_API_SECRET"),
        )
        .with_identity(user)
        .with_name(user)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    return {"token": token.to_jwt(), "url": os.environ.get("LIVEKIT_URL")}


@views.route("/chat/debug")
def chat_debug() -> str | dict[str, Any]:
    """Debug endpoint that probes the LiveKit server health."""
    checklogin()
    lk_url = os.environ.get("LIVEKIT_URL")
    if not lk_url:
        return "LIVEKIT_URL not set"

    url = lk_url.replace("ws://", "http://").replace("wss://", "https://")
    if not url.startswith("http"):
        url = "http://" + url

    try:
        with requests.Session() as s:
            s.trust_env = False
            res = s.get(url, timeout=5, verify=False)
            return {
                "url": url,
                "status": res.status_code,
                "headers": dict(res.headers),
                "text": res.text[:100],
            }
    except Exception as e:
        return f"Check failed for {url}: {e}"


@views.route("/chat/")
def chatsite() -> str:
    """Render the main chat page, conditionally enabling LiveKit features."""
    checklogin()
    livekit_available = bool(
        os.environ.get("LIVEKIT_URL") and os.environ.get("LIVEKIT_API_KEY") and os.environ.get("LIVEKIT_API_SECRET"),
    )
    if not livekit_available:
        log.warning("LiveKit variables missing in environment")

    return render_template("base/chat.html", livekit_available=livekit_available)


init()
