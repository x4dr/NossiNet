from pathlib import Path

from flask import Flask, url_for
from flask_testing import TestCase
from flask_wtf import CSRFProtect
from gamepack.WikiPage import WikiPage

from Data import close_db
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
        if WikiPage._wikipath is None:
            WikiPage.set_wikipath(Path("."))
        close_db()  # might be open
        app = Flask(__name__)
        app.register_blueprint(views.views)
        app.register_blueprint(wiki.views)
        app.register_blueprint(extra.views)
        webhook.register(app)
        helpers.register(app)
        CSRFProtect(app)
        app.config["WTF_CSRF_ENABLED"] = False
        app.url_build_error_handlers.append(lambda a, b, c: "404")
        app.template_folder = "../NossiSite/templates"
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config.from_mapping(
            SECRET_KEY="dev",
        )
        return app

    @staticmethod
    def delete(x):
        if Path(x).exists():
            Path(x).unlink()

    def register(self):
        # register with mock
        return self.app.test_client().post(
            url_for("views.register_user"), data=self.logindata, follow_redirects=True
        )

    def register_login(self):
        tc = self.app.test_client()
        tc.post(url_for("views.register_user"), data=self.logindata)
        tc.post(url_for("views.login"), data=self.logindata)
        return tc
