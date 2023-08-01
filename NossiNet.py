import logging.config
import sys
import Data
from NossiSite import views, wiki, extra, webhook, helpers, chat
from NossiSite.base import app, socketio

logging.config.fileConfig(Data.handle("logging_config.conf"))
# register the endpoints
app.register_blueprint(views.views)
app.register_blueprint(wiki.views)
app.register_blueprint(extra.views)
socketio.on_namespace(chat.Chat("/chat"))
webhook.register(app)
helpers.register(app)


if __name__ == "__main__":
    logging.warning("Nosferatu net being run directly, DO NOT USE IN PRODUCTION")

    test = False
    try:
        port = int(sys.argv[1])
    except Exception:
        port = 5000
    app.run(
        host="127.0.0.1",
        debug=True,
        port=port,
        use_reloader=False,
        ssl_context="adhoc",
    )

    logging.warning("Nosferatu net closing")
