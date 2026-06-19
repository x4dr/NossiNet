"""Base test case for NossiNet integration tests."""

import unittest
from pathlib import Path
from typing import Any

from flask import Flask, template_rendered, url_for
from flask.testing import FlaskClient
from flask_wtf import CSRFProtect  # type: ignore[import-untyped]
from gamepack.WikiPage import WikiPage

from Data import close_db
from NossiSite import extra, helpers, views, webhook


class NossiTestCase(unittest.TestCase):
    """Base test class providing app setup, login helpers, and template assertions."""

    @property
    def logindata(self) -> dict[str, str]:
        """Return login credentials matching the test app configuration."""
        return {
            "username": self.app.config["USERNAME"],
            "password": self.app.config["PASSWORD"],
            "passwordcheck": self.app.config["PASSWORD"],
        }

    def setUp(self) -> None:
        """Set up the test app, client, and template recording."""
        # Thoroughly reset wikipath
        WikiPage._wikipath = None
        WikiPage.set_wikipath(Path())

        close_db()  # ensure no DB is open
        self.app = self.create_app()
        self.client = self.app.test_client()
        self._templates: list[str] = []

        # connect template signal
        template_rendered.connect(self._record_template, self.app)

    def tearDown(self) -> None:
        """Tear down the test app and disconnect template signal."""
        template_rendered.disconnect(self._record_template, self.app)

    def _record_template(self, _sender: Flask, template: Any, _context: dict[str, object], **_extra: object) -> None:
        self._templates.append(template.name)

    def create_app(self) -> Flask:
        """Create and configure a Flask test app with all blueprints."""
        from unittest import mock

        with mock.patch.object(WikiPage, "set_wikipath"):
            from NossiSite import wiki

        app = Flask(__name__)
        app.register_blueprint(views.views)
        app.register_blueprint(wiki.views)
        app.register_blueprint(extra.views)
        webhook.register(app)
        helpers.register(app)
        CSRFProtect(app)
        app.config["WTF_CSRF_ENABLED"] = False
        app.url_build_error_handlers.append(lambda a, b, c: "404")  # noqa: ARG005
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
    def delete(path: str | Path) -> None:
        """Delete a file at the given path if it exists."""
        p = Path(path)
        if p.exists():
            p.unlink()

    def register(self) -> Any:
        """Register the test user via the registration endpoint."""
        return self.client.post(
            url_for("views.register_user"),
            data=self.logindata,
            follow_redirects=True,
        )

    def register_login(self, client: FlaskClient | None = None) -> FlaskClient:
        """Register and log in the test user, returning the client."""
        if client is None:
            client = self.app.test_client()
        with self.app.app_context():
            client.post(url_for("views.register_user"), data=self.logindata)
            client.post(url_for("views.login"), data=self.logindata)
        return client

    def assert_template_used(self, template_name: str) -> None:
        """Assert that a given template was rendered during the test."""
        self.assertIn(template_name, self._templates)
