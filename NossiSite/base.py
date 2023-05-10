import logging
import os
import random
import string

from flask import Flask
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

async_mode = "eventlet"

app = Flask(__name__)
CSRFProtect(app)
i = 0

key = ""
try:
    with open(os.path.join(os.path.expanduser("~"), "key"), "r") as keyfile:
        key = keyfile.read()
except FileNotFoundError:
    with open(os.path.join(os.path.expanduser("~"), "key"), "w") as keyfile:
        key = "".join(random.SystemRandom().choice(string.hexdigits) for _ in range(48))
        keyfile.write(key)

SECRET_KEY = key
SESSION_COOKIE_SECURE = True
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")
socketio.init_app(app, cors_allowed_origins="*")
log = logging.getLogger("frontend")
fh = logging.FileHandler("nossilog.log", mode="w")
fh.setLevel(logging.DEBUG)
log.addHandler(fh)
logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s")
log.setLevel(logging.DEBUG)
