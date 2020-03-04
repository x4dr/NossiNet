import re
import traceback
from typing import List, Union

import numexpr

from NossiPack.WoDDice import WoDDice
from NossiPack.krypta import DescriptiveError


class Node(object):
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
        self.code = self.code.replace("()", "")
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
        self.code = Node._calculate(self.code)

    @staticmethod
    def _calculate(message, a=0):
        if isinstance(message, str):
            parts = message.split(" ")
        elif isinstance(message, list):
            parts = message
            message = " ".join(message)
        else:
            raise TypeError("parameter was not str or list", message)
        i = len(parts)
        oldmessage = message
        while i > a:
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
            except:
                i -= 1

        if oldmessage != message:
            message = Node._calculate(message)  # recursive
        else:
            if a < len(parts):  # stop recursion
                message = Node._calculate(message, a + 1)
        return message

    @property
    def is_leaf(self):
        return len(self.dependent.keys()) == 0

    def __repr__(self):
        return str(self.depth) + "|" + str(self.code)

    def __str__(self):
        return self.__repr__()


class WoDParser(object):
    rolllogs: List[WoDDice]

    def __init__(self, defines=None):
        self.dbg = ""
        self.triggers = {}
        self.rights = []
        self.defines = {
            "difficulty": 6,
            "onebehaviour": 1,
            "sides": 10,
            "return": "sum",
        }  # WoDbasic
        self.defines.update(defines or {})
        self.rolllogs = []  # if the last roll isnt interesting

    diceparse = re.compile(  # the regex matching the roll (?# ) for indentation
        r"(?# )\s*(?:(?P<selectors>(?:[0-9](?:\s*,\s*)?)*)\s*@)?"  # selector matching
        r"(?# )\s*(?P<amount>[0-9]{1,4})\s*"  # amount of dice 0-999
        r"(?# )(d *(?P<sides>[0-9]{1,5}))? *"  # sides of dice 0-99999
        r"(?# )(?:[rR]\s*(?P<rerolls>-?\d+))?"  # reroll highest/lowest dice
        r"(?#   )(?P<sort>s)?"  # sorting rolls
        r"(?# )(?P<operation>"  # what is happening with the roll
        r"(?#   )(?P<against>"  # rolling against a value for successes
        r"(?#     )(?P<onebehaviour>[ef]) *"  # e is without subtracting 1,
        # f is with subtracting a success on a 1
        r"(?#     )(?P<difficulty>([1-9][0-9]{0,4})|([0-9]{0,4}[1-9])))|"
        # difficulty 1-99999
        r"(?#   )(?P<sum>g)|"  # summing rolls up instead
        r"(?#   )(?P<maximum>h)| *"  # taking the maximum value of the roll
        r"(?#   )(?P<minimum>l))? *"  # taking the minimum value of the roll
        r"(?# )(?P<explosion>!+)? *$",  # explosion effects
    )

    usage = "[<Selectors>@]<dice>d<sides>[R<rerolls>][s][ef<difficulty>][ghl][!!!]"

    def extract_diceparams(self, message):
        info = WoDParser.diceparse.match(message)
        info = {k: v for (k, v) in info.groupdict().items() if v} if info else {}
        if info.get("amount", None) is not None:
            info["amount"] = int(info["amount"])
        else:
            if self.triggers.get("ignore", None):
                print("invalid dicecode:'" + message + "'")
                return {}
            if not message.strip():
                return None
            raise DescriptiveError(
                "invalid dicecode:'" + message + "'\n usage: " + WoDParser.usage
            )
        if "@" in message and info.get("selectors") is None:
            raise DescriptiveError("Missing Selectors!")
        if info.get("sides", None) is not None:
            info["sides"] = int(info["sides"])
        if info.get("onebehaviour") == "f":
            info["onebehaviour"] = 1
            info["return"] = "threshhold"
        elif info.get("onebehaviour") == "e":
            info["onebehaviour"] = 0
            info["return"] = "threshhold"
        # would need rewrite if more than 1 desired
        if info.get("difficulty", None) is not None:
            info["difficulty"] = int(info["difficulty"])
        else:
            info.pop("difficulty", None)
        if info.pop("minimum", 0):
            info["return"] = "min"
        if info.pop("maximum", 0):
            info["return"] = "max"
        if info.pop("sum", 0):
            info["return"] = "sum"
        info["explosion"] = len(info.get("explosion", ""))

        return info

    def do_roll(self, roll, default=None) -> WoDDice:
        """Wrapper around make_roll that handles edgecases"""
        if isinstance(roll, str):
            if ";" in roll:
                roll = "(" + ")(".join(roll.split(";")) + ")"

            roll = roll.strip()
        roll = self.resolveroll(roll, 0)
        if roll.code:
            self.rolllogs.append(self.make_roll(roll.code))
        else:
            self.rolllogs.append(WoDDice.empty())

        default = self.defines.get("return", None) if not default else default
        if self.rolllogs[-1].result is None:
            if default is not None:
                self.rolllogs[-1].returnfun = default
            else:
                raise DescriptiveError(
                    'No return function! Should be one of "@efghl" for "'
                    + str(roll)
                    + '"'
                )
        return self.rolllogs[-1]

    def make_roll(self, roll: Union[str]) -> WoDDice:
        """Uses full and valid Rolls and returns WoDDice."""
        params = self.extract_diceparams(roll)
        if not params:  # no dice
            raise DescriptiveError('No Valid Dice in "' + roll + '"')
        fullparams = self.defines.copy()
        fullparams.update(params)
        return WoDDice(fullparams)

    def resolveroll(self, roll: Union[Node, str], depth) -> Node:
        if isinstance(roll, str):
            roll = Node(roll, 0)
            self.pretrigger(roll)
            res = self.resolveroll(roll, 0)
            return res
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
        roll = body
        try:
            roll, current, goal = body.rsplit(" ", 3)
            i = 0
            log = ""
            adversity = self.triggers.get("adversity", 0)
            while (
                i < (self.triggers.get("max") or 100)
                if not self.triggers.get("limitbreak", None)
                else 1000
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
                "Breakthrough Parameters: roll, current, goal\n"
                "Optionally &adversity x& to the left of breakthrough"
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

        elif triggername in ["speed", "cutoff", "adversity", "max"]:
            if triggername in ["speed"]:  # doubles
                x = float(triggerbody)
            elif triggername == "max":
                x = min(int(triggerbody), 100)
            else:
                x = int(triggerbody)

            self.triggers[triggername] = x
            return ""
        elif triggername == "breakthrough":
            return self.breakthrough(triggerbody)
        elif triggername in ["ignore", "verbose", "suppress", "order"]:
            if "off" not in triggerbody:
                self.triggers[triggername] = triggerbody if triggerbody else True
            else:
                self.triggers[triggername] = False
            return ""
        elif triggername in ["loop", "loopsum"]:
            roll, times = triggerbody.rsplit(" ", 1)  # split at the last space
            times = int(times)
            times = min(
                times,
                int(
                    (self.triggers.get("max", 0) or 100)
                    if not self.triggers.get("limitbreak", None)
                    else 500
                ),
            )
            loopsum = 0
            for i in range(times):
                loopsum += self.do_roll(roll).result or 0
            return str(loopsum) if triggername == "loopsum" else ""
        elif triggername == "values":
            try:
                trigger = str(re.sub(r" *: *", ":", triggerbody))
                for d in trigger.split(","):
                    self.defines[d.split(":")[0].strip()] = d.split(":")[1].strip()
                    return ""  # defines updated
            except:
                raise DescriptiveError(
                    "Values malformed. Expected: "
                    '"&values key:value, key:value, key:value&"'
                )
        elif triggername == "param":
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
        elif "if" == triggername:
            # &if a then b else c&
            ifbranch = fullparenthesis(triggerbody, opening="", closing="then")
            thenbranch = fullparenthesis(triggerbody, opening="then", closing="else")
            elsebranch = fullparenthesis(triggerbody, opening="else", closing="done")
            if (self.do_roll(ifbranch).result or 0) > 0:
                return thenbranch
            else:
                return elsebranch
        else:
            raise DescriptiveError("unknown Trigger: " + triggername)

    @staticmethod
    def gettriggers(message) -> List[str]:
        c = message.count("&")
        if c == 0:
            return []
        else:
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

    def pretrigger(self, roll: Node) -> None:
        triggers = self.gettriggers(roll.code)
        triggerreplace = []
        for trigger in triggers:
            triggername, triggerbody = trigger.strip("& ").split(" ", 1)
            triggerreplace.append(
                (trigger, self.triggerswitch(triggername, triggerbody))
            )
            param = self.triggers.pop("param", [])  # if there is anything
            for p in reversed(param):  # right to left
                roll.code, val = roll.code.rsplit(" ", 1)  # take rightmost thing
                self.defines[p] = val  # and write it into the defines
        for kv in triggerreplace:
            roll.code = roll.code.replace(kv[0], kv[1], 1)
        if triggerreplace:
            roll.rebuild()

    def resolvedefines(self, roll: Node) -> None:
        while roll.depth < 1000:
            for k, v in self.defines.items():
                if k in roll.code:
                    roll.dependent[k] = []
                    for _ in range(roll.code.count(k)):
                        roll.dependent[k].append(Node(v, roll.depth + 1))
                        self.resolvedefines(roll.dependent[k][-1])
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
