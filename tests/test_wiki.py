from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from Fantasy.Item import fenconvert, fendeconvert
from NossiPack.FenCharacter import FenCharacter
from NossiPack.MDPack import (
    table,
    split_row,
    split_md,
    search_tables,
    table_remove,
    table_add,
    table_edit,
)
from NossiPack.fengraph import armordata
from NossiSite import helpers
from NossiSite.wiki import wikisave, fill_infolets
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
            "unittest",
            "",
            "",
            "character",
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

    def test_FenCharacter_cost(self):
        sut = [
            FenCharacter.cost_calc("1,0,1"),
            FenCharacter.cost_calc("3,2,4"),
            FenCharacter.cost_calc("4,4,5"),
        ]
        self.assertEqual([0, 16, 24], sut)
        self.assertEqual(
            [(4, 4, 1), (4, 3, 2), (5, 3, 1), (5, 2, 2), (3, 3, 3)],
            FenCharacter.cost_calc("17"),
        )

    def test_fenconvert(self):
        self.assertEqual(fenconvert("30kg"), 30000)
        self.assertEqual(fendeconvert(30000, "weight"), "30kg")
        self.assertEqual(fendeconvert(30001, "weight"), "30.001kg")
        self.assertEqual(fendeconvert(31, "weight"), "31g")
        self.assertEqual(fendeconvert(3000000001, "weight"), "3000.000001t")
        self.assertEqual(fendeconvert(fenconvert("252s"), "money"), "2.52a")
        self.assertEqual(fendeconvert(fenconvert("3332c"), "money"), "33.32s")
        self.assertEqual(fendeconvert(fenconvert("0.001a"), "money"), "10k")

    def test_table_md(self):
        self.assertEqual(["", "", "a"], split_row("||a", 3))
        self.assertEqual([["a", "b"], ["1", "2"]], table("|a|b|\n|-|-\n1|2\n"))
        self.assertEqual([], table("h|i"))
        self.assertEqual(
            [["a", "b"], ["1", "2"], ["extra", ""]],
            table("|a|b|cut\n|-|-\n1|2\nextra\n"),
        )

    def test_split_md(self):
        self.assertEqual(
            (
                " abctext\n",
                {
                    "first heading": (
                        "",
                        {
                            "first subhead": (
                                "                    first subhead text\n                    with multiple lines\n",
                                {"subsub": ("                    subsub text\n", {})},
                            ),
                            "second subhead": ("                    moretext\n", {}),
                        },
                    ),
                    "next heading": ("                    direct text\n", {}),
                },
            ),
            split_md(
                """ abctext
                    # first heading
                    ## first subhead
                    first subhead text
                    with multiple lines
                    ### subsub
                    subsub text
                    ## second subhead
                    moretext
                    # next heading
                    direct text"""
            ),
        )

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

    def test_infolets(self):
        sut = fill_infolets("[[specific:healing:heilung:aurier:resonanzen:-]]", "test")
        self.assertIn("Wunde", sut)

    def test_wounds(self):
        sut = FenCharacter.from_md("#Character\n##Wounds\nQuelle|Code\n-|-\ntest|2:3:1")
        sut.wounds()

    def test_tablesrearch(self):
        sut = "##somestuff\n|a|b|\n|-|-|\n|x|1|\ny|2\n"
        self.assertEqual(search_tables(sut, "y", 0), "y|2\n")
        sut = table_add(sut, "z", "3")
        sut = table_remove(sut, "y")
        self.assertEqual(search_tables(sut, "z", 0), "|z|3|\n")
        self.assertEqual(search_tables(sut, "y", 0), "")
        sut = table_edit(sut, "z", "whoop")
        self.assertEqual(search_tables(sut, "z", 0), "| z | whoop |\n")
