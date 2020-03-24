import asyncio
from pathlib import Path
from unittest import TestCase, mock
from unittest.mock import Mock

import Data
from NossiInterface import Tools
from NossiInterface.Tools import splitpara, replacedefines, load_fen_char
from NossiPack.krypta import connect_db


class TestInterface(TestCase):
    message = None
    persist = None

    @classmethod
    def setUpClass(cls) -> None:
        def lambdaraise(x):
            raise Exception(x)

        message = Mock()
        message.author.name = "a"
        message.author.discriminator = "1"
        message.author.send = lambdaraise
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
        print(test)
        self.assertEqual(test, "c 4")

    def test_replacedef_ignore_trigger(self):
        msg = "a & a & a"
        test = asyncio.run(replacedefines(msg, self.message, self.persist))
        print(test)
        self.assertEqual(test, "c 4 & a & c 4")

    @mock.patch.object(Data, "DATABASE", "loadchara.db")
    @mock.patch.object(
        Tools,
        "wikiload",
        lambda x: ("", [], "#Werte\n##TestWert\n###Attribut\nkey|valb\n---|---\na|3"),
    )
    def test_loadchara(self):
        self.addCleanup(lambda x: Path(x).unlink(), Data.DATABASE)
        c = connect_db("Testing...")
        c.execute('INSERT INTO users VALUES ("test","__",0,"",0)')
        c.execute('INSERT INTO configs VALUES ("test","discord", "test#1234")')
        c.execute('INSERT INTO configs VALUES ("test","character_sheet", "test")')
        test = load_fen_char("test")

        self.assertEqual(test[test["a"]], "3")
