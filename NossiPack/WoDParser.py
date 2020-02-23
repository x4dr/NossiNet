import re
import traceback
from typing import List, Union

import numexpr

from NossiPack.WoDDice import WoDDice
from NossiPack.krypta import DescriptiveError


class Node(object):
    def __init__(self, roll: str, depth):
        self.dbg = ""
        self.message = roll
        self.depth = depth
        self.dependent = {}
        if self.depth > 100:
            raise DescriptiveError("recursion depth exceeded")
        self.buildroll()

    def buildroll(self):
        unparsed = self.message
        while unparsed:
            next_pos = unparsed.find("(")
            if next_pos == -1:
                break
            unparsed = unparsed[next_pos:]
            paren = fullparenthesis(unparsed)
            if paren:
                self.dependent["(" + paren + ")"] = Node(paren, self.depth + 1)
                unparsed = unparsed[len(paren) + 2:]

    def calculate(self):
        self.message = Node._calculate(self.message)

    @staticmethod
    def _calculate(message, a=0):
        parts = message.split(" ")
        i = len(parts)
        oldmessage = message
        while i > a:
            try:
                try:
                    part = "+".join(parts[a:i])
                    replace = " ".join(parts[a:i])
                    message = message.replace(replace, str(numexpr.evaluate(part)))
                except:
                    part = " ".join(parts[a:i])
                    message = message.replace(part, str(numexpr.evaluate(part)))
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
        return str(self.depth) + "|" + str(self.message)

    def __str__(self):
        return self.__repr__()


