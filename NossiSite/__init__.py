from flask import Flask
import eventlet
import random
import string

from flask_socketio import SocketIO


async_mode = 'eventlet'
eventlet.monkey_patch()

app = Flask(__name__)

DATABASE = './NN.db'
SECRET_KEY = ''.join(random.SystemRandom().choice(string.printable) for _ in range(48))  #should invalidate cookies
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode)


import NossiSite.views
import NossiSite.chat
import NossiSite.helpers
