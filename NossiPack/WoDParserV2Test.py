import re

from flask import json

from NossiPack.WoDDice import WoDDice


#


class WoDParser(object):
    def __init__(self, defines):
        self.dbg = ""
        self.triggers = []
        self.defines = defines
        self.tmpdefines = {}
        self.altrolls = []  # if the last roll isnt interesting

    @staticmethod
    def extract_diceparams(message):
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
        if info.get('amount', None) is not None:
            info['amount'] = int(info['amount'])
        else:
            raise Exception("invalid dicecode:'" + message + "'")
        if info.get('sidedness', None) is not None:
            info['sidedness'] = int(info['sidedness'])
        else:
            info.pop('sidedness', None)
        info['operation'] = info.get('operation', "")
        info['against'] = info.get('against', "")
        info['onebehaviour'] = 1 if info.get('onebehaviour', "f") == "f" else 0  # would need rewrite if more than 1
        # desired
        if info.get('difficulty', None) is not None:
            info['difficulty'] = int(info['difficulty'])
        else:
            info.pop('difficulty', None)

        info['return'] = "sum" if info.pop("sum", 0) else "max" if info.get("maximum", 0) else "min" if info.get(
            "minimum", 0) else ""

        info['explosion'] = len(info.get('explosion', ""))

        return info

    def do_roll(self, roll):
        self.make_roll(roll)
        return self.altrolls[-1].result

    def make_roll(self, roll):
        roll = Node(roll)
        roll = self.resolveroll(roll)
        params = self.extract_diceparams(roll)

        self.altrolls.append(WoDDice(params))
        return self.altrolls[-1]

    def resolveroll(self, roll):
        print("entered", roll)
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
        print("returned", roll.roll)
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

    @staticmethod
    def gettrigger(message):  # returns (newmessage,triggername, trigger)
        c = message.count("&")

        if c > 0:
            if c % 2 != 0:
                raise Exception("unmatched & in \"" + message + "\"")  # leftover & supposed to be cleared after usage
            else:
                m = message.split("&")
                tail = "&".join(m[1:])
                if tail.startswith("if "):  # special case for nested ifs/triggers
                    end = tail.rfind("else")
                    close = tail[end:].find("&")

                    return m[0] + "&" + tail[end + close + 1:], m[1].split(" ")[0], tail[:end + close].strip()

                return m[0] + "&" + "&".join(m[2:]), m[1].split(" ")[0], " ".join(m[1].split(" ")[1:])
        else:
            return message, "", ""

    def pretrigger(self, message):

        message, triggername, trigger = self.gettrigger(message)
        while triggername:

            if triggername == "values":
                try:
                    trigger = str(re.sub(r" *: *", ":", trigger))
                    for d in trigger.split(","):
                        self.defines[d.split(":")[0].strip()] = d.split(":")[1].strip()
                        message = message.replace("&", "", 1)  # no substitution to be made
                except:
                    raise Exception("Values malformed. Expected: \"&values key:value, key:value, key:value&\"")

            if triggername == "param":
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

            if "if" == triggername:
                # &if a then b else c&
                ifbranch = self.fullparenthesis(trigger, opening="if", closing="then")
                thenbranch = self.fullparenthesis(trigger, opening="then", closing="else")
                elsebranch = self.fullparenthesis(trigger, opening="else", closing="done")
                print(">" + ifbranch + "<" + ">" + thenbranch + "<" + ">" + elsebranch + "<")
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
        print("openclose:", opening, closing)
        while ((lvl > 0) or begun is None) and (i <= len(message) + 5):
            i += 1
            print("lvl:", lvl, i, "<" + message[i:i + max(len(closing), len(opening))] + ">", begun)
            if (message[i:i + len(closing)] == closing) \
                    and (((i == 0 or (not message[i - 1].isalnum()))
                          and not (message + " " * len(closing) * 2)[i + len(closing)].isalnum())
                         or len(closing) == 1):
                if begun is None:
                    continue  # ignore closing parenthesis if not opened yet
                print(lvl, "closing:" + message[i - 1:i + len(closing) + 1])
                lvl -= 1
            else:
                print(message[i - 1], message[i + len(closing)])
            if (message[i:i + len(opening)] == opening) \
                    and (((i == 0 or (not message[i - 1].isalnum()))
                          and not message[i + len(opening)].isalnum())
                         or len(opening) == 1):
                print(lvl, "opening:" + message[i - 3:i + len(opening)])
                lvl += 1
                if begun is None:
                    begun = i
        if i > len(message) + 5:
            print("len", message, "=", message, "\ni:", i)
            raise Exception("unmatched " + opening + " " + closing + ": " + message)
        result = message[begun + (len(opening) if not include else 0):
        i + (len(closing) if include else 0)]
        print("result:",
              begun, (len(opening) if not include else 0),
              i, (len(closing) if include else 0), result)
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
