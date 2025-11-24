from unittest import mock

from flask import url_for

import Data
from tests.NossiTestCase import NossiTestCase


class TestViews(NossiTestCase):

    @mock.patch.object(Data, "DATABASE", "login.db")
    def test_login(self):
        try:
            with self.app.app_context():
                rv = self.client.get("/login")
                self.assertTemplateUsed("base/login.html")
                self.assertEqual(rv.status_code, 200)

                rv = self.client.post(
                    "/login", data=self.logindata, follow_redirects=True
                )
                self.assertTemplateUsed("base/login.html")  # not registered

                # now register
                self.register()
                rv = self.client.post(
                    "/login", data=self.logindata, follow_redirects=True
                )
                self.assertTemplateUsed("base/show_entries.html")
        finally:
            self.delete("login.db")

    @mock.patch.object(Data, "DATABASE", "version.db")
    def test_version(self):
        try:
            with self.app.app_context():
                rv = self.client.get(url_for("views.getversion"))
                self.assertEqual(rv.status_code, 200)
        finally:
            self.delete("version.db")

    @mock.patch.object(Data, "DATABASE", "entries.db")
    def test_entries(self):
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
                self.assertTemplateUsed("base/show_entries.html")

                # empty post triggers BadRequestKeyError
                with self.assertRaises(Exception):  # BadRequestKeyError
                    c.post(url_for("views.editentries"))

                # post new entries
                form1 = {
                    "id": "new",
                    "title": "testpost",
                    "text": "nonpublic",
                    "tags": "testtag",
                }
                rv = c.post(
                    url_for("views.editentries"), data=form1, follow_redirects=True
                )
                self.assertEqual(rv.status_code, 200)

                form2 = {"id": "new", "title": "xxyxz", "text": "public", "tags": ""}
                rv = c.post(
                    url_for("views.editentries"), data=form2, follow_redirects=True
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
    def test_register(self):
        try:
            with self.app.app_context():
                with self.app.test_client() as c:
                    # --- First registration ---
                    with c.post(
                        url_for("views.register_user"),
                        data=self.logindata,
                        follow_redirects=True,  # keep flash in session
                    ) as rv:
                        self.assertIn(
                            "User successfully created.", rv.get_data(as_text=True)
                        )
                        self.assertEqual(rv.status_code, 200)
                        self.assertTemplateUsed("base/show_entries.html")
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
                        self.assertTemplateUsed("base/register.html")

        finally:
            self.delete("register.db")
