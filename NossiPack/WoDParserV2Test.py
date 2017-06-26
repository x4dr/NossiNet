import re

from NossiPack.WoDDice import WoDDice
print("entered wodparser2")

class WoDParser(object):
    def __init__(self, defines, roll):
        self.dbg = ""
        self.triggers = []
        self.roll = Node(roll)
        self.defines = defines
        self.tmpdefines = {}
        self.altrolls = []  # if the last roll isnt interesting

    def nv(self):
        self.altrolls.append()

    def extract_diceparams(self, message):
        message = message.strip()
        subones = 1
        diff = 6
        dice = 10
        amount = self.validate_roll(message)  # TDO: make validdroll return range so that parsing dice is easier
        # find indexes of parameters
        d = message.find("d")
        e = message.find("e")
        f = message.find("f")
        g = message.find("g")
        m = message.find("m")
        x = message.find("!")
        if x < 0:  # no explosion found
            x = len(message) + 1  # so that [:x] reads to the end of the string
        ef = max(e, f, g, m)  # there can be only 1 option, so this is the index of the only option
        if amount == 0:  # detected invalid roll
            if len(message) > 1:  # there is a roll at all
                raise Exception('invalid roll: "' + message + '"')
        if amount == 1:  # detected only amount of default dice at default rules
            if " " in message:  # if there is whitespace
                amount = int(message[:message.find(" ")])  # set amount to how much is before the whitespace
            else:
                amount = int(message)
        elif amount == 2:  # detected options segment, but no sides segment
            amount = int(message[:ef])
            if g == ef:  # if g is the option, negate the difficulty feature
                diff = 0
            elif m == ef:  # if m is the option, negate the difficulty feature and turn it upside down, because #FCKLGC
                diff = -1
            else:  # g and m are not the option
                diff = int(message[ef + 1:x])  # ... so the difficulty is whatever follows (until end of string aka x)
            if "f" in message:  # if f is present, subtract 1es from successes
                subones = 1
            else:  # all other possibilities are exhausted, e must be the option - ignore 1es
                subones = 0

        elif amount == 3:  # detected sides segment, but no options
            amount = int(message[:d])
            dice = int(message[d + 1:x])

        elif amount == 4:  # detected all segments
            amount = int(message[:d])
            dice = int(message[d + 1: ef])
            if g == ef:  # if g is the option, negate the difficulty feature
                diff = 0
            elif m == ef:  # if m is the option, negate the difficulty feature and turn it upside down, because #FCKLGC
                diff = -1
            else:  # g and m are not the option
                diff = int(message[ef + 1:x])  # ... so the difficulty is whatever follows (until end of string aka x)
            if "f" in message:  # if f is present, subtract 1es from successes
                subones = 1
            else:  # all other possibilities are exhausted, e must be the option - ignore 1es
                subones = 0

        explode = dice + 1 - message.count("!")

        return amount, dice, diff, subones, explode

    def do_roll(self, roll):
        roll = self.resolveroll(roll)
        params = self.extract_diceparams(roll)
        return WoDDice(*params[1:]).result(params[1])

    def diceparse(self, message):
        self.expand(self.roll)

    def resolveroll(self, roll):
        if isinstance(roll, str):
            return roll
        print(roll.roll, "=", end="")
        if isinstance(roll.roll, str):
            self.expand(roll)
        print(end="=")
        if roll.is_leaf:
            print("|")
            self.parseadd(roll.roll)
            return " ".join(roll.roll)

        else:
            print(end="=")
            for i in range(len(roll.roll)):
                roll.roll[i] = self.resolveroll(  # recursive
                    roll.dependent.get(roll.roll[i],  # either resolve all the dependencies
                                       roll.roll[i]))  # if not dependent just return the string
            self.parseadd(roll.roll)
        print(end=">")
        print("resolved")
        return " ".join(roll.roll)

    @staticmethod
    def parseadd(roll):
        print("input:", roll)
        adding = 0
        result = [""]
        while len(roll) > 0:
            current = roll.pop(0)
            try:
                adding += int(current)
            except:
                if current != "+":
                    if adding or result[-1] != "0":  # there shouldnt be a case when multiple numbers follow, but jic
                        result.append(str(adding))
                        adding = 0
                        result.append(current)
        print("output:", result)
        return result[1:]

    def expand(self, node):
        self.resolvedefine(node)

    def pretrigger(self, message):
        if "§param_" in message:  # space delimited
            tpos = message.find("§param_")
            tpos2 = message[tpos:].find(" ") + tpos
            triggers = message[tpos:message[tpos:].find(" ") + tpos]
            message = message[:tpos] + message[tpos2:]
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
                    self.tmpdefines[key] = values[i]
                    self.dbg += ("using: " + values[i] + " as " + key + ".\n")
                except:
                    raise Exception("No value for parameter: " + key)
                    # self.defines[key] = "0" # default to 0; alternative
                i += 1
            message = self.preparse(message)  # preparse again

        if "§if_" in message:  # $if_(cond)(then)(else)
            try:
                cond = message[message.find("§if_"):]
                cond = self.fullparenthesis(cond)  # gets the if condition (first parenthesis)
                trigger = (message[message.find("§if_"):].replace("§if_", "", 1).strip()).replace("(" + cond + ")", "",
                                                                                                  1)
                thenbranch = self.fullparenthesis(trigger)  # gets the then branch
                elsebranch = self.fullparenthesis(message[message.find(thenbranch) + len(thenbranch):])  # else branch
                roll = WoDParser({**self.defines, **self.tmpdefines}, cond)
                res = roll.do_roll(roll.roll)
                self.altrolls.append(roll)
                self.dbg = self.dbg[:-3] + ", for " + str(res) + " successes. \n"
                if res > 0:
                    message = re.sub(r'§if_.*' + re.escape(thenbranch) + "\)(\(" + re.escape(elsebranch) + "\))?",
                                     "(" + thenbranch.replace("$", str(res)) + ")",
                                     message)
                else:
                    message = re.sub(r'§if_.*' + re.escape(thenbranch) + "\)(\(" + re.escape(elsebranch) + "\))?",
                                     "(" + elsebranch.replace("$", str(res)) + ")",
                                     message)
            except:
                raise Exception("Malformed if:" + message)
        return message

    def resolvedefine(self, node):
        # makes node.roll into array
        print("entered resolvedefine with", node.roll)
        if isinstance(node.roll, str):
            node.roll = self.pretrigger(node.roll)
            node.roll = node.roll.replace('_', ' ').replace('  ', ' ').split(' ')  # get rid of _ and split

        for b in node.roll:
            if b in self.defines.keys():
                print(b, "=", self.defines.get(b))
                node.dependent[b] = Node(self.defines.get(b), node.depth + 1)
                print(node.dependent[b].roll, "recursive")

                self.resolvedefine(node.dependent[b])  # depth first

    @staticmethod
    def fullparenthesis(message):
        if "(" not in message:
            return message
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


class Node(object):
    def __init__(self, roll, depth=0):
        self.dbg = ""
        self.roll = roll
        self.depth = depth
        self.dependent = {}
        if self.depth > 10:
            raise Exception("recursion depth exceeded")

    @property
    def is_leaf(self):
        return len(self.dependent.keys()) == 0


if __name__ == "__main__":
    test = WoDParser({"a": "19"}, " 1 3 a d5")
    print(">"+test.resolveroll(test.roll)+"<")
