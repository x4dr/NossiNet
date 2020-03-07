from pathlib import Path

from flask_testing import TestCase

from NossiSite.base import app as nossinet


def delete(file: Path):
    if file.exists():
        file.unlink()


class TestViews(TestCase):
    render_templates = False

    # if the create_app is not implemented NotImplementedError will be raised
    def create_app(self, db=None):
        db_path = Path.cwd().absolute() / f"{db}.db"
        if db is None:
            db = "test"  # will not be created by flask on default call by TestCase
            (Path.cwd().absolute() / f"{db}.db").touch()  # thus, create now
        app = nossinet
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config.from_mapping(
            SECRET_KEY="dev", DATABASE=db_path,
        )
        self.addCleanup(delete, db_path)
        return app

    def test_login(self):
        # test response of register page
        app = self.create_app("login")
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

    def test_register(self):
        """Make sure register user works"""
        app = self.create_app("register")
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
