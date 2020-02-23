import os
import random
import string

import eventlet
from flask import Flask
from flask_socketio import SocketIO
from github_webhook import Webhook

async_mode = 'eventlet'
eventlet.monkey_patch()

app = Flask(__name__)

DATABASE = './NN.db'
i = 0

key = ""
try:
    with open(os.path.join(os.path.expanduser('~'), 'key'), 'r') as keyfile:
        key = keyfile.read()
except:
    with open(os.path.join(os.path.expanduser('~'), 'key'), 'w') as keyfile:
        key = ''.join(random.SystemRandom().choice(string.hexdigits) for _ in range(48))
        keyfile.write(key)


SECRET_KEY = key
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode)
webhook = Webhook(app, endpoint="/postreceive", secret=SECRET_KEY)

import NossiSite.helpers

from NossiSite.helpers import log

import NossiSite.views

import NossiSite.chat

import NossiSite.github_webhook
