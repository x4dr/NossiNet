import logging
import os
import random
import string

from flask import Flask
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
CSRFProtect(app)


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
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 7  #
app.config.from_object(__name__)
log = logging.getLogger("frontend")
fh = logging.FileHandler("nossilog.log", mode="w")
fh.setLevel(logging.DEBUG)
log.addHandler(fh)
logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s")
log.setLevel(logging.DEBUG)
app.jinja_env.globals["restart_id"] = "".join(
    random.SystemRandom().choice(string.hexdigits) for _ in range(4)
)
