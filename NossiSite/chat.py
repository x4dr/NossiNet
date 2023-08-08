import json
import threading
import time
from datetime import datetime

import requests
import simple_websocket
from flask import Blueprint, render_template, session
from flask_sock import Sock
from jinja2 import Environment, PackageLoader, select_autoescape
from Data import connect_db

env = Environment(loader=PackageLoader("NossiSite"), autoescape=select_autoescape())
template = env.get_template("chatmsg.html")

views = Blueprint("chat", __name__)
sock = Sock()
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
                now=datetime.now().isoformat(),
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
            row[2]: {"line": row[0], "time": datetime.fromtimestamp(row[1]).isoformat()}
            for row in reversed(rows)
        }, rows[0][2] if rows else after


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


@sock.route("/chatupdates")
def chat_updates(ws: simple_websocket.ws):
    clients.append(ws)
    while True:
        try:
            x = ws.receive()
            if data["webhook"]:
                message_data = {
                    "content": json.loads(x)["message_data"],
                    "username": session["user"],
                }
                result = requests.post(data["webhook"], json=message_data)
                result.raise_for_status()
                print(result.content)
        except Exception as e:
            print(e)
            break
    clients.remove(ws)


@views.route("/chat")
def chat():
    return render_template("chat.html")


init()
