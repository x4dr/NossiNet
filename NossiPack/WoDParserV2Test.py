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
        info = re.match(  # the regex matching the roll (?# ) for indentation
            r'(?# ) *(?P<amount>[0-9]{1,3}) *'  # amount of dice 0-999
            r'(?# )(d *(?P<sidedness>[0-9]{1,5}))? *'  # sidedness of dice 0-99999
            r'(?# )(?P<operation>'  # what is happening with the roll
            r'(?#   )(?P<against>'  # rolling against a value for successes 
            r'(?#     )(?P<onebehaviour>[ef]) *'  # e is without subtracting 1, f is with subtracting a success on a 1
            r'(?#     )(?P<difficulty>([1-9][0-9]{0,4})|([0-9]{0,4}[1-9])))|'  # difficulty 1-99999
            r'(?#   )(?P<sum>g)|'  # summing rolls up instead
            r'(?#   )(?P<maximum>h)| *'  # taking the maximum value of the roll
            r'(?#   )(?P<minimum>l))? *'  # taking the minimum value of the roll
            r'(?# )(?P<explosion>!+)? *$',  # explosion effects
            message)
        info = {k: v for (k, v) in info.groupdict().items() if v} if info else {}
        info['amount'] = int(info.get('amount', 0))
        info['sidedness'] = int(info.get('sidedness', 0))
        info['operation'] = info.get('operation', "")
        info['against'] = info.get('against', "")
        info['onebehaviour'] = 1 if info.get('onebehaviour', "f") == "f" else 0  # would need rewrite if more than 1
        # desired
        info['difficulty'] = int(info.get('difficulty', 0))

        info['return'] = "sum" if info.pop("sum",0) else\
                         "max" if info.get("maximum",0)else\
                         "min" if info.get("minimum",0)else\
                         ""

        info['explosion'] = len(info.get('explosion', ""))

        return info

    def do_roll(self, roll):
        roll = self.resolveroll(roll)
        params = self.extract_diceparams(roll)
        self.altrolls.append(WoDDice(params))
        return self.altrolls[-1].roll(params['amount'])

    def diceparse(self):
        self.expand(self.roll)

    def resolveroll(self, roll):
        if isinstance(roll, str):
            return roll
        if isinstance(roll.roll, str):
            self.expand(roll)

        if roll.is_leaf:
            roll.roll = self.parseadd(roll.roll)
            return " ".join(roll.roll)
        else:
            for i in range(len(roll.roll)):
                roll.roll[i] = self.resolveroll(  # recursive
                    roll.dependent.get(roll.roll[i],  # either resolve all the dependencies
                                       roll.roll[i]))  # if not dependent just return the string
            roll.roll = self.parseadd(roll.roll)
        return " ".join(roll.roll)

    @staticmethod
    def parseadd(roll):
        roll = roll[:]  # copy
        print("input:", roll)
        adding = None
        result = []
        if not roll:
            return result
        for current in roll:  # consume everything
            try:
                print("processing", current, adding, result)
                adding = int(current) + (adding if adding else 0)  # and they are numbers
            except:
                print("processing2", current, adding)
                if current != "+":  # plus and writing things next to each other are equivalent
                    if adding is not None:  # if adding has been set
                        print("adding", current, adding)
                        result.append(str(adding))
                    adding = None
                    print("loop", current, adding, result)
                    result.append(current) if current else None  # only appends if current not ""

        if adding is not None:
            result.append(str(adding))
        print("output:", result)
        return result

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

        if isinstance(node.roll, str):
            node.roll = self.pretrigger(node.roll)
            node.roll = node.roll.replace('_', ' ').replace('  ', ' ').split(' ')  # get rid of _ and split
            node.roll = [n for n in node.roll if n]  # deletes ''
        print("entered resolvedefine with", node.roll)
        for b in node.roll:
            if b in self.defines.keys():
                print(b, "=", self.defines.get(b))
                node.dependent[b] = Node(self.defines.get(b), node.depth + 1)
                print(node.dependent[b].roll, "recursive")
                self.resolvedefine(node.dependent[b])  # depth first
        print("resolvedefine output:", node.roll)

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
