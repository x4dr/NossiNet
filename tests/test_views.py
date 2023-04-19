from pathlib import Path
from unittest import mock

import flask
from flask import url_for, redirect
from flask.testing import FlaskClient
from werkzeug.exceptions import BadRequestKeyError

import Data
from tests.NossiTestCase import NossiTestCase


class TestViews(NossiTestCase):
    @mock.patch.object(Data, "DATABASE", "login.db")
    def test_login(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        # test response of login
        c: FlaskClient = self.app.test_client()
        c.get("/login")
        self.assert_template_used("login.html")
        # test response of register page
        c.post("/login", data=self.logindata, follow_redirects=True)
        self.assert_template_used("login.html")  # not registered
        self.register()
        c.post("/login", data=self.logindata, follow_redirects=True)
        self.assert_template_used("show_entries.html")  # not registered

    @mock.patch.object(Data, "DATABASE", "version.db")
    def test_version(self):
        self.addCleanup(self.delete, Data.DATABASE)
        c = self.app.test_client()
        self.assert200(c.get(url_for("getversion")))

    @mock.patch.object(Data, "DATABASE", "entries.db")
    def test_entries(self):
        self.addCleanup(self.delete, Data.DATABASE)
        c = self.app.test_client()
        try:
            c.get(url_for("editentries"))
        except Exception as e:
            self.assertEqual(e.args[0], "REDIR")
            self.assertEqual(
                e.args[1].get_data(),
                redirect(url_for("login", r=url_for("editentries")[1:])).get_data(),
            )
        with self.register_login() as c:
            c.get(url_for("editentries"))
            self.assertTemplateUsed("show_entries.html")
            self.assertRaises(BadRequestKeyError, c.post, url_for("editentries"))

            token = flask.session.get("print")
            # does not return the sessionprint anymore
            if not token:
                return "currently not testable"
            form = {
                "id": "new",
                "title": "testpost",
                "text": "nonpublic",
                "tags": "testtag",
                "token": token,
            }
            self.assert200(
                c.post(url_for("editentries"), data=form, follow_redirects=True)
            )
            form = {
                "id": "new",
                "title": "xxyxz",
                "text": "public",
                "tags": "",
                "token": token,
            }
            self.assert200(
                c.post(url_for("editentries"), data=form, follow_redirects=True)
            )
            rv = c.get(url_for("show_entries"))
            self.assertIn(b"xxyxz", rv.data)
            self.assertNotIn(b"testpost", rv.data)
            c.post(url_for("update_filter"), data={"tags": "testtag", "token": token})
            self.assertEqual(flask.session.get("tags", None), "testtag")
            rv = c.get(url_for("show_entries"))
            self.assertIn(b"testpost", rv.data)
            self.assertNotIn(b"xxyxz", rv.data)

    @mock.patch.object(Data, "DATABASE", "register.db")
    def test_register(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        """Make sure register user works"""
        rv = self.register()
        print(rv)
        self.assert_status(rv, 200)
        self.assertTemplateUsed("show_entries.html")  # redirected to start
        rv = self.register()
        print(rv)
        self.assertTemplateUsed("register.html")
        self.assert_message_flashed(
            f"Username {self.app.config['USERNAME'].upper()} is taken!", "error"
        )
