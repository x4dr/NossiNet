import logging
import os
import threading

from flask import jsonify
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
            response = jsonify({"message": "Update received, restarting..."})
            threading.Timer(1, os._exit, [1]).start()  # shut down to be restarted
            return response
        else:
            logger.error(f"got unexpected request from: {req['repository']['name']}")
