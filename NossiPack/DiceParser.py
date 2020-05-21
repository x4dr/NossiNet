import re
import traceback
import warnings
from typing import List, Union

import numexpr

from NossiPack.Dice import Dice
from NossiPack.krypta import DescriptiveError


class DiceCodeError(Exception):
    pass


class Node:
    def __init__(self, roll: str, depth):
        self.do = False
        self.code = str(roll)
        self.depth = depth
        self.dependent = {}
        if self.depth > 100:
            raise DescriptiveError("recursion depth exceeded")
        self.buildroll()

    def rebuild(self):
        self.dependent = {}
        self.buildroll()

    def buildroll(self):
        self.code = self.calc(self.code.replace("()", ""))
        unparsed = self.code
        while unparsed:
            next_pos = unparsed.find("(")
            if next_pos == -1:
                break
            unparsed = unparsed[next_pos:]
            paren = fullparenthesis(unparsed)
            if paren:
                self.dependent["(" + paren + ")"] = self.dependent.get(
                    "(" + paren + ")", []
                ) + [Node(paren, self.depth + 1)]
                self.dependent["(" + paren + ")"][-1].do = True
            unparsed = unparsed[len(paren) + 2 :]

    def calculate(self):
        self.code = Node.calc(self.code)

    @staticmethod
    def calc(message, a=0):
        special = (
            ["+", "*", "* *", ",", "-", "/", "/ /"],
            ["~", "="],
            ["h", "l", "g", "d", "e", "f"],
        )

        # ** and // are with space since they will be escaped with spaces first

        def b(m):
            o = ""

            try:
                operations, always, functions = special
                for o in operations:
                    m = re.sub(
                        r"\b" + re.escape(o) + r"\b", " " + o.replace(" ", "") + " ", m
                    )
                for al in always:
                    m = re.sub(al, " " + al + " ", m)
                for f in functions:
                    m = re.sub(
                        r"((?<=\d)|\b)" + re.escape(f) + r"((?=\d)|\b)",
                        " " + f + " ",
                        m,
                    )
            except:
                print(o + "ERROR" + m)
                raise
            return m

        def ub(m):
            while "  " in m:
                m = m.replace("  ", " ")
            return m

        if isinstance(message, str):
            message = re.sub(r" +", " ", b(message))
            parts = message.split(" ")
        elif isinstance(message, list):
            parts = message
            message = " ".join(message)
        else:
            raise TypeError("parameter was not str or list", message)
        i = len(parts)
        oldmessage = message
        while i > a:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    try:
                        part = "+".join(parts[a:i])
                        replace = " ".join(parts[a:i])
                        message = message.replace(
                            replace, str(numexpr.evaluate(part, local_dict={}))
                        )
                    except:
                        part = " ".join(parts[a:i])
                        message = message.replace(
                            part, str(numexpr.evaluate(part, local_dict={}))
                        )
                    break
                except (SyntaxError, KeyError, TypeError, AttributeError):
                    i -= 1

        message = re.sub(r" +", " ", b(message))
        if oldmessage != message:
            message = Node.calc(message)  # recursive
        else:
            if a < len(parts):  # stop recursion
                message = Node.calc(message, a + 1)
        return ub(message).strip()

    @property
    def is_leaf(self):
        return len(self.dependent.keys()) == 0

    def __repr__(self):
        return str(self.depth) + "|" + str(self.code)

    def __str__(self):
        return self.__repr__()


