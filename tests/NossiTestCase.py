import unittest
from pathlib import Path

from flask import Flask, url_for, template_rendered
from flask_wtf import CSRFProtect

from Data import close_db
from NossiSite import views, wiki, extra, webhook, helpers
from gamepack.WikiPage import WikiPage


class NossiTestCase(unittest.TestCase):
    @property
    def logindata(self):
        return {
            "username": self.app.config["USERNAME"],
            "password": self.app.config["PASSWORD"],
            "passwordcheck": self.app.config["PASSWORD"],
        }

    def setUp(self):
        if WikiPage._wikipath is None:
            WikiPage.set_wikipath(Path("."))

        close_db()  # ensure no DB is open
        self.app = self.create_app()
        self.client = self.app.test_client()
        self._templates = []

        # connect template signal
        template_rendered.connect(self._record_template, self.app)

    def tearDown(self):
        template_rendered.disconnect(self._record_template, self.app)

    def _record_template(self, sender, template, context, **extra):
        self._templates.append(template.name)

    def create_app(self):
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
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config["SECRET_KEY"] = "dev"
        app.config["SERVER_NAME"] = "localhost.localdomain"
        app.config["APPLICATION_ROOT"] = "/"
        app.config["PREFERRED_URL_SCHEME"] = "http"
        return app

    @staticmethod
    def delete(path):
        p = Path(path)
        if p.exists():
            p.unlink()

    def register(self):
        return self.client.post(
            url_for("views.register_user"),
            data=self.logindata,
            follow_redirects=True,
        )

    def register_login(self, client=None):
        if client is None:
            client = self.app.test_client()
        with self.app.app_context():
            client.post(url_for("views.register_user"), data=self.logindata)
            client.post(url_for("views.login"), data=self.logindata)
        return client

    # helpers for assertions
    def assertTemplateUsed(self, template_name):
        self.assertIn(template_name, self._templates)
