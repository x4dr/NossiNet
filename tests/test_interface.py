import asyncio
from unittest import TestCase
from unittest.mock import Mock

from NossiInterface.Tools import splitpara, replacedefines


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
