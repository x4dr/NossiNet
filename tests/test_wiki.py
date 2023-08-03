from pathlib import Path
from unittest import mock

from flask import url_for
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.Item import fenconvert, fendeconvert
from gamepack.MDPack import (
    split_row,
    table,
    search_tables,
    table_add,
    table_remove,
    table_row_edit,
)
import Data
from NossiPack.WikiPage import WikiPage
from NossiSite import helpers
from NossiSite.wiki import fill_infolets
from tests.NossiTestCase import NossiTestCase


class TestViews(NossiTestCase):
    render_templates = False

    def setUp(self) -> None:
        pass  # DB created during normal usage

    @mock.patch.object(Data, "DATABASE", "index.db")
    def test_index(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        with self.register_login() as c:
            print(c.get(url_for("wiki.wiki_index")))

    def test_ewparsing(self):
        x = None
        try:
            WikiPage(
                "unittest",
                ["character"],
                "#Layer1\n## layer2\n### layer3\ntext\n### layer 3 again\n"
                "more text\n## some more layer 2\n a|b\n--|--\nc|d\n but what about THIS\n\n### finalthird\nfinal "
                "text\n",
                [],
                [],
            ).save(WikiPage.locate("unittest"), "unittest")
        except Exception as e:
            x = e
            if not isinstance(x, DescriptiveError):
                raise
        self.assertIsInstance(x, DescriptiveError)
        self.assertEqual(x.args[0], "wikiupdate failed")
        self.render_templates = False
        app = self.create_app()
        helpers.register(app)
        c = app.test_client()
        c.get("/ewsheet/test")
        del WikiPage.page_cache[WikiPage.locate("unittest")]
        WikiPage.locate("unittest.md").unlink()
        (WikiPage.wikipath() / "control").unlink()

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

    def test_infolets(self):
        self.assertRaises(
            DescriptiveError,
            lambda: WikiPage(
                title="healing",
                tags=[],
                body="# heilung\n## Aurier\n### Resonanzen\nWunde\n",
                links=[],
                meta=[],
            ).save(WikiPage.locate("healing"), "unittest"),
        )
        sut = fill_infolets("[[specific:healing:heilung:aurier:resonanzen:-]]", "test")
        self.assertIn("Wunde", sut)
        WikiPage.locate("healing.md").unlink()
        (WikiPage.wikipath() / "control").unlink()

    def test_tablesrearch(self):
        sut = "##somestuff\n|a|b|\n|-|-|\n|x|1|\ny|2\n"
        self.assertEqual(search_tables(sut, "y", 0), "y|2\n")
        sut = table_add(sut, "z", "3")
        sut = table_remove(sut, "y")
        self.assertEqual(search_tables(sut, "z", 0), "| z | 3 |\n")
        self.assertEqual(search_tables(sut, "y", 0), "")
        sut = table_row_edit(sut, "z", "whoop")
        self.assertEqual(search_tables(sut, "z", 0), "| z | whoop |\n")
