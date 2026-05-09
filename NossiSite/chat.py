import os
import re
import time
from datetime import datetime, timezone

import requests
from flask import render_template, session, request
from jinja2 import Environment, PackageLoader, select_autoescape
from livekit import api

from NossiPack.Chatrooms import Chatroom
from NossiPack.User import Userlist
from Data import connect_db
from NossiSite.helpers import checklogin
from NossiSite.socks import broadcast_to_hub
from NossiSite.base import log
from NossiSite.socks import views

env = Environment(loader=PackageLoader("NossiSite"), autoescape=select_autoescape())
history_template = env.get_template("base/chathistory.html")

data: dict = {"webhook": "", "channelid": "", "botname": "Okysa", "thread": None}


def load_chat(after: int):
    with connect_db("loadchatlog") as db:
        rows = db.execute(
            "SELECT line, time, linenr FROM chatlogs WHERE linenr > ? "
            "ORDER BY linenr DESC LIMIT 100",
            [after],
        ).fetchall()
        return {
            row[2]: {
                "line": row[0],
                "time": datetime.fromtimestamp(row[1], timezone.utc).isoformat(),
            }
            for row in reversed(rows)
        }, (rows[0][2] if rows else after)


def init():
    db = connect_db("init chat")
    webhook = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'webhook'"
    ).fetchone()
    channelid = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'channelid'"
    ).fetchone()
    botname = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'botname'"
    ).fetchone()
    data["webhook"] = webhook[0] if webhook else ""
    data["channelid"] = channelid[0] if channelid else ""
    data["botname"] = botname[0] if botname else "Okysa"


def sync_chat(username, message_content, mention=None, broadcast=True):
    """
    Synchronizes a message to the local chat and Discord.
    """
    ul = Userlist()
    u = ul.loaduserbyname(username)

    # Determine names for local vs discord
    display_name = username
    if mention:
        pass
    elif u:
        discord_config = u.config("discord", "")
        discord_id_match = re.match(r"(\d+)", discord_config)
        discord_id = discord_id_match.group(1) if discord_id_match else ""
        mention = f"<@{discord_id}>" if discord_id else username
    else:
        mention = username

    # 1. Save locally to NossiNet Chat
    try:
        # Use display name for local chat
        formatted_line = f"{display_name}\n{message_content}"
        room_id = data.get("channelid")
        cr = Chatroom(room_id) if room_id else None
        if cr:
            cr.addlinetolog(formatted_line, time.time())

        if broadcast:
            # Resolve mentions for the local display if possible
            resolved_content = (
                cr.resolve_mentions(message_content) if cr else message_content
            )
            timestamp = datetime.now(timezone.utc).isoformat()
            # Broadcast via SSE for instant chat update
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
                }
            )
    except Exception as e:
        log.error(f"Local chat save failed: {e}")

    # 2. Sync to Discord Webhook (Best Effort)
    if data["webhook"]:
        # If the content already starts with a mention (like in doroll), we might want to preserve it
        # or prepend it if not present.
        content = message_content
        if mention and not content.startswith(mention):
            content = f"{mention} {content}"

        message_data = {
            "content": content,
            "username": username,
        }
        try:
            requests.post(data["webhook"], json=message_data, timeout=5)
        except Exception as e:
            log.error(f"Discord sync failed: {e}")


@views.route("/chat/history")
def chat_history():
    checklogin()
    messages, _ = load_chat(0)
    return history_template.render(
        messages=messages,
        now=datetime.now(timezone.utc).isoformat(),
    )


@views.route("/chat/send", methods=["POST"])
def chat_send():
    checklogin()
    message_content = request.form.get("message_data")
    if not message_content:
        return "", 204

    username = session.get("user")
    sync_chat(username, message_content)

    return "", 204


@views.route("/chat/livekit-token/<room_name>")
def livekit_token(room_name):
    user = session.get("user", "Anonymous")
    token = (
        api.AccessToken(
            os.environ.get("LIVEKIT_API_KEY"), os.environ.get("LIVEKIT_API_SECRET")
        )
        .with_identity(user)
        .with_name(user)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    return {"token": token.to_jwt(), "url": os.environ.get("LIVEKIT_URL")}


@views.route("/chat/debug")
def chat_debug():
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
def chatsite():
    checklogin()
    livekit_available = False
    lk_url = os.environ.get("LIVEKIT_URL")
    log.debug(f"Checking LiveKit at {lk_url}")
    if (
        lk_url
        and os.environ.get("LIVEKIT_API_KEY")
        and os.environ.get("LIVEKIT_API_SECRET")
    ):
        url = lk_url.replace("ws://", "http://").replace("wss://", "https://")
        if not url.startswith("http"):
            url = "http://" + url
        try:
            # Use a session without environment proxies for local addresses
            with requests.Session() as s:
                s.trust_env = False
                res = s.get(url, timeout=5, verify=False)
                if res.status_code == 200:
                    livekit_available = True
                    log.debug("LiveKit check: OK (200)")
                else:
                    log.warning(
                        f"LiveKit responded with status {res.status_code} at {url}"
                    )
        except Exception as e:
            log.error(f"LiveKit connectivity check failed for {url}: {e}")
    else:
        log.warning("LiveKit variables missing in environment")

    return render_template("base/chat.html", livekit_available=livekit_available)


init()
