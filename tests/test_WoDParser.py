from unittest import TestCase

from NossiPack.WoDParser import WoDParser, Node, fullparenthesis
from NossiPack.krypta import DescriptiveError


class TestWoDParser(TestCase):
    def setUp(self) -> None:
        self.p = WoDParser()

    def test_extract_diceparams(self):
        self.assertEqual(self.p.extract_diceparams("3")["amount"], 3)

        info = self.p.extract_diceparams("99d7")
        self.assertEqual(info["amount"], 99)
        self.assertEqual(info["sides"], 7)

        info = self.p.extract_diceparams("113d04f9")
        self.assertEqual(info["amount"], 113)
        self.assertEqual(info["sides"], 4)
        self.assertEqual(info["difficulty"], 9)
        self.assertEqual(info["onebehaviour"], 1)

        info = self.p.extract_diceparams("999d77777e3000!!")
        self.assertEqual(info["amount"], 999)
        self.assertEqual(info["sides"], 77777)
        self.assertEqual(info["difficulty"], 3000)
        self.assertEqual(info["onebehaviour"], 0)
        self.assertEqual(info["explosion"], 2)

    def test_do_roll(self):
        self.assertGreaterEqual(self.p.do_roll("3d10h").result, 1)
        self.assertLessEqual(self.p.do_roll("3d10h").result, 10)

    def test_return_funs(self):
        for roll, exp, ret in [
            ("6g", 27, "sum"),
            ("6h", 7, "max"),
            ("6=", 6, "id"),
            ("6l", 2, "min"),
            ("6~", None, "none"),
            ("1,2@6", 5, "1 , 2@"),
            ("6,2@6", 10, "6 , 2@"),
        ]:
            d = WoDParser({"return": "sum"}).do_roll(roll)
            d.r = [2, 3, 4, 5, 6, 7]
            self.assertEqual(ret, d.returnfun, roll)
            self.assertEqual(1 if "=" in roll else 10, d.max, roll + " sides")
            self.assertEqual(exp, d.result, roll)

    def test_parenthesis_roll(self):
        self.assertIn(self.p.do_roll("4(3) d1g").result, range(1, 70))

    def test_altrolls(self):
        self.p.do_roll("1(2g)(3(4g)g)g")
        for r in self.p.rolllogs:
            self.assertIn("==>", r.roll_v())

    def test_postmath(self):
        self.p.defines["return"] = "id"
        self.assertEqual(
            self.p.do_roll("(100d1g)-3").result, 97, "100d1g -3 should be 97",
        )

    def test_premath(self):
        self.p.defines["return"] = "id"
        self.assertEqual(
            self.p.do_roll("(5+3**2//2-3)*10+4=").result, 64, "5+3**2 should be 64",
        )

    def test_default(self):
        p = WoDParser({"sides": 17, "return": "max"})
        r = p.do_roll("9")
        self.assertIn(int(r), range(10, 9 * 17 + 1))
        r = p.do_roll("9f7")
        r.r = list(range(1, 10))
        self.assertEqual(int(r), 2)
        r = p.do_roll("9e7")
        r.r = list(range(1, 10))
        self.assertEqual(int(r), 3)

    def test_nested(self):
        self.p.do_roll("5d(5d(5d10))")

    def test_parseadd(self):
        a = ["d", "4", "3", "9", "+", "1", "g", "1", "-1"]
        self.assertEqual(Node.calc(a), "d 17 g 0")

    def test_looptriggers(self):
        r = self.p.do_roll("&loop 3 2&; 0 d1g")
        self.assertFalse(r is None)
        for x in self.p.rolllogs:
            self.assertIsNotNone(x.result)

    def test_triggerorder(self):
        self.assertEqual(self.p.do_roll("&loop 7 2&").result, None)
        self.assertNotEqual(self.p.do_roll("&loop 7 2&;6g;&loop 4 3&").result, None)

    def test_pretrigger(self):
        p = WoDParser(
            {
                "shoot": "dex fire",
                "dex": "Dexterity",
                "fire": "Firearms",
                "Dexterity": "3",
                "Firearms": "4",
                "gundamage": "4",
                "sum": "d1g",
            }
        )
        self.assertFalse(
            -1
            == p.do_roll(
                "&param difficulty& "
                "&values hit:(shoot difficulty)&  "
                "&if hit then gundamage hit -1 e6 else 0 done& "
                "sum "
            ).result
        )

    def test_resolvedefine(self):
        p = WoDParser(
            {"a": "b c D", "b": "e f", "c": "3", "D": "1", "e": "9", "f": "10"}
        )
        r = p.resolveroll("a d1g", 0)
        self.assertEqual(r.code, "23 d 1 g")

    def test_explosion(self):
        for _ in range(1000):
            if len(self.p.make_roll("5!").r) > 5:
                break
        else:
            self.assertFalse("in 1000 exploded rolls, not one exploded!")

    def test_selection_sum(self):
        for _ in range(100):
            result = self.p.do_roll("10@12d10").result
            self.assertTrue(
                result <= 10,
                "singular selector should not produce "
                f"a higher value than dice sidedness {self.p.rolllogs[-1].r}",
            )

    def test_selection_exclusivity(self):

        try:
            self.p.do_roll("10@12d10g")
        except DescriptiveError as e:
            self.assertEqual(e.args[0], "Interpretation Conflict: 10@ vs sum")
        else:
            self.assertFalse("There should have been an exception")

    def test_selection_0(self):
        for _ in range(10):
            self.assertTrue(
                self.p.do_roll("0@12d6").result == 0,
                f"0 selector should result in 0 {self.p.rolllogs[-1].r}",
            )
            self.assertTrue(
                self.p.do_roll("-2@12d6").result == 0,
                f"-2 selector should result in 0 {self.p.rolllogs[-1].r}",
            )

    def test_negative_dice(self):
        self.assertTrue(
            self.p.do_roll("-6d6g").result < 0,
            f"negative dice, negative result {self.p.rolllogs[-1].r}, {self.p.rolllogs[-1].result}",
        )

    def test_selection(self):
        r = self.p.make_roll("99,99@20s!!")
        self.assertIn(r.result, range(2, 21))

    def test_identityreturn(self):
        p = WoDParser({"return": "id"})
        r = p.do_roll("&loopsum 1 8&")
        self.assertEqual(8, r.result)

    def test_fullparenthesis(self):
        self.assertEqual(
            fullparenthesis("f______(-----((^^^^)~~~~~)---)___"),
            "-----((^^^^)~~~~~)---",
        )
        with self.assertRaises(Exception):
            fullparenthesis("_____(######")
