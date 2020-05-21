from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from Fantasy.Item import fenconvert, fendeconvert
from NossiPack.FenCharacter import FenCharacter
from NossiPack.fengraph import armordata
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

    def test_FenCharacter_cost(self):
        sut = [
            FenCharacter.cost_calc("1,0,1"),
            FenCharacter.cost_calc("3,2,4"),
            FenCharacter.cost_calc("4,4,5"),
        ]
        self.assertEqual([0, 110, 320], sut)
        self.assertEqual(
            [[3, 3, 2], [4, 3, 1], [5, 1, 1], [4, 2, 2]], FenCharacter.cost_calc("100")
        )

    def test_fenconvert(self):
        self.assertEqual(fenconvert("30kg"), 30000)
        self.assertEqual(fendeconvert(30000, "weight"), "30kg")
        self.assertEqual(fendeconvert(30001, "weight"), "30.001kg")
        self.assertEqual(fendeconvert(31, "weight"), "31gr")
        self.assertEqual(fendeconvert(3000000001, "weight"), "3000.000001t")
        self.assertEqual(fendeconvert(fenconvert("252s"), "money"), "2.52g")
        self.assertEqual(fendeconvert(fenconvert("3332c"), "money"), "33.32s")
        self.assertEqual(fendeconvert(fenconvert("0.001g"), "money"), "10c")

    def test_armor(self):
        d = armordata()
        for a in d.values():
            n = a.name
            a.apply_mods(
                "N <> of Resilience, P x+2,S x+1, Wx/2, K x *1.1, R 100 * (x/100) **2"
            )
            self.assertTrue(a.name.endswith("Resilience") and a.name.startswith(n))
        a = list(d.values())[0]
        n = a.name
        a.apply_mods("N<>a")
        a.apply_mods("Nb<>")
        self.assertEqual(a.name, f"b{n}a")
