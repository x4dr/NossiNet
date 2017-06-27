from unittest import TestCase
from NossiPack.WoDParserV2Test import WoDParser, Node


class TestWoDParser(TestCase):
    def test_nv(self):
        print(None)

    def test_extract_diceparams(self):
        p = WoDParser({}, "")
        self.assertEqual(p.extract_diceparams("3")['amount'], 3)

        info = p.extract_diceparams("99d7")
        self.assertEqual(info['amount'], 99)
        self.assertEqual(info['sidedness'], 7)

        info = p.extract_diceparams("113d04f9")
        self.assertEqual(info['amount'], 113)
        self.assertEqual(info['sidedness'], 4)
        self.assertEqual(info['difficulty'], 9)
        self.assertEqual(info['onebehaviour'], 1)

        info = p.extract_diceparams("999d77777e3000!!")
        self.assertEqual(info['amount'], 999)
        self.assertEqual(info['sidedness'], 77777)
        self.assertEqual(info['difficulty'], 3000)
        self.assertEqual(info['onebehaviour'], 0)
        self.assertEqual(info['explosion'], 2)

    def test_do_roll(self):
        p = WoDParser({}, "")
        self.assertGreaterEqual(p.do_roll("3d10h"), 1)
        self.assertLessEqual(p.do_roll("3d10h"), 10)
        print(p.altrolls[-1].roll_vv())
        print(p.do_roll("3d10h"), 0)

    def test_resolveroll(self):
        node = Node("a d1g")
        p = WoDParser({"a": "b c d", "b": "e f", "c": "3", "d": "1", "e": "9", "f": "10"}, "")
        p.resolvedefine(node)
        self.assertEqual(p.resolveroll(node),"23 d1g")

    def test_parseadd(self):
        p = WoDParser({}, "")
        a = ["d","4","3","9","+","1","g","1","-1"]
        self.assertEqual(p.parseadd(a), ['d', '17', 'g', '0'])

    def test_pretrigger(self):
        p = WoDParser({}, "")
        p.pretrigger("if;param;")
        self.fail()

    def test_resolvedefine(self):
        p = WoDParser({"a": "b c d", "b": "e f", "c": "3", "d": "1", "e": "9", "f": "10"}, "a d1g")
        p.resolvedefine(p.roll)
        self.assertEqual([[y.roll for y in x] for x in [list(y.values()) for y in [x.dependent for x in p.roll.dependent.values()]]],
                         [[['e', 'f'], ['3'], ['1']]])


    def test_fullparenthesis(self):
        p = WoDParser({}, "")
        self.assertEqual(p.fullparenthesis("f______(-----((^^^^)~~~~~)---)___"), "-----((^^^^)~~~~~)---")

        with self.assertRaises(Exception):
            p.fullparenthesis("_____(######")
