from unittest import TestCase
from NossiPack.WoDParser import WoDParser, Node


class TestWoDParser(TestCase):
    def test_extract_diceparams(self):
        p = WoDParser({})
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
        p = WoDParser({})

        self.assertGreaterEqual(p.do_roll("3d10h"), 1)
        self.assertLessEqual(p.do_roll("3d10h"), 10)
        print("altrolls[-1].roll_vv():\n" + p.altrolls[-1].roll_vv())
        print("altrolls[-1].roll_v():\n" + p.altrolls[-1].roll_v())
        print("do_roll:", p.do_roll("3d10h"))

    def test_parenthesis_roll(self):
        p = WoDParser({})
        print("parenthesisroll:", p.do_roll("4(3)"))

    def test_resolveroll(self):
        node = Node("a d1g")
        p = WoDParser({"a": "b c d", "b": "e f", "c": "3", "d": "1", "e": "9", "f": "10"})
        p.resolvedefine(node)
        self.assertEqual(p.resolveroll(node), "23 d1g")

    def test_altrolls(self):
        p = WoDParser({})
        print("parenthesisroll:", p.do_roll("4(3)(9(3))"))
        for r in p.altrolls[:-1]:
            print(r.roll_v())

    def test_parseadd(self):
        p = WoDParser({})
        a = ["d", "4", "3", "9", "+", "1", "g", "1", "-1"]
        self.assertEqual(p.parseadd(a), ['d', '17', 'g', '0'])

    def test_looptriggers(self):
        p = WoDParser({})
        r = p.make_roll("&loop 3 2&; 3")
        for x in p.altrolls:
            if x is not None:
                print(x.result)
            else:
                print("roll none")

    def test_triggerorder(self):
        p = WoDParser({})
        p.make_roll("&loop 7 2&;6;&loop 4 3&")



    def test_pretrigger(self):
        print("start pretrigger")
        p = WoDParser({"shoot": "dex fire", "dex": "Dexterity", "fire": "Firearms", "Dexterity": "3", "Firearms": "4",
                       "gundamage": "4", "sum": "d1g"})
        print("firstshoot")
        print(p.do_roll("5 sum"))
        print("firstshootdone")
        r = p.do_roll("&param difficulty& &if shoot difficulty then gundamage $ -1 e6 else 0 done& sum ")
        print(r, "\nend pretrigger")

    def test_resolvedefine(self):
        p = WoDParser({"a": "b c d", "b": "e f", "c": "3", "d": "1", "e": "9", "f": "10"})
        r = Node("a d1g")
        p.resolvedefine(r)
        self.assertEqual(
            [[y.roll for y in x] for x in [list(y.values()) for y in [x.dependent for x in r.dependent.values()]]],
            [[['e', 'f'], ['3'], ['1']]])

    def test_fullparenthesis(self):
        p = WoDParser({})
        self.assertEqual(p.fullparenthesis("f______(-----((^^^^)~~~~~)---)___"), "-----((^^^^)~~~~~)---")

        with self.assertRaises(Exception):
            print(p.fullparenthesis("_____(######"))