class DiceParser:
    rolllogs: List[Dice]

    def __init__(self, defines=None):
        self.dbg = ""
        self.triggers = {}
        self.rights = []
        self.defines = {
            "difficulty": 6,
            "onebehaviour": 1,
            "sides": 10,
            "return": "sum",
        }  # threshhold basic
        self.defines.update(defines or {})
        self.rolllogs = []  # if the last roll isnt interesting

    diceparse = re.compile(  # the regex matching the roll (?# ) for indentation
        r"(?# )\s*(?:(?P<selectors>(?:-?[0-9](?:\s*,\s*)?)*)\s*@)?"  # selector matching
        r"(?# )\s*(?P<amount>-?[0-9]{1,5})(\.[0-9]+)?\s*"  # amount of dice -99999--99999,
        # any number after the decimal point will be ignored
        r"(?# )(d *(?P<sides>[0-9]{1,5}))? *"  # sides of dice 0-99999
        r"(?# )(?:[rR]\s*(?P<rerolls>-?\s*\d+))?"  # reroll highest/lowest dice
        r"(?#   )\s*(?P<sort>s)?"  # sorting rolls
        r"(?# )\s*(?P<operation>"  # what is happening with the roll
        r"(?#   )(?P<against>"  # rolling against a value for successes
        r"(?#     )(?P<onebehaviour>[ef]) *"  # e is without subtracting 1,
        # f is with subtracting a success on a 1
        r"(?#     )(?P<difficulty>([1-9][0-9]{0,4})|([0-9]{0,4}[1-9])))|"
        # difficulty 1-99999
        r"(?#   )(?P<sum>g)|"  # summing rolls up
        r"(?#   )(?P<id>=)|"  # counting the amount instead of doing anything with the dice
        r"(?#   )(?P<none>~)|"  # returning nothing
        r"(?#   )(?P<maximum>h)| *"  # taking the maximum die
        r"(?#   )(?P<minimum>l))? *"  # taking the minimum die
        r"(?# )(?P<explosion>!+)? *$",  # explosion barrier lowered by 1 per !
    )

    usage = "[<Selectors>@]<dice>[d<sides>[R<rerolls>][s][ef<difficulty>ghl][!!!]]"

    @classmethod
    def extract_diceparams(cls, message):
        def setreturn(d, n):
            ret = d.get("return", None)
            if ret:
                raise DescriptiveError(f"Interpretation Conflict: {ret} vs {n}")
            d["return"] = n

        dice = cls.diceparse.match(message)
        dice = {k: v for (k, v) in dice.groupdict().items() if v} if dice else {}
        info = {}
        if dice.get("amount", None) is not None:
            info["amount"] = int(float(dice["amount"]))
        else:
            if not message.strip():
                return None
            raise DiceCodeError(
                "invalid dicecode:'" + message + "'\n usage: " + DiceParser.usage
            )
        if dice.get("sides", None) is not None:
            info["sides"] = int(dice["sides"])
        if dice.get("rerolls", None) is not None:
            info["rerolls"] = int(dice["rerolls"].replace(" ", ""))
        if dice.get("sort", None) is not None:
            info["sort"] = dice["sort"]

        if dice.get("selectors", None):
            setreturn(info, dice["selectors"] + "@")
        else:
            if "@" in message:
                raise DescriptiveError("Missing Selectors!")
        if dice.get("onebehaviour") == "f":
            info["onebehaviour"] = 1
            setreturn(info, "threshhold")
        elif dice.get("onebehaviour") == "e":
            info["onebehaviour"] = 0
            setreturn(info, "threshhold")
        # would need rewrite if more than 1 desired
        if dice.get("difficulty", None) is not None:
            info["difficulty"] = int(dice["difficulty"])
        if dice.get("minimum", 0):
            setreturn(info, "min")
        if dice.get("maximum", 0):
            setreturn(info, "max")
        if dice.get("sum", 0):
            setreturn(info, "sum")
        if dice.get("id", 0):
            setreturn(info, "id")
        if dice.get("none", 0):
            setreturn(info, "none")
        info["explosion"] = len(dice.get("explosion", ""))

        return info

    def do_roll(self, roll, depth=0) -> Dice:
        """Wrapper around make_roll that handles edgecases"""
        if isinstance(roll, str):
            if ";" in roll:
                roll = "(" + ")(".join(roll.split(";")) + ")"

            roll = roll.strip()
        roll = self.resolveroll(roll, depth)
        if roll.code:
            self.rolllogs.append(self.make_roll(roll.code))
        else:
            self.rolllogs.append(Dice.empty())
        return self.rolllogs[-1]

    def make_roll(self, roll: str) -> Dice:
        """Uses full and valid Rolls and returns Dice."""
        roll = roll.strip()
        params = self.extract_diceparams(roll)
        if not params:  # no dice
            return Dice.empty()
        fullparams = self.defines.copy()
        fullparams.update(params)
        return Dice(fullparams)

    def resolveroll(self, roll: Union[Node, str], depth) -> Node:
        if isinstance(roll, str):
            roll, _ = self.pretrigger(roll)
            roll = Node(roll, depth)
            res = self.resolveroll(roll, depth)
            return res
        roll.code, change = self.pretrigger(roll.code)
        if change or depth < 1:
            roll.rebuild()
            self.resolvedefines(roll)
        for k, vs in roll.dependent.items():
            for v in vs:
                if v is None:
                    toreplace = ""
                elif isinstance(v, Node):
                    if not v.do:
                        toreplace = " " + str(self.resolveroll(v, depth + 1).code) + " "
                    else:
                        toreplace = " " + str(self.do_roll(v).result or 0) + " "
                else:
                    toreplace = str(v)
                roll.code = roll.code.replace(k, toreplace, 1)
        roll.calculate()
        return roll

    def assume(self, message):
        """consumes a parenthesis"""
        if message.strip()[0] == "(":
            p = fullparenthesis(message)
            if len(message.replace(p, "").strip()[1:].strip()[1:].strip()) > 0:
                raise DescriptiveError(
                    "Leftovers after " + message + ":" + message.replace(p, "")
                )
            return self.do_roll(fullparenthesis(message))
        return message

    def breakthrough(self, body: str) -> str:
        roll, current, goal, adversity = body, None, None, None
        try:
            if body.count(" ") == 3:
                body += " "
            roll, current, goal, adversity = body.rsplit(" ", 4)
            i = 0
            log = ""
            adversity = 0 if not adversity else int(adversity)
            while i < min(
                (self.triggers.get("max") or 50),
                (500 if not self.triggers.get("limitbreak", None) else 1000),
            ):
                x = self.do_roll(roll).result
                log += str(x) + " : "
                i += 1
                while x < 0:
                    log += str(current) + "/2 = "
                    current //= 2
                    log += str(current) + "\n"
                    x += 1
                    if x < 0:
                        log += str(x) + " : "
                if x > 0:
                    log += (
                        str(current)
                        + " + "
                        + str(x)
                        + ((" - " + str(adversity)) if adversity != 0 else "")
                        + " = "
                    )
                current += x - adversity
                log += str(current) + "\n"
                if current >= goal:
                    break
            self.triggers["breakthrough"] = (i, current, goal, log)
            return str(i)
        except TypeError:
            raise DescriptiveError(roll + " does not have a result")  # probably
        except DescriptiveError:
            raise
        except Exception as e:
            print(e, e.__class__, e.args, traceback.format_exc())
            raise DescriptiveError(
                "Breakthrough Parameters: roll, current, goal [, adversity]\n"
                f"not fullfilled by {roll}, {current}, {goal}, {adversity}"
            )

    def triggerswitch(self, triggername, triggerbody):
        """
        :param triggername: name to select method by
        :param triggerbody: input to method
        :return: what to replace the trigger with, once resolved
        """
        if triggername == "limitbreak":
            print("RIGHTS:", self.rights)
            if "Administrator" in self.rights:
                self.triggers[triggername] = True
                print("LIMITBREAK")
            else:
                self.triggers["rightsviolation"] = True
            return ""

        if triggername in ["adversity", "max"]:
            if triggername == "max":
                x = min(int(triggerbody), 100)
            else:
                x = int(triggerbody)

            self.triggers[triggername] = x
            return ""
        if triggername == "breakthrough":
            return self.breakthrough(triggerbody)
        if triggername in ["ignore", "verbose"]:
            if "off" not in triggerbody:
                self.triggers[triggername] = triggerbody if triggerbody else True
            else:
                self.triggers[triggername] = False
            return ""
        if triggername in ["loop", "loopsum"]:
            roll, times = triggerbody.rsplit(" ", 1)  # split at the last space
            times = int(times)
            times = min(
                times,
                int(
                    min(
                        (self.triggers.get("max", 0) or 50),
                        (500 if not self.triggers.get("limitbreak", None) else 1000),
                    )
                ),
            )
            loopsum = sum(self.do_roll(roll).result or 0 for _ in range(times))
            return str(loopsum) if triggername == "loopsum" else ""
        if triggername == "values":
            try:
                trigger = str(re.sub(r" *: *", ":", triggerbody))
                for d in trigger.split(";"):
                    self.defines[d.split(":")[0].strip()] = d.split(":")[1].strip()
                    return ""  # defines updated
            except:
                raise DescriptiveError(
                    "Values malformed. Expected: "
                    '"&values key:value; key:value; key:value&"'
                )
        if triggername == "param":
            try:
                self.triggers["param"] = self.triggers.get(
                    "param", []
                ) + triggerbody.split(
                    " "
                )  # space delimited
                return ""  # no substitution to be made
            except:
                raise DescriptiveError(
                    'Parameter malformed. Expected: "&param key1 key2 key3& [...] '
                    'value1 value2 value3"'
                )
        if triggername == "if":
            # &if a then b else c&
            ifbranch = fullparenthesis(triggerbody, opening="", closing="then")
            thenbranch = fullparenthesis(triggerbody, opening="then", closing="else")
            elsebranch = fullparenthesis(triggerbody, opening="else", closing="done")
            ifroll = self.do_roll(ifbranch)
            if (ifroll.result or 0) > 0:
                return thenbranch.replace("$", str(ifroll.result))
            return elsebranch.replace("$", str(ifroll.result))
        raise DescriptiveError("unknown Trigger: " + triggername)

    @staticmethod
    def gettriggers(message) -> List[str]:
        c = message.count("&")
        if c == 0:
            return []
        if c % 2 != 0:  # show entire code in case unmatched & was not the last one
            raise DescriptiveError('unmatched & in "' + message + '"')
        pos = 0
        triggers = []
        while pos < len(message):
            trigger = fullparenthesis(message[pos:], "&", "&", True)
            if "&" in trigger:
                triggers.append(trigger)
            pos += message[pos:].find(trigger) + len(trigger)  # processed part
        return triggers

    def pretrigger(self, roll: str) -> (str, bool):
        triggers = self.gettriggers(roll)
        triggerreplace = []
        change = False
        for trigger in triggers:
            try:
                triggername, triggerbody = trigger.strip("& ").split(" ", 1)
            except ValueError:
                triggername, triggerbody = trigger.strip("& "), ""
            triggerreplace.append(
                (trigger, self.triggerswitch(triggername, triggerbody))
            )
            param = self.triggers.pop("param", [])  # if there is anything
            for p in reversed(param):  # right to left
                change = True
                roll, val = roll.rsplit(" ", 1)  # take rightmost thing
                self.defines[p] = val  # and write it into the defines
        for kv in triggerreplace:
            change = True
            roll = roll.replace(kv[0], kv[1], 1)
        return roll, change

    def resolvedefines(self, roll: Node, used=None) -> None:
        used = used or []
        while roll.depth < 1000:
            for k, v in self.defines.items():
                if k in used:
                    continue
                if re.match(r".*\b" + re.escape(k) + r"\b", roll.code):
                    roll.dependent[k] = []
                    for _ in range(roll.code.count(k)):
                        new = Node(v, roll.depth + 1)
                        self.resolvedefines(new, used + [k])
                        new.do = False
                        roll.dependent[k].append(new)

            else:
                break


