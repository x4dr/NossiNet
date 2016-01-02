from flask import Flask
import eventlet

from flask_socketio import SocketIO

async_mode = 'eventlet'
eventlet.monkey_patch()

app = Flask(__name__)

DATABASE = './NN.db'
SECRET_KEY = 'ajdjJFeiJjFnnm88e4ko94VBPhzgY34'
app.config.from_object(__name__)
socketio = SocketIO(app, async_mode=async_mode)


import NossiSite.views
import NossiSite.chat
import NossiSite.helpers
