from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from NossiSite import helpers
from NossiSite.wiki import wikisave
from tests.NossiTestCase import NossiTestCase


class TestViews(NossiTestCase):
    render_templates = False

    def setUp(self) -> None:
        pass  # DB created during normal usage

    @mock.patch.object(Data, "DATABASE", "index.db")
    def test_index(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        with self.register_login() as c:
            print(c.get(url_for("wiki_index")))

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
