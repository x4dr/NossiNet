import sys
import Data
import logging.config
from NossiSite import views, chat, wiki, extra, webhook, helpers
from NossiSite.base import app, socketio

logging.config.fileConfig(Data.handle("logging_config.conf"))
# register the endpoints
views.register(app)
chat.register(app, socketio)
wiki.register(app),
extra.register(app)
webhook.register(app)
helpers.register(app)

if __name__ == "__main__":
    logging.warning("Nosferatu net being run directly, DO NOT USE IN PRODUCTION")
    test = False
    try:
        port = int(sys.argv[1])
    except Exception:
        port = 5000
    socketio.run(app, "0.0.0.0", debug=True, port=port)

    logging.warning("Nosferatu net closing")
