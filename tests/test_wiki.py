from pathlib import Path
from unittest import mock

from flask import url_for

import Data
from NossiPack.LocalMarkdown import LocalMarkdown
from gamepack.FenCharacter import FenCharacter
from gamepack.Item import fenconvert, fendeconvert
from gamepack.MDPack import search_tables, table_add, table_remove, table_row_edit
from gamepack.WikiPage import WikiPage
from gamepack.endworld import MovementSystem
from gamepack.endworld.Mecha import Mecha
from tests.NossiTestCase import NossiTestCase


class TestWiki(NossiTestCase):
    render_templates = False

    def setUp(self):
        super().setUp()  # DB and app already initialized

    @mock.patch.object(Data, "DATABASE", "index.db")
    def test_index(self):
        try:
            c = self.register_login()
            with self.app.app_context():
                rv = c.get(url_for("wiki.wiki_index"))
            self.assertEqual(rv.status_code, 200)
        finally:
            self.delete("index.db")

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
        processed = LocalMarkdown().process(
            "# thing\n"
            "## !hidden subheading\n"
            "hiddentext\n"
            "and stuff \n"
            "### hidden sub subheading\n"
            "## visible again",
            "test",
        )
        self.assertIn('<h2 id="visible-again">visible again</h2>', processed)

    def test_mecha(self):
        WikiPage._wikipath = Path(__file__).parent  # point wiki to test folder
        wikipage = WikiPage.load(Path(__file__).parent / "testmecha.md", False)
        mecha_sheet = Mecha.from_mdobj(wikipage.md(True))
        self.assertIsNotNone(mecha_sheet.total_mass)
        self.assertTrue(hasattr(mecha_sheet, "speeds"))

        # update page and save
        wikipage.body = mecha_sheet.to_mdobj().to_md()
        wikipage.tags = ["mech"]
        wikipage.live = False
        wikipage.save_overwrite("", "")

    def test_speed(self):
        WikiPage._wikipath = Path("~/wiki").expanduser()
        wikipage = WikiPage.load(Path("endworld/mecha/systems/movement.md"))
        systems = wikipage.md().children["Movement Systems"].tables[0]
        for i in range(2, len(systems.rows)):
            if systems.rows[i][2].strip() == "":
                continue
            data = systems.row_as_dict(i)
            m = MovementSystem(data["Type"], data)
            m.amount = 1
            # test some speeds calculation
            self.assertIsNotNone(m.speeds(5))
