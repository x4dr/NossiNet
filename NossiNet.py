# from flask_socketio import SocketIO

from NossiSite import app, socketio

socketio.run(app, "0.0.0.0", debug=False)
