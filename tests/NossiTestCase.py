from pathlib import Path

from flask import Flask, url_for
from flask_testing import TestCase

from NossiPack.krypta import close_db
from NossiSite import views, wiki, extra, webhook, helpers


class NossiTestCase(TestCase):
    # if the create_app is not implemented NotImplementedError will be raised
    @property
    def logindata(self):
        return {
            "username": self.app.config["USERNAME"],
            "password": self.app.config["PASSWORD"],
            "passwordcheck": self.app.config["PASSWORD"],
        }

    def create_app(self):
        close_db()  # might be open
        app = Flask(__name__)
        views.register(app)
        wiki.register(app)
        extra.register(app)
        webhook.register(app)
        helpers.register(app)
        app.url_build_error_handlers.append(lambda a, b, c: "404")
        app.template_folder = "../NossiSite/templates"
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config.from_mapping(SECRET_KEY="dev",)
        print(self.countTestCases())
        return app

    @staticmethod
    def delete(x):
        if Path(x).exists():
            Path(x).unlink()

    def register(self):

        # register with mock
        return self.app.test_client().post(
            url_for("register_user"), data=self.logindata, follow_redirects=True
        )

    def register_login(self):
        tc = self.app.test_client()
        tc.post(url_for("register_user"), data=self.logindata)
        tc.post(url_for("login"), data=self.logindata)
        return tc
