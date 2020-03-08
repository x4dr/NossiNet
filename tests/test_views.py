from pathlib import Path
from unittest import mock

from flask import Flask
from flask_testing import TestCase

from NossiPack.krypta import Data, close_db
from NossiSite import views


def delete(x):
    if Path(x).exists():
        Path(x).unlink()


class TestViews(TestCase):
    render_templates = False

    # if the create_app is not implemented NotImplementedError will be raised
    def create_app(self):
        close_db()  # might be open
        app = Flask(__name__)
        views.register(app)
        app.template_folder = "../NossiSite/templates"
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config.from_mapping(SECRET_KEY="dev",)
        print(self.countTestCases())
        return app

    @mock.patch.object(Data, "DATABASE", "login.db")
    def test_login(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        # test response of login
        app = self.create_app()
        c = app.test_client()
        c.get("/login")
        self.assert_template_used("login.html")
        form = {
            "username": app.config["USERNAME"],
            "password": app.config["PASSWORD"],
        }
        # test response of register page
        c.post("/login", data=form, follow_redirects=True)
        self.assert_template_used("login.html")  # not registered
        form = {
            "username": app.config["USERNAME"],
            "password": app.config["PASSWORD"],
            "passwordcheck": app.config["PASSWORD"],
        }
        c.post("/register", data=form)  # register
        c.post("/login", data=form, follow_redirects=True)
        self.assert_template_used("show_entries.html")  # not registered

    @mock.patch.object(Data, "DATABASE", "version.db")
    def test_version(self):
        self.addCleanup(delete, Data.DATABASE)
        app = self.create_app()
        c = app.test_client()
        self.assert200(c.get("/version"))

    @mock.patch.object(Data, "DATABASE", "register.db")
    def test_register(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        """Make sure register user works"""
        app = self.create_app()
        c = app.test_client()
        # mock site interaction
        form = {
            "username": app.config["USERNAME"],
            "password": app.config["PASSWORD"],
            "passwordcheck": app.config["PASSWORD"],
        }
        # register with mock
        rv = c.post("/register", data=form, follow_redirects=True)
        print(rv)
        self.assert_status(rv, 200)
        self.assertTemplateUsed("show_entries.html")  # redirected to start

        rv = c.post("/register", data=form)
        print(rv)
        self.assertTemplateUsed("register.html")
        self.assert_message_flashed(
            f"Username {app.config['USERNAME'].upper()} is taken!", "error"
        )
