import logging

from github_webhook import Webhook

from NossiSite.base import app as defaultapp

logger = logging.getLogger(__name__)


def register(app=None):
    if app is None:
        app = defaultapp
    ghwh = Webhook(app, endpoint="/postreceive", secret=app.config["SECRET_KEY"])

    @ghwh.hook()
    def on_push(req):
        if req["repository"]["name"] == "NossiNet":
            exit(4)
        else:
            logger.error(f"got unexpected request from: {req['repository']['name']}")
