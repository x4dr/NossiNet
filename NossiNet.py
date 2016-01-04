# from flask_socketio import SocketIO

from NossiSite import app, socketio

socketio.run(app, "127.0.0.1", debug=True)
