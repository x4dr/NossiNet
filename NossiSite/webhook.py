import logging
import os

from github_webhook import Webhook

from NossiSite.base import app as defaultapp

logger = logging.getLogger(__name__)


def register(app=None):
    if app is None:
        app = defaultapp
    ghwh = Webhook(app, endpoint="/postreceive", secret=app.config["SECRET_KEY"])

    @ghwh.hook()
    def on_push(req):
        repo = req["repository"]["name"]
        if repo in ["NossiNet", "Okysa", "Gamepack"]:
            os.system(f"redeploy {repo}")
        else:
            logger.error(f"got unexpected request from: {req['repository']['name']}")