def fullparenthesis(
    text: str, opening: str = "(", closing: str = ")", include=False
) -> str:
    """
    Finds the text within a parenthesis
    (or other bounding strings that work like parenthesis)
    :param text: the text to be searched
    :param opening: start token
    :param closing: end token
    :param include: if True, the opening and closing parts will be included
    :return: text between first opening token and first matching
    closing token or complete text on failure
    """
    if opening not in text:
        return text
    i = -1
    lvl = 0
    begun = None
    while ((lvl > 0) or begun is None) and (i <= len(text) + 5):
        i += 1
        if (
            not (opening == closing and (begun is None))
            and (text[i : i + len(closing)] == closing)
            and (
                (
                    (i == 0 or (not text[i - 1].isalnum()))
                    and not (text + " " * len(closing) * 2)[i + len(closing)].isalnum()
                )
                or len(closing) == 1
            )
        ):
            if begun is None:
                continue  # ignore closing parenthesis if not opened yet
            lvl -= 1
        elif (not opening and not i) or (  # "" matches at the start of line
            (text[i : i + len(opening)] == opening)
            and (
                (
                    (i == 0 or (not text[i - 1].isalnum()))
                    and not text[i + len(opening)].isalnum()
                )
                or len(opening) == 1
            )
        ):
            lvl += 1
            if begun is None:
                begun = i
    if i > len(text) + len(closing):
        raise DescriptiveError("unmatched '" + opening + "': '" + text + "'")
    result = text[
        begun
        + (len(opening) if not include else 0) : i
        + (len(closing) if include else 0)
    ]
    return result
