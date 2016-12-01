import re, time, json

from NossiPack import *


class WoDParser(object):
    def __init__(self, defines):
        self.dbg = ""
        self.triggers = []
        self.defines = defines
        self.altrolls = []  # if the last roll isnt interesting

    def parseadd(self, message, trace=False):
        message = message.replace("#", " ")
        message = message.replace("+", " ")
        message = message.strip()
        action = True
        message = re.sub(r'- *([0-9])', ' -\g<1>', message)

        adder = re.compile(r'((\b-?[0-9]+) +(-?[0-9]+\b))')  # [-]XX + [-]XX to match numbers to add
        if trace:
            if len(message.strip()) > 2:
                self.dbg += "adding: " + message
        while action:
            a = adder.findall(message)
            try:
                a = a[0]
                message = message.replace(a[0], str(int(a[1]) + int(a[2])))
            except:
                action = False
        if trace:
            self.dbg += " = " + message + "\n"
        return message

    def resolvedefine(self, message, reclvl=0, trace=False):
        bits = message.replace('_', ' ').split(' ')  # splits into bits that should be looked up
        bits = [b for b in bits if b != ""]  # clean empty elements
        replace = [self.defines.get(b, None) for b in bits]

        for i in range(len(bits)):
            if replace[i]:
                message = message.replace(bits[i], str(replace[i]))
        message = re.sub(r'0 *_', "-1", message)
        message = re.sub(r'([0-9]+ *)_', "\g<1>", message)
        return message

    @staticmethod
    def validate_roll(message):
        dicecode = re.compile(r' *[0-9]{1,3} *(d *-?[0-9]{1,5}) *(([efg] *-?[0-9]{1,5})|(g)) *!* *$')
        match = dicecode.match(message)
        if match:
            return 4
        else:
            dicecode = re.compile(r' *[0-9]{1,3} *(d *-?[0-9]{1,5}) *!* *$')
            match = dicecode.match(message)
            if match:
                return 3
            else:
                dicecode = re.compile(r' *[0-9]{1,3} *(([efg] *-?[0-9]{1,5})|(g)) *!* *$')
                match = dicecode.match(message)
                if match:
                    return 2
                else:
                    dicecode = re.compile(r' *[0-9]{1,3} *!* *$')
                    match = dicecode.match(message)
                    if match:
                        return 1
                    else:
                        return 0

    @staticmethod
    def fullparenthesis(message):
        i = message.find("(")
        lvl = 1
        try:
            while lvl > 0:
                i += 1
                if message[i] == ")":
                    lvl -= 1
                if message[i] == "(":
                    lvl += 1
            return message[message.find("(") + 1:i]
        except:
            raise Exception("unmatched bracked: " + message)

    def pretrigger(self, message):
        if "§param_" in message:  # need to be last
            triggers = message[message.find("§param_"):]
            message = message[:message.find("§param_")]
            try:
                keys = triggers.split(":")[0]
                values = triggers.split(":")[1]
            except:
                raise Exception("Parameter malformed. Missing ':'? ")
            keys = [x for x in keys.replace("§param_", " ").replace("  ", " ").split(" ") if x]  # purge empty elements
            values = [x for x in values.split(" ") if x]
            i = 0
            for key in keys:
                try:
                    self.defines[key] = values[i]
                    self.dbg += ("using: " + values[i] + " as " + key + ".\n")
                except:
                    raise Exception("No value for parameter: " + key)
                    # self.defines[key] = "0" # default to 0; alternative
                i += 1
            message = self.preparse(message)  # preparse again

        if "§if_" in message:
            try:
                cond = message[message.find("§if_"):]
                cond = self.fullparenthesis(cond)
                trigger = (message[message.find("§if_"):].replace("§if_", "", 1).strip()).replace("(" + cond + ")", "",
                                                                                                  1)
                trigger = self.fullparenthesis(trigger)
                othertrigger = self.fullparenthesis(message[message.find(trigger) + len(trigger):])
                roll = self.diceparser(cond)
                res = roll.roll_nv()
                self.altrolls.append(roll)
                self.dbg = self.dbg[:-3] + ", for " + str(res) + " successes. \n"
                if res > 0:
                    message = re.sub(r'§if_.*' + re.escape(trigger) + "\)(\(" + re.escape(othertrigger) + "\))?",
                                     "(" + trigger.replace("$", str(res)) + ")",
                                     message)
                else:
                    message = re.sub(r'§if_.*' + re.escape(trigger) + "\)(\(" + re.escape(othertrigger) + "\))?",
                                     "(" + othertrigger.replace("$", str(res)) + ")",
                                     message)
            except:
                raise Exception("Malformed if:" + message)
        return message

    def preparse(self, message):
        if message and message[0] == "#":
            message = message[1:]

        for k in self.defines.keys():  # longer ones first
            if not k.strip():  # fix for the dumbasses who have empty keys in their defines
                continue
            if not str(self.defines[k]).strip():
                continue
            finder = re.compile(r'\b' + k + r'_?\b')
            matches = finder.findall(message)
            for m in matches:
                message = message.replace("(" + m + ")", m)  # simple fix to infiniparenthesis
                message = message.replace(m, "(" + m + ")")
        return message

    def process_parenthesis(self, message, testing=False):
        finder = re.compile(r'(.*)\((.*?)\)(.*)')  # finds stuff in parenthesis and processes that first
        while finder.findall(message):
            message = self.pretrigger(message)
            tochange = finder.findall(message)[0][1]  # first result, whatever is in parentheses
            if tochange[0] == "#":  # if its a dicecode in itself:
                roll = self.diceparser(tochange)
                self.altrolls.append(roll)
                if "g" in tochange:
                    tobecome = " " + str(roll.roll_sum()) + " "
                    self.dbg = self.dbg[:-3] + self.dbg[-3:].replace(".", ",")
                    self.dbg = self.dbg[:-1] + " for a sum of" + tobecome[:-1] + ". \n"
                else:
                    tobecome = " " + str(roll.roll_nv()) + " "
                    self.dbg = self.dbg[:-3] + self.dbg[-3:].replace(".", ",")
                    self.dbg = self.dbg[:-1] + "for" + tobecome + "successes. \n"
            else:
                tobecome = " " + self.resolvedefine(tochange)
                tobecome = self.preparse(tobecome)
            if testing:
                self.dbg += "Resolving " + tochange + " to " + tobecome + "\n"
            message = message.replace("(" + tochange + ")", tobecome)
            message = self.pretrigger(message)  # one last time
        return message

    def process_triggers(self, message, testing=False):
        triggerfilter = re.compile(r'§[a-zA-Z]*[a-zA-Z0-9_: \-]*')
        triggers = triggerfilter.findall(message)
        for trigger in triggers:
            self.triggers.append(trigger.replace(" ", ""))  # add them to the non executed triggers and
            message = message.replace(trigger, "")  # execute them from the level above.

        return message

    def extract_diceparams(self, message):
        message = message.strip()
        subones = 1
        diff = 6
        dice = 10
        explode = dice
        amount = self.validate_roll(message)  # TDO: make validdroll return range so that parsing dice is easier
        d = message.find("d")
        e = message.find("e")
        f = message.find("f")
        g = message.find("g")
        x = message.find("!")
        if x < 0:
            x = len(message) + 1
        ef = max(e, f, g)
        if amount == 0:
            if len(message) > 1:
                raise Exception('invalid roll: "' + message + '"')
        if amount == 1:
            if " " in message:
                amount = int(message[:message.find(" ")])
            else:
                amount = int(message)
        elif amount == 2:
            amount = int(message[:ef])
            if g != ef:
                diff = int(message[ef + 1:x])
            else:
                diff = 0
            if "f" in message:
                subones = 1
            else:
                subones = 0

        elif amount == 3:
            amount = int(message[:d])
            dice = int(message[d + 1:x])

        elif amount == 4:
            amount = int(message[:d])
            dice = int(message[d + 1: ef])
            if g != ef:
                diff = int(message[ef + 1:x])
            else:
                diff = 0
            if "f" in message:
                subones = 1
            else:
                subones = 0

        explode = dice + 1 - message.count("!")

        return amount, dice, diff, subones, explode

    def write_humanreadable(self, amount, dice, diff, subones, explode):
        if subones:
            onebehaviour = "subtracting"
        else:
            onebehaviour = "ignoring"
        if explode <= dice:
            explodebehaviour = ", exploding on rolls of " + str(explode) + " or more"
        else:
            explodebehaviour = ""
        if diff == 0:
            if dice == 1:
                self.dbg += "==> " + str(amount) + ".\n"  # d1g
                return
            self.dbg += str(amount) + " " + str(dice) + " sided "
            if amount > 1:
                self.dbg += "dice summed together. \n"
            else:
                self.dbg += "die. \n"
        else:
            self.dbg += str(amount) + " " + str(dice) + " sided dice against " + str(diff) + ", " + onebehaviour + \
                        " ones" + explodebehaviour + ". \n"

    def diceparser(self, message, rec=False, testing=False):
        t0 = time.time()
        message = self.pretrigger(message)
        message = self.preparse(message)
        if "?" in message:  # set query flag so output is instead done to self.dbg
            testing = True
            message = message.replace("?", "")
        oldmessage = ""
        t1 = time.time()

        while message != oldmessage:
            oldmessage = message
            message = self.preparse(message)
            message = self.process_parenthesis(message, testing)  # iteratively processes parenthesis
            message = self.process_triggers(message, testing)  # processes triggers to be executed by the instance above
        t2 = time.time()
        message = self.parseadd(message, testing)  # adds all numbers together
        amount, dice, diff, subones, explode = self.extract_diceparams(message)  # actually parses the message into dice
        self.write_humanreadable(amount, dice, diff, subones, explode)  # and generates the human readable messages
        roll = WoDDice(dice, diff, subones, explode)  # creates the Dice object

        roll.roll(amount)  # and rolls the dice :)

        for x in range(len(self.altrolls)):
            if len(self.altrolls[x].r) < 1:
                self.altrolls.pop(x)
        t3 = time.time()
        # print("total=", t3 - t0, "\tpreparsing:", t1 - t0, "\tmain loop:", t2 - t1, "\tpostprocessing:",
        # t3 - t2, "\tfor ", message) #debug timings
        return roll

    with open('strings.json') as json_data:
        shorthand = json.load(json_data)['shorthand']
