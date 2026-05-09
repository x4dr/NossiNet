import json
import os
import re
import threading
import time
from datetime import datetime, timezone

import requests
from flask import render_template, session, request
from jinja2 import Environment, PackageLoader, select_autoescape
from livekit import api
from simple_websocket import Server

from NossiPack.Chatrooms import Chatroom
from NossiPack.User import Userlist
from Data import connect_db
from NossiSite.helpers import checklogin
from NossiSite.socks import broadcast_to_hub
from NossiSite.base import log
from NossiSite.socks import views

env = Environment(loader=PackageLoader("NossiSite"), autoescape=select_autoescape())
template = env.get_template("base/chatmsg.html")
history_template = env.get_template("base/chathistory.html")

clients = []
last_update = {}
data: dict = {"webhook": "", "channelid": "629329117266968576", "thread": None}


def send_chat_update():
    cache = {}
    for client in list(clients):  # copy to avoid changing set while iterating
        lu = last_update.get(client) or 0
        response, last = cache.get(lu, (None, None))

        if not response:
            messages, last = load_chat(lu)
            response = template.render(
                messages=messages,
                now=datetime.now(timezone.utc).isoformat(),
            )
            cache[lu] = (response, last)
        try:
            client.send(response)
            last_update[client] = last
        except:  # noqa E722 # if any exception happens, remove client
            clients.remove(client)


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


def background_chat_update():
    while True:
        send_chat_update()
        time.sleep(5)


def init():
    t = threading.Thread(target=background_chat_update)
    t.daemon = True
    t.start()
    db = connect_db("init chat")
    webhook = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'webhook'"
    ).fetchone()
    channelid = db.execute(
        "SELECT value FROM configs WHERE user = 'bridge' AND option= 'channelid'"
    ).fetchone()
    data["webhook"] = webhook[0] if webhook else ""
    data["channelid"] = channelid[0] if channelid else "629329117266968576"
    data["thread"] = t


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

    ul = Userlist()
    username = session.get("user")
    u = ul.loaduserbyname(username)
    if not u:
        return "", 204

    # Extract only digits from the start of the config (handles "ID(username)" format)
    discord_config = u.config("discord", "")
    discord_id_match = re.match(r"(\d+)", discord_config)
    discord_id = discord_id_match.group(1) if discord_id_match else ""
    mention = f"<@{discord_id}>" if discord_id else username

    # 1. Save locally to NossiNet Chat
    try:
        formatted_line = f"{mention}\n{message_content}"
        Chatroom(data["channelid"]).addlinetolog(formatted_line, time.time())
        # Broadcast via SSE for instant chat update
        broadcast_to_hub(
            {
                "type": "chat",
                "line": message_content,
                "user": mention,
                "time": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        log.error(f"Local chat save failed: {e}")

    # 2. Sync to Discord Webhook (Best Effort)
    if data["webhook"]:
        message_data = {
            "content": message_content,
            "username": username,  # Keep username for Discord sender identity
        }
        try:
            requests.post(data["webhook"], json=message_data, timeout=5)
        except Exception as e:
            log.error(f"Discord sync failed: {e}")

    return "", 204


@views.route("/ws-chatupdates", websocket=True)
def chat_updates():
    log.info("WebSocket connection attempt on /ws-chatupdates")
    try:
        ws = Server.accept(request.environ)
        log.info(
            f"WebSocket connection accepted for user: {session.get('user', 'Anonymous')}"
        )
    except Exception as e:
        log.error(f"WebSocket acceptance failed: {e}")
        return ""

    clients.append(ws)
    while True:
        try:
            x = ws.receive()
            if x:
                message_content = json.loads(str(x))["message_data"]
                username = session.get("user", "Anonymous")

                # 1. Save locally to NossiNet Chat
                try:
                    formatted_line = f"{username}: {message_content}"
                    Chatroom(data["channelid"]).addlinetolog(
                        formatted_line, time.time()
                    )
                except Exception as e:
                    log.error(f"Local chat save failed: {e}")

                # 2. Sync to Discord Webhook (Best Effort)
                if data["webhook"]:
                    message_data = {
                        "content": message_content,
                        "username": username,
                    }
                    try:
                        requests.post(data["webhook"], json=message_data, timeout=5)
                    except Exception as e:
                        log.error(f"Discord sync failed: {e}")
        except Exception as e:
            log.error(f"WebSocket receive error: {e}")
            break
    clients.remove(ws)
    return ""


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
