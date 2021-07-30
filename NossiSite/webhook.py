from github_webhook import Webhook

from NossiSite.base import app as defaultapp


def register(app=None):
    if app is None:
        app = defaultapp
    ghwh = Webhook(app, endpoint="/postreceive", secret=app.config["SECRET_KEY"])

    @ghwh.hook()
    def on_push(req):
        if req["repository"]["name"] == "NossiNet":
            exit(4)
        else:
            print("got request from:", req["repository"]["name"])