class WoDParser(object):
    rolllogs: List[WoDDice]

    def __init__(self, defines=None):
        self.dbg = ""
        self.triggers = {}
        self.rights = []
        self.defines = {"difficulty": 6, "onebehaviour": 1, "sides": 10, "return": ""}  # WoDbasic
        self.defines.update(defines or {})
        self.rolllogs = []  # if the last roll isnt interesting

    diceparse = re.compile(  # the regex matching the roll (?# ) for indentation
        r'(?# )\s*(?:(?P<selectors>(?:[0-9](?:\s*,\s*)?)*)\s*@)?'  # selector matching
        r'(?# )\s*(?P<amount>[0-9]{1,4})\s*'  # amount of dice 0-999
        r'(?# )(d *(?P<sides>[0-9]{1,5}))? *'  # sides of dice 0-99999
        r'(?# )(?:[rR]\s*(?P<rerolls>-?\d+))?'  # reroll highest/lowest dice
        r'(?#   )(?P<sort>s)?'  # sorting rolls
        r'(?# )(?P<operation>'  # what is happening with the roll
        r'(?#   )(?P<against>'  # rolling against a value for successes
        r'(?#     )(?P<onebehaviour>[ef]) *'  # e is without subtracting 1, f is with subtracting a success on a 1
        r'(?#     )(?P<difficulty>([1-9][0-9]{0,4})|([0-9]{0,4}[1-9])))|'  # difficulty 1-99999
        r'(?#   )(?P<sum>g)|'  # summing rolls up instead
        r'(?#   )(?P<maximum>h)| *'  # taking the maximum value of the roll
        r'(?#   )(?P<minimum>l))? *'  # taking the minimum value of the roll
        r'(?# )(?P<explosion>!+)? *$',  # explosion effects
    )

    usage = "[<Selectors>@]<dice>d<sides>[R<rerolls>][s][ef<difficulty>][ghl][!!!]"

    def extract_diceparams(self, message):
        info = WoDParser.diceparse.match(message)
        info = {k: v for (k, v) in info.groupdict().items() if v} if info else {}
        if info.get('amount', None) is not None:
            info['amount'] = int(info['amount'])
        else:
            if self.triggers.get("ignore", None):
                print("invalid dicecode:'" + message + "'")
                return {}
            if not message.strip():
                return None
            raise DescriptiveError("invalid dicecode:'" + message + "'\n usage: " + WoDParser.usage)
        if "@" in message and info.get("selectors") is None:
            raise DescriptiveError("Missing Selectors!")
        if info.get('sides', None) is not None:
            info['sides'] = int(info['sides'])
        if info.get("onebehaviour") == "f":
            info['onebehaviour'] = 1
            info['return'] = "threshhold"
        elif info.get("onebehaviour") == "e":
            info['onebehaviour'] = 0
            info['return'] = "threshhold"
        # would need rewrite if more than 1 desired
        if info.get('difficulty', None) is not None:
            info['difficulty'] = int(info['difficulty'])
        else:
            info.pop('difficulty', None)
        if info.pop("minimum", 0):
            info['return'] = "min"
        if info.pop("maximum", 0):
            info['return'] = "max"
        if info.pop("sum", 0):
            info['return'] = "sum"
        info['explosion'] = len(info.get('explosion', ""))

        return info

    def do_roll(self, roll, default=None, depth=0) -> WoDDice:
        if ";" in roll:
            roll = "(" + ")(".join(roll.split(";")) + ")"
        if depth == 0:  # otherwise assume roll is resolved
            self.resolveroll(roll, depth)
            return self.rolllogs[-1]
        else:
            roll = roll.strip()
            if roll:
                self.rolllogs.append(self.make_roll(roll))
            else:
                self.rolllogs.append(WoDDice.empty())

            default = self.defines.get("return", None) if not default else default
            if self.rolllogs[-1].result is None:
                if default is not None:
                    self.rolllogs[-1].returnfun = default
                else:
                    raise DescriptiveError("No return function! Should be one of \"@efghl\" for \"" + roll + "\"")
            return self.rolllogs[-1]

    def make_roll(self, roll: Union[str]) -> WoDDice:
        """Uses full and valid Rolls and returns WoDDice."""
        params = self.extract_diceparams(roll)
        if not params:  # no dice
            raise DescriptiveError("No Valid Dice in \"" + roll + "\"")
        fullparams = self.defines.copy()
        fullparams.update(params)
        return WoDDice(fullparams)

    def resolveroll(self, roll: Union[Node, str], depth):
        if isinstance(roll, str):
            roll = self.resolvedefines(roll)
            roll = self.pretrigger(roll)
            return self.resolveroll(Node(roll, depth + 1), depth + 1)
        for k in list(roll.dependent.keys()):
            toreplace = " " + str(self.resolveroll(roll.dependent[k], depth + 1)) + " "
            roll.message = roll.message.replace(k, toreplace)
            del roll.dependent[k]
        roll.calculate()
        res = self.do_roll(roll.message, depth=depth + 1).result
        return res

    def assume(self, message):
        """consumes a parenthesis"""
        if message.strip()[0] == "(":
            p = fullparenthesis(message)
            if len(message.replace(p, "").strip()[1:].strip()[1:].strip()) > 0:
                raise DescriptiveError("Leftovers after " + message + ":" + message.replace(p, ""))
            return self.do_roll(fullparenthesis(message))
        return message

    @staticmethod
    def gettrigger(message):  # returns (newmessage,triggername, trigger)
        c = message.count("&")
        if c == 0:
            return message, "", ""
        else:
            if c % 2 != 0:
                raise DescriptiveError("unmatched & in \"" + message + "\"")
                # leftover & supposed to be cleared after usage

        m = message.split("&")
        tail = "&".join(m[1:])
        if tail.startswith("if "):  # special case for nested ifs/triggers
            end = tail.rfind("else")
            close = tail[end:].find("&")

            return m[0] + " & " + tail[end + close + 1:], m[1].split(" ")[0], tail[:end + close].strip()

        # message with first trigger removed (and rest of triggers appended
        # name of first trigger
        # command of the trigger (everything after a space until the &
        newmessage = m[0] + " & " + "&".join(m[2:])
        # the remaining "&" is used in replacement operations by the triggers
        triggername = m[1].split(" ")[0]
        triggercontent = " ".join(m[1].split(" ")[1:])
        return newmessage, triggername, triggercontent

    def pretrigger(self, message):
        message, triggername, trigger = self.gettrigger(message)
        while triggername:
            print("Triggering:", triggername, "with", trigger)
            if triggername == "limitbreak":
                print("RIGHTS:", self.rights)
                if "Administrator" in self.rights:
                    self.triggers[triggername] = True
                    print("LIMITBREAK")
                else:
                    self.triggers["rightsviolation"] = True
                message = message.replace("&", "", 1)
            elif triggername in ["speed", "cutoff", "adversity", "max"]:
                if triggername in ["speed"]:  # doubles
                    x = float(trigger)
                elif triggername == "max":
                    x = min(int(trigger), 100)
                else:
                    x = int(trigger)

                self.triggers[triggername] = x
                message = message.replace("&", "", 1)
            elif triggername == "breakthrough":
                try:
                    nextpart = trigger.rfind(" ")
                    if nextpart == -1:
                        raise DescriptiveError("No parameters")
                    goal = int(self.assume(trigger[nextpart:]))
                    print("goal", goal)
                    trigger = trigger[:nextpart]
                    print("newtrigger", trigger)
                    nextpart = trigger.rfind(" ")
                    if nextpart == -1:
                        raise DescriptiveError("No second parameter")
                    current = int(self.assume(trigger[nextpart:]))
                    print("current", current)
                    nextpart = trigger.rfind(" ")
                    if nextpart == -1:
                        raise DescriptiveError("No third parameter")
                    trigger = trigger[:nextpart]
                    print("newtrigger", trigger)
                    i = 0
                    log = ""
                    adversity = self.triggers.get("adversity", 0)
                    print("limit:", self.triggers.get("limitbreak", False))
                    while i < (self.triggers.get("max") or 100) if not self.triggers.get("limitbreak", None) else 1000:
                        x = self.do_roll(trigger).result
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
                            log += str(current) + " + " + str(x) + (
                                (" - " + str(adversity)) if adversity != 0 else "") + " = "
                        current += x - adversity
                        log += str(current) + "\n"
                        if current >= goal:
                            break
                    self.triggers[triggername] = (i, current, goal, log)
                    message = message.replace("&", str(i), 1)
                except TypeError:
                    raise DescriptiveError(trigger + " does not have a result")  # probably
                except DescriptiveError:
                    raise
                except Exception as e:
                    print(e, e.__class__, e.args, traceback.format_exc())
                    raise DescriptiveError("Breakthrough Parameters: roll, current, goal\n"
                                           "Optionally &adversity x& to the left of breakthrough")

            elif triggername in ["ignore", "verbose", "suppress", "order"]:
                if "off" not in trigger:
                    self.triggers[triggername] = trigger if trigger else True
                else:
                    self.triggers[triggername] = False
                message = message.replace("&", "", 1)
            elif triggername in ["loop", "loopsum"]:
                times = int(trigger[trigger.rfind(" "):])  # everything to the right of the last space
                times = min(times, ((self.triggers.get("max") or 39)
                                    if not self.triggers.get("limitbreak", None) else 100))
                trigger = trigger[:trigger.rfind(" ")]  # roll in the left of the trigger
                loopsum = 0
                for i in range(times):
                    # looprolls.append(roll) # never to be seen again
                    loopsum += self.do_roll(trigger).result or 0
                message = message.replace("&", str(loopsum) if triggername == "loopsum" else "", 1)
            elif triggername == "values":
                try:
                    trigger = str(re.sub(r" *: *", ":", trigger))
                    for d in trigger.split(","):
                        self.defines[d.split(":")[0].strip()] = d.split(":")[1].strip()
                        message = message.replace("&", "", 1)  # no substitution to be made
                except:
                    raise DescriptiveError("Values malformed. Expected: \"&values key:value, key:value, key:value&\"")

            elif triggername == "param":
                try:
                    trigger = str(re.sub(r" +", "", trigger))
                    for d in reversed(trigger.split(",")):
                        m = message.rsplit(" ", 1)
                        message = m[0]
                        self.dbg += "using " + m[1] + " as " + d.strip() + "\n"
                        self.defines[d.strip()] = m[1]

                    message = message.replace("&", "", 1)  # no substitution to be made
                except:
                    raise DescriptiveError(
                        "Parameter malformed. Expected: \"&param key1,key2,key3&[...]value1,value2,value3\"")

            elif "if" == triggername:
                # &if a then b else c&
                ifbranch = fullparenthesis(trigger, opening="if", closing="then")
                thenbranch = fullparenthesis(trigger, opening="then", closing="else")
                elsebranch = fullparenthesis(trigger, opening="else", closing="done")
                #                ifbranch = trigger.split("then")[0][2:].strip()
                #                thenbranch = trigger.split("then")[1].strip()
                #                elsebranch = thenbranch.split("else")[1].strip()
                #                thenbranch = thenbranch.split("else")[0].strip()

                ifroller = WoDParser(self.defines.copy())
                ifroll = ifroller.do_roll(ifbranch).result
                if ifroll > 0:
                    message = message.replace("&", "(" + thenbranch.replace("$", str(ifroll), 1) + ")", 1)
                else:
                    message = message.replace("&", "(" + elsebranch.replace("$", str(-ifroll), 1) + ")", 1)
            else:
                raise DescriptiveError("unknown Trigger: " + triggername)
            message, triggername, trigger = self.gettrigger(message)

        return message

    def resolvedefines(self, message: str) -> str:
        newmessage = ""
        counter = 0
        while newmessage != message and counter < 1000:
            newmessage = message
            counter += 1
            for k, v in self.defines.items():
                message = message.replace(k, str(v))
        return message


def fullparenthesis(message, opening="(", closing=")", include=False):
    if opening not in message:
        return message
    i = -1
    lvl = 0
    begun = None
    while ((lvl > 0) or begun is None) and (i <= len(message) + 5):
        i += 1
        if (message[i:i + len(closing)] == closing) \
                and (((i == 0 or (not message[i - 1].isalnum()))
                      and not (message + " " * len(closing) * 2)[i + len(closing)].isalnum())
                     or len(closing) == 1):
            if begun is None:
                continue  # ignore closing parenthesis if not opened yet
            lvl -= 1
        if (message[i:i + len(opening)] == opening) \
                and (((i == 0 or (not message[i - 1].isalnum()))
                      and not message[i + len(opening)].isalnum())
                     or len(opening) == 1):
            lvl += 1
            if begun is None:
                begun = i
    if i > len(message) + 5:
        raise DescriptiveError("unmatched " + opening + " " + closing + ": " + message)
    result = message[begun + (len(opening) if not include else 0): i + (len(closing) if include else 0)]
    return result
