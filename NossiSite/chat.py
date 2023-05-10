from flask_socketio import Namespace


class Chat(Namespace):
    def on_connect(self):
        # reply with a message when connected
        self.emit("message", {"data": "Welcome to the Nosferatu Network!"})

    def on_message(self, message):
        # reply with the same message
        self.emit("message", {"data": message["data"]})
