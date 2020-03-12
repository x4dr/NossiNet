from flask import Flask
from flask_testing import TestCase

from NossiPack.krypta import close_db
from NossiSite import wiki, helpers
from NossiSite.helpers import wikisave


class TestViews(TestCase):
    render_templates = False

    # if the create_app is not implemented NotImplementedError will be raised
    def create_app(self):
        close_db()  # might be open
        app = Flask(__name__)
        wiki.register(app)
        app.template_folder = "../NossiSite/templates"
        app.config["TESTING"] = True
        # Set to 0 to have the OS pick the port.
        app.config["LIVESERVER_PORT"] = 0
        app.config["USERNAME"] = "unittest"
        app.config["PASSWORD"] = "unittest"
        app.config.from_mapping(SECRET_KEY="dev",)
        print(self.countTestCases())
        return app

    def setUp(self) -> None:
        pass  # DB created during normal usage

    def test_ewparsing(self):
        wikisave(
            "unittest_character",
            "",
            "",
            "",
            "#Layer1\n##layer2\n###layer3\ntext\n###layer 3 again\n"
            "more text\n##some more layer 2\n a|b\n--|--\nc|d\n but what about THIS\n###finalthird\nfinal text\n",
        )
        self.render_templates = False
        app = self.create_app()
        helpers.register(app)
        c = app.test_client()
        c.get("/ewsheet/test")
        self.create_app()
