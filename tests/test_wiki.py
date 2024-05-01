from pathlib import Path
from unittest import mock

from flask import url_for
from gamepack.Dice import DescriptiveError
from gamepack.FenCharacter import FenCharacter
from gamepack.Item import fenconvert, fendeconvert
from gamepack.MDPack import (
    search_tables,
    table_add,
    table_remove,
    table_row_edit,
)
from gamepack.WikiPage import WikiPage

import Data
from NossiPack.LocalMarkdown import LocalMarkdown
from NossiSite import helpers
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
        WikiPage.locate("unittest.md").unlink(True)
        (WikiPage.wikipath() / "control").unlink(True)

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

    def test_tablesrearch(self):
        sut = "##somestuff\n|a|b|\n|-|-|\n|x|1|\ny|2\n"
        self.assertEqual(search_tables(sut, "y", 0), "y|2\n")
        sut = table_add(sut, "z", "3")
        sut = table_remove(sut, "y")
        self.assertEqual(search_tables(sut, "z", 0), "| z | 3 |\n")
        self.assertEqual(search_tables(sut, "y", 0), "")
        sut = table_row_edit(sut, "z", "whoop")
        self.assertEqual(search_tables(sut, "z", 0), "| z | whoop |\n")

    def test_local_markdown_transclusion(self):
        sut = WikiPage(
            title="healing",
            tags=[],
            body="# heilung\n## Aurier\n### Resonanzen\nWunde\n",
            links=[],
            meta=[],
        )
        self.assertRaises(
            DescriptiveError, lambda: sut.save(WikiPage.locate("healing"), "unittest")
        )
        x = LocalMarkdown.pre_process("![](healing#resonanzen)")[0]
        self.assertEqual(x, "Wunde\n")
        x = LocalMarkdown.pre_process("![healing#resonanzen]")[0]
        self.assertIn("Wunde", x)
        self.assertNotIn("!", x)
        x = LocalMarkdown.pre_process("![healing]")[0]
        self.assertIn("heilung", x)
        self.assertNotIn("!", x)
        x = LocalMarkdown.pre_process("![healing#resonanzen](test)")[0]  # wrong order
        self.assertEqual("![healing#resonanzen](test)", x)
        x = LocalMarkdown.pre_process("![test](healing#resonanzen)")[0]
        self.assertIn("Wunde", x)
        self.assertNotIn("!", x)
        self.assertNotIn("esonanzen", x)
        self.assertIn("test", x)
        x = LocalMarkdown.pre_process("![test](healing)")[0]
        self.assertEqual(len(x.split("\n")), 5)
        self.assertNotIn("!", x)
        WikiPage.locate("healing").unlink(True)
        (WikiPage.wikipath() / "control").unlink(True)

    def test_local_markdown_fold_transclusion(self):
        sut = WikiPage(
            title="healing",
            tags=[],
            body="# heilung\n## Aurier\n### Resonanzen\nWunde\n",
            links=[],
            meta=[],
        )
        self.assertRaises(
            DescriptiveError, lambda: sut.save(WikiPage.locate("healing"), "unittest")
        )
        x = LocalMarkdown.pre_process("![[]](healing#resonanzen)")[0]  # empty heading
        self.assertEqual(x, "#!\nWunde\n")
        x = LocalMarkdown.pre_process("![[healing#resonanzen]]")[
            0
        ]  # shortform with path
        self.assertIn("Wunde", x)
        self.assertIn("###!", x)
        x = LocalMarkdown.pre_process("![[healing]]")[0]  # shortform without path
        self.assertIn("#! heilung", x)
        x = LocalMarkdown.pre_process("![[healing#resonanzen]](test)")[0]  # wrong order
        self.assertEqual(x, "![[healing#resonanzen]](test)")
        x = LocalMarkdown.pre_process("![[test]](healing#resonanzen)")[0]
        # heading with path
        self.assertIn("Wunde", x)
        self.assertIn("###! test", x)
        x = LocalMarkdown.pre_process("![[test]](healing)")[0]  # heading without path
        self.assertEqual(len(x.split("\n")), 5)
        self.assertIn("#! test", x)
        WikiPage.locate("healing").unlink(True)
        (WikiPage.wikipath() / "control").unlink(True)

    def test_local_markdown_hiding(self):
        print(
            LocalMarkdown.process(
                "# thing\n"
                "## !hidden subheading\n"
                "hiddentext\n"
                "and stuff \n"
                "### hidden sub subheading\n"
                "## visible again"
            )
        )
