import asyncio
from pathlib import Path
from unittest import TestCase, mock
from unittest.mock import Mock

import Data
from NossiInterface.Tools import splitpara, replacedefines
from NossiPack.krypta import connect_db
from NossiSite import wiki
from NossiSite.webhook import _get_travis_public_keys
from NossiSite.wiki import get_fen_char


class TestInterface(TestCase):
    message = None
    persist = None

    @classmethod
    def setUpClass(cls) -> None:
        message = Mock()
        message.author.name = "a"
        message.author.discriminator = "1"
        message.author.send = print()
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

    @mock.patch.object(Data, "DATABASE", "loadchara.db")
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

    def test_get_travis_public_keys(self):
        self.assertEqual(
            str(_get_travis_public_keys()),
            r"['-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnQU2j9lnR"
            r"tyuW36arNOc\ndzCzyKVirLUi3/aLh6UfnTVXzTnx8eHUnBn1ZeQl7Eh3J3qqdbIKl6npS27ONzCy\n3PIcf"
            r"jpLPaVyGagIL8c8XgDEvB45AesC0osVP5gkXQkPUM3B2rrUmp1AZzG+Fuo0\nSAeNnS71gN63U3brL9fN/MTC"
            r"XJJ6TvMt3GrcJUq5uq56qNeJTsiowK6eiiWFUSfh\ne1qapOdMFmcEs9J/R1XQ/scxbAnLcWfl8lqH/MjMdCMe0"
            r"j3X2ZYMTqOHsb3cQGSS\ndMPwZGeLWV+OaxjJ7TrJ+riqMANOgqCBGpvWUnUfo046ACOx7p6u4fFc3aRiuqYK\nVQI"
            r"DAQAB\n-----END PUBLIC KEY-----', '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAO"
            r"CAQ8AMIIBCgKCAQEAvtjdLkS+FP+0fPC09j25\ny/PiuYDDivIT86COVedvlElk99BBYTrqNaJybxjXbIZ1Q6xFNhO"
            r"Y+iTcBr4E1zJu\ntizF3Xi0V9tOuP/M8Wn4Y/1lCWbQKlWrNQuqNBmhovF4K3mDCYswVbpgTmp+JQYu\nBm9QMdieZ"
            r"MNry5s6aiMA9aSjDlNyedvSENYo18F+NYg1J0C0JiPYTxheCb4optr1\n5xNzFKhAkuGs4XTOA5C7Q06GCKtDNf44s"
            r"/CVE30KODUxBi0MCKaxiXw/yy55zxX2\n/YdGphIyQiA5iO1986ZmZCLLW8udz9uhW5jUr3Jlp9LbmphAC61bVSf4ou2Ys"
            r"JaN\n0QIDAQAB\n-----END PUBLIC KEY-----']",
        )
