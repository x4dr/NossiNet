from flask import Flask
import eventlet
import os
import random
import string


from flask_socketio import SocketIO

async_mode = 'eventlet'
eventlet.monkey_patch()

app = Flask(__name__)

DATABASE = './NN.db'
i = 0
while i < 10:
    key=""
    try:
        with open(os.path.join(os.path.expanduser('~'), 'key'), 'r') as keyfile:
            key = keyfile.read()
    except:
        with open(os.path.join(os.path.expanduser('~'), 'key'), 'w') as keyfile:
            keyfile.write(''.join(random.SystemRandom().choice(string.printable) for _ in range(48)))
    i+=1
    if key != "":
        i += 9

SECRET_KEY = key  # should invalidate cookies
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode)
import NossiSite.views

import NossiSite.chat

import NossiSite.helpers
