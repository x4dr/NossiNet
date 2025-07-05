from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from NossiPack.LocalMarkdown import LocalMarkdown
from NossiSite import helpers
from gamepack.FenCharacter import FenCharacter
from gamepack.Item import fenconvert, fendeconvert
from gamepack.MDPack import (
    search_tables,
    table_add,
    table_remove,
    table_row_edit,
)
from gamepack.Mecha import Mecha
from gamepack.WikiPage import WikiPage
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
        WikiPage(
            "unittest",
            ["character"],
            "#Layer1\n## layer2\n### layer3\ntext\n### layer 3 again\n"
            "more text\n## some more layer 2\n a|b\n--|--\nc|d\n but what about THIS\n\n### finalthird\nfinal "
            "text\n",
            [],
            {},
        ).save(WikiPage.locate("unittest"), "unittest")
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

    def test_local_markdown_hiding(self):
        print(
            LocalMarkdown.process(
                "# thing\n"
                "## !hidden subheading\n"
                "hiddentext\n"
                "and stuff \n"
                "### hidden sub subheading\n"
                "## visible again",
                "test",
            )
        )

    def test_mecha(self):

        wikipage = WikiPage.load(
            Path(__file__).parent.absolute() / "testmecha.md", False
        )
        mecha_sheet = Mecha.from_mdobj(wikipage.md(True))
        print(mecha_sheet.speeds())
        wikipage.body = mecha_sheet.to_mdobj().to_md()
        wikipage.tags = ["mech"]
        wikipage.live = False
        wikipage.save_overwrite("", "")
