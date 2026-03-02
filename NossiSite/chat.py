import json
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import render_template, session, request
from jinja2 import Environment, PackageLoader, select_autoescape
from livekit import api
from simple_websocket import Server

from Data import connect_db
from NossiSite.helpers import checklogin
from NossiSite.base import log
from NossiSite.socks import views

env = Environment(loader=PackageLoader("NossiSite"), autoescape=select_autoescape())
template = env.get_template("base/chatmsg.html")

clients = []
last_update = {}
data: dict = {"webhook": "", "thread": None}


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
    data["webhook"] = webhook[0] if webhook else ""
    data["thread"] = t


@views.route("/ws-chatupdates", websocket=True)
def chat_updates():
    ws = Server.accept(request.environ)
    clients.append(ws)
    while True:
        try:
            x = ws.receive()
            if x and data["webhook"]:
                message_data = {
                    "content": json.loads(str(x))["message_data"],
                    "username": session["user"],
                }
                result = requests.post(data["webhook"], json=message_data)
                result.raise_for_status()
                print(result.content)
        except Exception as e:
            print(e)
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
