import logging.config
import sys

import Data
from NossiSite import views, extra, webhook, helpers, chat, socks, wiki, sheets
from NossiSite.base import app
from gamepack.WikiPage import WikiPage, start_savequeue

logconf = Data.handle("logging_config.conf")
logging.config.fileConfig(logconf, disable_existing_loggers=False)

# register the endpoints
app.register_blueprint(views.views)
app.register_blueprint(wiki.views)
app.register_blueprint(sheets.views)

socks.start_threads()
app.register_blueprint(extra.views)
app.register_blueprint(chat.views)
webhook.register(app)
helpers.register(app)

WikiPage.live = True
start_savequeue()

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
        ssl_context=("cert.pem", "key.pem") if not test else None,
    )

    logging.warning("Nosferatu net closing")
