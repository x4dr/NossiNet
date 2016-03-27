from flask import Flask
import eventlet
import random
import string

from flask_socketio import SocketIO


async_mode = 'eventlet'
eventlet.monkey_patch()

app = Flask(__name__)

DATABASE = './NN.db'

with open('key', 'w') as keyfile:
    key = keyfile.read()
SECRET_KEY = key  #should invalidate cookies
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode)


import NossiSite.views
import NossiSite.chat
import NossiSite.helpers
