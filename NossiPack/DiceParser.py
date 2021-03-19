import re
import traceback
import warnings
from typing import List, Union, Dict

import numexpr

from NossiPack.Dice import Dice
from NossiPack.RegexRouter import (
    RegexRouter,
    DuplicateKeyException,
    PartialMatchException,
)
from NossiPack.krypta import DescriptiveError


class DiceCodeError(Exception):
    pass


class MessageReturn(Exception):
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
    lp: "DiceParser"
    rolllogs: List[Dice]
    regexrouter = RegexRouter()

    def __init__(self, defines=None, lastroll=None, lastparse=None):
        self.dbg = ""
        self.triggers = {}
        self.rights = []
        self.defines = {
            "difficulty": 6,
            "onebehaviour": 1,
            "sides": 10,
            "returnfun": "sum",
        }  # threshhold basic
        self.defines.update(defines or {})
        self.rolllogs = []  # if the last roll isnt interesting
        self.lr = lastroll or []
        self.lp = lastparse or None

    @staticmethod
    @regexrouter.register(re.compile(r"^(?P<returnfun>(-?\d+(\s*,\s*)?)+\s*@)"))
    def extract_selectors(matches):
        return matches

    @staticmethod
    @regexrouter.register(re.compile(r"(?<=[0-9 -])d\s*(?P<sides>[0-9]{1,5})"))
    def extract_sides(matches):
        if matches.get("sides", ""):
            return {"sides": int(matches["sides"])}

    @staticmethod
    @regexrouter.register(re.compile(r"(?<=[0-9-])[rR]\s*(?P<rerolls>-?\s*\d+)"))
    def extract_reroll(matches):
        if matches.get("rerolls", ""):
            return {"rerolls": int(matches["rerolls"].replace(" ", ""))}
        else:
            return {}

    @staticmethod
    @regexrouter.register(re.compile(r"(?<=[\d-])(?P<sort>s)"))
    def extract_sort(matches):
        return {"sort": bool(matches.get("sort", ""))}

    @staticmethod
    @regexrouter.register(re.compile(r"^(.*@)?(?P<amount>-?(\d+))(?!.*@)"))
    def extract_core(matches):
        return {"amount": int(matches["amount"].replace(" ", ""))}

    @staticmethod
    @regexrouter.register(
        re.compile(
            r"^([-\d,\s]*@)?(?P<literal>(\[(\s*-?\s*\d+\s*,?)+\s*])|-+)(?!\s*\d)"
        )
    )
    def extract_literal(matches):
        literal = matches["literal"].strip()
        return {
            "amount": literal
            if literal and all(x == "-" for x in literal)
            else [int(x) for x in literal[1:-1].split(",")]
        }

    @staticmethod
    @regexrouter.register(re.compile(r"(?P<end>[g=~hl])!*$"))
    def extract_base_functions(matches):
        functions = {"g": "sum", "h": "max", "l": "min", "~": "none", "=": "id"}
        return {"returnfun": functions[matches["end"]]}

    @staticmethod
    @regexrouter.register(re.compile(r"(?P<one>[ef])\s*(?P<difficulty>(\d+))!*$"))
    def extract_threshhold(matches):
        r = {"returnfun": "threshhold", "onebehaviour": "f" in matches["one"]}
        if matches["difficulty"]:
            r["difficulty"] = int(matches["difficulty"])
        return r

    @staticmethod
    @regexrouter.register(re.compile(r"(?P<explosion>!+)$"))
    def extract_explosion(matches):
        return {"explosion": len(matches["explosion"])}

    usage = "[<Selectors>@]<dice>[d<sides>[R<rerolls>][s][ef<difficulty>ghl][!!!]]"

    @classmethod
    def extract_diceparams(cls, message):
        """
        extracts the dice parameters
        :param message: the actual dicecode, after all processing
        :return: dictionary of paramaters
        """
        try:
            params = cls.regexrouter.run(message, True)
        except DuplicateKeyException as e:
            raise DescriptiveError(
                f"Interpretation Conflict: {e.args[3]} vs {e.args[4]}"
            )
        except PartialMatchException:
            raise DiceCodeError(message + " is not valid. \n" + cls.usage)
        # sanitychecks:
        if "@" in message and "@" not in params.get("returnfun", ""):
            raise DiceCodeError(f"Invalid Selectors in: {message}")
        if "amount" not in params:
            raise DiceCodeError(cls.usage)
        return params

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
        a = fullparams.get("amount", "")
        if a and isinstance(a, str) and a.count("-") == len(a):
            fullparams["amount"] = self.lr[-len(a)].r[:]
        d = Dice(**fullparams)
        self.lr = self.lr + [d]
        return d

    def resolveroll(self, roll: Union[Node, str], depth) -> Node:
        if isinstance(roll, str):
            oldroll = roll[:]
            try:
                roll, _ = self.pretrigger(roll)
                roll = Node(roll, depth)
            except MessageReturn:
                raise
            except Exception as e:
                print("pretrigger exc", e.args[0])
                roll = Node(oldroll, depth)
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

    def resonances(self, rolls=None) -> List[Dict[int, int]]:
        """
        evaluates the last rolls for resonances and returns an
        ordered list of resonances and a dict of occurences for each
        """
        if rolls is None:
            rolls = self.rolllogs
            if self.lp:
                rolls += self.lp.rolllogs
        res = [{} for _ in range(10)]
        for r in rolls:
            if "@" not in r.returnfun:
                continue
            for i in range(10):
                res[i][r.resonance(i + 1)] = res[i].get(r.resonance(i + 1), 0) + 1
                if -1 in res[i]:
                    del res[i][-1]
        return res

    def project(self, body: str) -> str:
        roll, goal, current = body, None, 0
        try:
            roll, goal = body.rsplit(" ", 2)
            goal = int(goal)
            i = 0
            log = ""
            while i < min(
                (self.triggers.get("max") or 50),
                (500 if not self.triggers.get("limitbreak", None) else 1000),
            ):
                x = self.do_roll(roll).result
                log += str(x) + " : "
                i += 1
                current += x
                log += f"{str(current)} + {x} = {current}\n"
                if current >= goal:
                    break
            self.triggers["project"] = (i, current, goal, log)
            return str(i)
        except TypeError as e:
            print(e, e.__class__, e.args, traceback.format_exc())
            raise DescriptiveError(roll + " does not have a result")  # probably
        except DescriptiveError:
            raise
        except Exception as e:
            print(e, e.__class__, e.args, traceback.format_exc())
            raise DescriptiveError(
                "project parameters: roll, current, goal [, adversity]\n"
                f"not fullfilled by {roll}, {current}, {goal}"
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
        if triggername == "project":
            return self.project(triggerbody)
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
        if triggername == "resonances":
            raise MessageReturn(
                "\n"
                + "\n".join([f"{i}: {x}" for i, x in enumerate(self.resonances()) if x])
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
                while val.count(")") > val.count("("):
                    if not roll:
                        raise DescriptiveError("unmatched ')' in " + val)
                    val: str = roll[-1] + val
                    roll = roll[:-1]
                val = val.strip()
                if val.startswith("(") and val.endswith(")"):
                    val = str(self.do_roll(val[1:-1]).result)
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
