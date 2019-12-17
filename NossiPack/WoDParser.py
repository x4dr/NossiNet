import re

from flask import json

from NossiPack.WoDDice import WoDDice


class WoDParser(object):
    def __init__(self, defines=None):
        self.dbg = ""
        self.triggers = {}
        self.rights = []
        self.defines = {"difficulty": 6, "onebehaviour": 1, "sides": 10, "return": None}  # WoDbasic
        self.defines.update(defines or {})
        self.altrolls = []  # if the last roll isnt interesting

    diceparse = re.compile(  # the regex matching the roll (?# ) for indentation
        r'(?# )\s*(?:(?P<selectors>(?:[0-9](?:,\s*)?)*)\s*@)?' +  # selector matching
        r'(?# )\s*(?P<amount>[0-9]{1,4})\s*' +  # amount of dice 0-999
        r'(?# )(d *(?P<sides>[0-9]{1,5}))? *' +  # sides of dice 0-99999
        r'(?# )(?:[rR]\s*(?P<rerolls>-?\d+))?'  # reroll highest/lowest dice
        r'(?#   )(?P<sort>s)?' +  # sorting rolls
        r'(?# )(?P<operation>' +  # what is happening with the roll
        r'(?#   )(?P<against>' +  # rolling against a value for successes
        r'(?#     )(?P<onebehaviour>[ef]) *' +  # e is without subtracting 1, f is with subtracting a success on a 1
        r'(?#     )(?P<difficulty>([1-9][0-9]{0,4})|([0-9]{0,4}[1-9])))|' +  # difficulty 1-99999
        r'(?#   )(?P<sum>g)|' +  # summing rolls up instead
        r'(?#   )(?P<maximum>h)| *' +  # taking the maximum value of the roll
        r'(?#   )(?P<minimum>l))? *' +  # taking the minimum value of the roll
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
            print(message, info)
            raise Exception("invalid dicecode:'" + message + "'\n usage: "+WoDParser.usage)
        if "@" in message and info.get("selectors") is None:
            raise Exception("Missing Selectors!")
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
            info['return'] = "minimum"
        if info.pop("maximum", 0):
            info['return'] = "maximum"
        if info.pop("sum", 0):
            info['return'] = "sum"
        info['explosion'] = len(info.get('explosion', ""))

        return info

    def do_roll(self, roll):
        self.altrolls.append(self.make_roll(roll))
        if self.triggers.get("ignore", None) and self.altrolls[-1] is None:
            return None
        elif self.altrolls[-1] is None:
            raise Exception("Diceroll is missing. Probably a bug. Tell Maric about the dicecode you used.")
        else:
            return self.altrolls[-1].result

    def make_roll(self, roll: str):
        if ";" in roll:
            self.altrolls.extend([self.make_roll(m) for m in roll.split(";")])
            return None
        try:
            roll = Node(roll)
            roll = self.resolveroll(roll)
            params = self.extract_diceparams(roll)
            if not params:
                raise Exception("No Valid Parameters!", roll)
            fullparams = self.defines.copy()
            fullparams.update(params)
            v = WoDDice(fullparams)
            return v
        except Exception as e:
            print("Exception during make roll:", e.args, e.__traceback__.tb_lineno, e.__traceback__.tb_frame.__repr__())
            raise

    def resolveroll(self, roll):
        if isinstance(roll, str):
            return roll
        if roll.roll is None:
            self.expand(roll)
            return self.resolveroll(roll)
        if roll.is_leaf:
            roll.roll = self.parseadd(roll.roll)
        else:

            for i in range(len(roll.roll)):
                roll.roll[i] = self.resolveroll(  # recursive
                    roll.dependent.get(roll.roll[i],  # either resolve all the dependencies
                                       roll.roll[i]))  # if not dependent just return the string

            roll.roll = self.parseadd(roll.roll)
        paren = ""
        for p in roll.roll:
            if "(" in p:
                paren = "yes"
                break  # if there are parenthesis left process them
        if paren:
            x = " ".join(roll.roll)
            paren = self.fullparenthesis(x, include=True)
            roller = WoDParser(self.defines.copy())
            result = str(roller.do_roll(self.fullparenthesis(x)))
            self.altrolls += roller.altrolls

            x = x.replace(paren, " " + result + " ", 1).replace("  ", " ")
            roll.roll = None
            roll.message = x
            return self.resolveroll(roll)
        return " ".join(roll.roll)

    @staticmethod
    def parseadd(roll):
        roll = roll[:]  # copy
        #
        adding = None
        result = []
        if not roll:
            return result
        for current in roll:  # consume everything
            try:
                #
                adding = int(current) + (adding if adding else 0)  # and they are numbers
            except:
                #
                if current != "+":  # plus and writing things next to each other are equivalent
                    if adding is not None:  # if adding has been set
                        #
                        result.append(str(adding))
                    adding = None
                    #
                    result.append(current) if current else None  # only appends if current not ""

        if adding is not None:
            result.append(str(adding))
        #
        return result

    def expand(self, node):
        self.resolvedefine(node)

    def assume(self, message):
        if message.strip()[0] == "(":
            p = self.fullparenthesis(message)
            if len(message.replace(p, "").strip()[1:].strip()[1:].strip()) > 0:
                raise Exception("Leftovers after " + message + ":" + message.replace(p, ""))
            return self.do_roll(self.fullparenthesis(message))
        return message

    @staticmethod
    def gettrigger(message):  # returns (newmessage,triggername, trigger)
        c = message.count("&")
        if c == 0:
            return message, "", ""
        else:
            if c % 2 != 0:
                raise Exception("unmatched & in \"" + message + "\"")  # leftover & supposed to be cleared after usage

        m = message.split("&")
        tail = "&".join(m[1:])
        if tail.startswith("if "):  # special case for nested ifs/triggers
            end = tail.rfind("else")
            close = tail[end:].find("&")

            return m[0] + " & " + tail[end + close + 1:], m[1].split(" ")[0], tail[:end + close].strip()

        # message with first trigger removed (and rest of triggers appended
        # name of first trigger
        # command of the trigger (everything after a space until the &
        newmessage = m[0]
        if m[2]:
            newmessage += " & " + "&".join(m[2:])
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
                goal = int(self.assume(trigger[trigger.rfind(" "):]))
                trigger = trigger[:trigger.rfind(" ")]
                current = int(self.assume(trigger[trigger.rfind(" "):]))
                trigger = trigger[:trigger.rfind(" ")]
                i = 0
                log = ""
                adversity = self.triggers.get("adversity", 0)
                print("limit:", self.triggers.get("limitbreak", False))
                while i < (self.triggers.get("max") or 100) if not self.triggers.get("limitbreak", None) else 1000:
                    x = self.do_roll(trigger)
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
            elif triggername in ["ignore", "verbose", "suppress", "order"]:
                if "off" not in trigger:
                    self.triggers[triggername] = trigger if trigger else True
                else:
                    self.triggers[triggername] = False
                message = message.replace("&", "", 1)
            elif triggername in ["loop", "loopsum"]:
                times = int(trigger[trigger.rfind(" "):])  # everything to the right of the last space
                times = min(times, (self.triggers.get("max") or 39)
                if not self.triggers.get("limitbreak", None) else 100)
                trigger = trigger[:trigger.rfind(" ")]  # roll in the left of the trigger
                self.altrolls.append(self.make_roll(trigger))  # first one is constructed
                for i in range(times - 1):  # need 1 less
                    self.altrolls.append(self.altrolls[-1].another())  # rest are rerolls
                    loopsum += self.altrolls[-1].result
                message = message.replace("&", ("&ignore&" if (triggername == "loop") else str(loopsum)),
                                          1)  # its ok for loops to not have dice outside the trigger
            elif triggername == "values":
                try:
                    trigger = str(re.sub(r" *: *", ":", trigger))
                    for d in trigger.split(","):
                        self.defines[d.split(":")[0].strip()] = d.split(":")[1].strip()
                        message = message.replace("&", "", 1)  # no substitution to be made
                except:
                    raise Exception("Values malformed. Expected: \"&values key:value, key:value, key:value&\"")

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
                    raise Exception(
                        "Parameter malformed. Expected: \"&param key1,key2,key3&[...]value1,value2,value3\"")

            elif "if" == triggername:
                # &if a then b else c&
                ifbranch = self.fullparenthesis(trigger, opening="if", closing="then")
                thenbranch = self.fullparenthesis(trigger, opening="then", closing="else")
                elsebranch = self.fullparenthesis(trigger, opening="else", closing="done")
                #                ifbranch = trigger.split("then")[0][2:].strip()
                #                thenbranch = trigger.split("then")[1].strip()
                #                elsebranch = thenbranch.split("else")[1].strip()
                #                thenbranch = thenbranch.split("else")[0].strip()

                ifroller = WoDParser(self.defines.copy())
                ifroll = ifroller.do_roll(ifbranch)

                if ifroll > 0:
                    message = message.replace("&", "(" + thenbranch.replace("$", str(ifroll), 1) + ")", 1)
                else:
                    message = message.replace("&", "(" + elsebranch.replace("$", str(-ifroll), 1) + ")", 1)
            else:
                raise Exception("unknown Trigger: " + triggername)
            message, triggername, trigger = self.gettrigger(message)

        return message

    def resolvedefine(self, node):
        # makes node.roll into array
        if (not node.roll) or isinstance(node.roll, str):
            node.message = self.pretrigger(node.message)
            node.roll = node.message.replace('_', ' ').replace('  ', ' ').split(' ')  # get rid of _ and split
            node.roll = [n for n in node.roll if n]  # deletes ''

        for b in node.roll:
            if b in self.defines.keys():
                node.dependent[b] = Node(self.defines.get(b), node.depth + 1)

                self.resolvedefine(node.dependent[b])  # depth first

    @staticmethod
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
            raise Exception("unmatched " + opening + " " + closing + ": " + message)
        result = message[begun + (len(opening) if not include else 0): i + (len(closing) if include else 0)]
        return result

    @staticmethod
    def shorthand():
        with open('./NossiSite/locales/EN.json') as json_data:
            return json.load(json_data)['shorthand']


class Node(object):
    def __init__(self, roll, depth=0):
        self.dbg = ""
        self.message = roll
        self.roll = None
        self.special = None
        self.depth = depth
        self.dependent = {}
        if self.depth > 100:
            raise Exception("recursion depth exceeded")

    @property
    def is_leaf(self):
        return len(self.dependent.keys()) == 0
