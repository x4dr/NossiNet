"""Tests for the main views blueprint (login, registration, entries)."""

from unittest import mock

from flask import url_for
from werkzeug.exceptions import BadRequestKeyError

import Data
from tests.NossiTestCase import NossiTestCase


class TestViews(NossiTestCase):
    """Test cases for login, registration, entries, and version endpoints."""

    @mock.patch.object(Data, "DATABASE", "login.db")
    def test_login(self) -> None:
        """Verify login page rendering, failed login, and successful login after registration."""
        try:
            with self.app.app_context():
                rv = self.client.get("/login")
                self.assert_template_used("base/login.html")
                self.assertEqual(rv.status_code, 200)

                rv = self.client.post(
                    "/login",
                    data=self.logindata,
                    follow_redirects=True,
                )
                self.assert_template_used("base/login.html")  # not registered

                # now register
                self.register()
                rv = self.client.post(
                    "/login",
                    data=self.logindata,
                    follow_redirects=True,
                )
                self.assert_template_used("base/show_entries.html")
        finally:
            self.delete("login.db")

    @mock.patch.object(Data, "DATABASE", "version.db")
    def test_version(self) -> None:
        """Verify the version endpoint returns HTTP 200."""
        try:
            with self.app.app_context():
                rv = self.client.get(url_for("views.getversion"))
                self.assertEqual(rv.status_code, 200)
        finally:
            self.delete("version.db")

    @mock.patch.object(Data, "DATABASE", "entries.db")
    def test_entries(self) -> None:
        """Verify entry creation, filtering, and public/private visibility."""
        try:
            # not logged in
            with self.app.app_context():
                try:
                    self.client.get(url_for("views.editentries"))
                except Exception as e:
                    assert e.args[0] == "REDIR"

            # logged in
            c = self.register_login()
            with self.app.app_context():
                rv = c.get(url_for("views.editentries"))
                self.assert_template_used("base/show_entries.html")

                # empty post triggers BadRequestKeyError
                with self.assertRaises(BadRequestKeyError):
                    c.post(url_for("views.editentries"))

                # post new entries
                form1 = {
                    "id": "new",
                    "title": "testpost",
                    "text": "nonpublic",
                    "tags": "testtag",
                }
                rv = c.post(
                    url_for("views.editentries"),
                    data=form1,
                    follow_redirects=True,
                )
                self.assertEqual(rv.status_code, 200)

                form2 = {"id": "new", "title": "xxyxz", "text": "public", "tags": ""}
                rv = c.post(
                    url_for("views.editentries"),
                    data=form2,
                    follow_redirects=True,
                )
                self.assertEqual(rv.status_code, 200)

                rv = c.get(url_for("views.show_entries"))
                assert b"xxyxz" in rv.data
                assert b"testpost" not in rv.data

                # filter test
                c.post(url_for("views.update_filter"), data={"tags": "testtag"})
                with c.session_transaction() as sess:
                    assert sess.get("tags") == "testtag"

                rv = c.get(url_for("views.show_entries"))
                assert b"testpost" in rv.data
                assert b"xxyxz" not in rv.data

        finally:
            self.delete("entries.db")

    @mock.patch.object(Data, "DATABASE", "register.db")
    def test_register(self) -> None:
        """Verify user registration and duplicate username rejection."""
        try:
            with self.app.app_context(), self.app.test_client() as c:
                # --- First registration ---
                with c.post(
                    url_for("views.register_user"),
                    data=self.logindata,
                    follow_redirects=True,  # keep flash in session
                ) as rv:
                    self.assertIn(
                        "User successfully created.",
                        rv.get_data(as_text=True),
                    )
                    self.assertEqual(rv.status_code, 200)
                    self.assert_template_used("base/show_entries.html")
                # --- Duplicate registration ---
                with c.post(
                    url_for("views.register_user"),
                    data=self.logindata,
                    follow_redirects=True,
                ) as rv:
                    self.assertIn(
                        f"Username {self.app.config['USERNAME'].upper()} is taken!",
                        rv.get_data(as_text=True),
                    )
                    self.assertEqual(rv.status_code, 200)
                    self.assert_template_used("base/register.html")

        finally:
            self.delete("register.db")
