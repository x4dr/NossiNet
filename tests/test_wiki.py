from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from NossiPack.FenCharacter import FenCharacter
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

    def test_xp_parsing(self):
        self.assertEqual(
            FenCharacter.parse_xp(
                "[Worograd, Istan, Dinas Godol, Yonn]KKLP(1/3) (nvm)"
            ),
            7,
        )

    def test_matrix_parsing(self):
        testdat = {"_lines": ["|a|b|c", "-|-|-|", "|1|2|3|4", "hi|ho|hu"]}
        sut = FenCharacter.parse_matrix(testdat)
        self.assertEqual(
            testdat["_lines"], ["|a|b|c", "-|-|-|", "|1|2|3|4", "hi|ho|hu"]
        )
        self.assertEqual(sut, [])

        testdat = {"_lines": ["|a|b|c", "-|-|-|", "|1|2|3|", "hi|ho|hu"]}
        sut = FenCharacter.parse_matrix(testdat)
        self.assertEqual(sut, [])  # uneven format
        testdat = {"_lines": ["|a|b|c|", "|-|-|-|", "|1|2|3|", "|4|5|6|", "|Total|||"]}
        sut = FenCharacter.parse_matrix(testdat)
        self.assertEqual(testdat["_lines"], [])
        self.assertEqual(sut[4][2], "9.0")
        self.assertEqual(sut[4][0], "Total")
