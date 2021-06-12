import asyncio
from pathlib import Path
from unittest import TestCase, mock
from unittest.mock import Mock

import Data
from NossiInterface.Tools import splitpara, replacedefines
from NossiInterface.reminder import extract_time_delta, set_user_tz
from NossiPack.krypta import connect_db
from NossiSite import wiki
from NossiSite.wiki import get_fen_char


class TestInterface(TestCase):
    message = None
    persist = None

    @classmethod
    def setUpClass(cls) -> None:
        message = Mock()
        message.author.name = "a"
        message.author.discriminator = "1"
        message.author.send = print
        cls.message = message
        cls.persist = {"a#1": {"defines": {"a": "c b", "b": "4"}}}

    def test_splitpara(self):
        teststr = "daslkdj & dadjlkj & asdjlaksjd & alskjdlask & lkja"
        spl = splitpara(teststr)
        self.assertEqual(len(spl), 6)
        self.assertEqual("".join(spl), teststr)

    def test_replacedef_simple(self):
        msg = "a"
        test = asyncio.run(replacedefines(msg, self.message, self.persist))
        self.assertEqual(test, "c 4")

    def test_replacedef_ignore_trigger(self):
        msg = "a & a & a"
        test = asyncio.run(replacedefines(msg, self.message, self.persist))
        self.assertEqual(test, "c 4 & a & c 4")

    # noinspection SqlResolve,SqlInsertValues
    @mock.patch.object(Data, "DATABASE", "loadchara.db" "")
    @mock.patch.object(
        wiki,
        "wikiload",
        lambda x: ("", [], "#Werte\n##TestWert\n###Attribut\nkey|valb\n---|---\na|3"),
    )
    @mock.patch.object(wiki, "chara_objects", {})
    def test_loadchara(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        c = connect_db("Testing...")
        c.execute('INSERT INTO users VALUES ("test","__",0,"",0)')
        c.execute('INSERT INTO configs VALUES ("test","discord", "test#1234")')
        c.execute('INSERT INTO configs VALUES ("test","character_sheet", "test")')
        test = get_fen_char("test").stat_definitions()
        self.assertEqual(test[test["a"]], "3")

    def test_timeparse(self):
        set_user_tz(0, "UTC")
        self.assertEqual(extract_time_delta("in 3:45:12 test", 0), (13512, "test"))
        self.assertEqual(extract_time_delta("in 45:12 test", 0), (162720, "test"))
        self.assertEqual(extract_time_delta("in 45m12 test", 0), (2712, "test"))
        self.assertEqual(extract_time_delta("in 1d6h test", 0), (108000, "test"))
        self.assertEqual(extract_time_delta("in 1:6:0:0 test", 0), (108000, "test"))
        self.assertEqual(extract_time_delta("3h45m12 test", 0), (13512, "test"))
        self.assertEqual(extract_time_delta("12s", 0), (12, ""))
        self.assertEqual(extract_time_delta("12", 0), (12 * 60, ""))
        self.assertLess(extract_time_delta("at 22:31:00 test", 0)[0], 24 * 60 * 60)
