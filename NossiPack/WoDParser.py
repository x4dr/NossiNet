import re

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
            cond = message[message.find("§if_"):]
            cond = self.fullparenthesis(cond)
            trigger = (message[message.find("§if_"):].replace("§if_", "", 1).strip()).replace("(" + cond + ")", "", 1)
            trigger = self.fullparenthesis(trigger)
            roll = self.diceparser(cond)
            res = roll.roll_nv()
            self.altrolls.append(roll)
            self.dbg = self.dbg[:-3] + ", for" + str(res) + " successes. \n"
            if res:
                message = re.sub(r'§if_.*' + re.escape(trigger) + "\)", "(" + trigger.replace("$", str(res)) + ")",
                                 message)
            else:
                message = re.sub(r'§if_.*' + re.escape(trigger) + "\)", "", message)
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
                    self.dbg = self.dbg[:-3]+self.dbg[-3:].replace(".", ",")
                    self.dbg = self.dbg[:-1] + " for a sum of" + tobecome[:-1] + ". \n"
                else:
                    tobecome = " " + str(roll.roll_nv()) + " "
                    self.dbg = self.dbg[:-3]+self.dbg[-3:].replace(".", ",")
                    self.dbg = self.dbg[:-1] + " for " + tobecome + "successes. \n"
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
        message = self.pretrigger(message)
        message = self.preparse(message)
        if "?" in message:  # set query flag so output is instead done to self.dbg
            testing = True
            message = message.replace("?", "")
        oldmessage = ""

        while message != oldmessage:
            oldmessage = message
            message = self.preparse(message)
            message = self.process_parenthesis(message, testing)  # iteratively processes parenthesis
            message = self.process_triggers(message, testing)  # processes triggers to be executed by the instance above
        message = self.parseadd(message, testing)  # adds all numbers together
        amount, dice, diff, subones, explode = self.extract_diceparams(message)  # actually parses the message into dice
        self.write_humanreadable(amount, dice, diff, subones, explode)  # and generates the human readable messages
        roll = WoDDice(dice, diff, subones, explode)  # creates the Dice object

        if amount:
            roll.roll(amount)  # and rolls the dice :)

        for x in range(len(self.altrolls)):
            if len(self.altrolls[x].r) < 1:
                self.altrolls.pop(x)
        if testing:
            self.dbg += "test complete:" + message
            return
        return roll

    @staticmethod
    def shorthand():
        return {
            'str': 'Strength strbonus',
            'dex': 'Dexterity dexbonus',
            'sta': 'Stamina stabonus',
            'strbonus': '0',
            'dexbonus': '0',
            'stabonus': '0',
            'cha': 'Charisma',
            'man': 'Manipulation',
            'app': 'Appearance',
            'per': 'Perception',
            'int': 'Intelligence',
            'wit': 'Wits',
            'aler': 'Alertness_',
            'anim': 'AnimalKen_',
            'acad': 'Academics_',
            'athl': 'Athletics_',
            'craf': 'Crafts_',
            'comp': 'Computer_',
            'braw': 'Brawl_',
            'driv': 'Drive_',
            'fina': 'Finance_',
            'dodg': 'Dodge_',
            'etiq': 'Etiquette_',
            'inve': 'Investigation_',
            'empa': 'Empathy_',
            'fire': 'Firearms_',
            'law': 'Law_',
            'expr': 'Expression_',
            'mele': 'Melee_',
            'ling': 'Linguistics_',
            'inti': 'Intimidation_',
            'perf': 'Performance_',
            'medi': 'Medicine_',
            'lead': 'Leadership_',
            'secu': 'Security_',
            'occu': 'Occult_',
            'stre': 'Streetwise_',
            'stea': 'Stealth_',
            'poli': 'Politics_',
            'subt': 'Subterfuge_',
            'surv': 'Survival_',
            'scie': 'Science_',
            # some examples
            'armor': '0',
            'soak': 'sta armor e6',
            'hack': 'int comp',
            'shoot': 'dex fire',
            'punch': 'dex braw',
            'strike': 'dex mele',
            'sneak': 'dex stea',
            'sum': 'd1g',
            'gundamage': '4',
            'fireweapon': '0 §if_(#shoot difficulty)(#gundamage $ -1 e6) sum §param_difficulty:',
            'bloodheal': '§heal_1 §blood_1',
            'drink': '§blood_-amount §param_amount:',
            'damage': '#(#Aggravated sum)(#Bashing Lethal sum) sum',
            'initiative' : '#(#1 sum) wit dex sum',
            'health': '(#7 - damage) sum'
        }

    # noinspection PyPep8Naming
    @staticmethod
    def disciplines(char):
        result = {}
        Animalism = int(char.get('Animalism', 0))
        if Animalism > 0:
            result['Animalism1'] = "#Manipulation#AnimalKen"
        if Animalism > 1:
            result['Animalism2'] = "#Charisma#Survival"
        if Animalism > 2:
            if int(char.get('Intimidation', 0)) > int(char.get('Intimidation', 0)):
                result['Animalism3'] = "#Manipulation#Intimidation"
            else:
                result['Animalism3'] = "#Manipulation#Empathy"
        if Animalism > 3:
            result['Animalism4'] = "#Manipulation#AnimalKen"
        if Animalism > 4:
            result['Animalism5'] = "#Manipulation#SelfControl"

        Auspex = int(char.get('Auspex', 0))
        if Auspex > 0:
            result['Auspex1'] = "#Auspex"
        if Auspex > 1:
            result['Auspex2'] = "#Perception#Empathy f8"
        if Auspex > 2:
            result['Auspex3'] = "#Perception#Empathy"
        if Auspex > 3:
            result['Auspex4'] = "#Intelligence#Subterfuge"
        if Auspex > 4:
            result['Auspex5'] = "#Perception#Alertness"

        Celerity = int(char.get('Celerity', 0))
        # TODO
        # grants extra dice, not a roll by itself for levels 5 and lower,
        # optional powers _xor_ more dice at 6 and beyond
        if Celerity > 0:
            result['dex'] = "Dexterity Celerity dexbonus"
            result['Celerity1'] = "1d1e1"
        if Celerity > 1:
            result['Celerity2'] = "1d1e1"
        if Celerity > 2:
            result['Celerity3'] = "1d1e1"
        if Celerity > 3:
            result['Celerity4'] = "1d1e1"
        if Celerity > 4:
            result['Celerity5'] = "1d1e1"

        Chimerstry = int(char.get('Chimerstry', 0))
        if Chimerstry > 0:
            result['Chimerstry1'] = "1d1e1"
        if Chimerstry > 1:
            result['Chimerstry2'] = "1d1e1"
        if Chimerstry > 2:
            result['Chimerstry3'] = "1d1e1"
        if Chimerstry > 3:
            result['Chimerstry4'] = "1d1e1"
        if Chimerstry > 4:
            result['Chimerstry5'] = "#Manipulation#Subterfuge"

        Dementation = int(char.get('Dementation', 0))
        if Dementation > 0:
            result['Dementation1'] = "#Charisma#Empathy"
        if Dementation > 1:
            result['Dementation2'] = "#Manipulation#Subterfuge"
        if Dementation > 2:
            result['Dementation3'] = "#Perception#Occult"
        if Dementation > 3:
            result['Dementation4'] = "#Manipulation#Empathy f7"
        if Dementation > 4:
            result['Dementation5'] = "#Manipulation#Intimidation"

        Dominate = int(char.get('Dominate', 0))
        if Dominate > 0:
            result['Dominate1'] = "#Manipulation#Intimidation"
        if Dominate > 1:
            result['Dominate2'] = "#Manipulation#Leadership"
        if Dominate > 2:
            result['Dominate3'] = "#Wits#Subterfuge"
        if Dominate > 3:
            result['Dominate4'] = "#Charisma#Leadership"
        if Dominate > 4:
            result['Dominate5'] = "#Charisma#Intimidation"

        Flight = int(char.get('Flight', 0))
        # TODO
        # has no roll associated, remove or employ house-rules?
        if Flight > 0:
            result['Flight1'] = "1d1e1"
        if Flight > 1:
            result['Flight2'] = "1d1e1"
        if Flight > 2:
            result['Flight3'] = "1d1e1"
        if Flight > 3:
            result['Flight4'] = "1d1e1"
        if Flight > 4:
            result['Flight5'] = "1d1e1"

        Fortitude = int(char.get('Fortitude', 0))
        # TODO
        # grants extra dice for soaks, not a roll by itself for levels 5 and lower,
        # optional powers _xor_ more dice at 6 and beyond
        if Fortitude > 0:
            result['sta'] = 'Stamina Fortitude stabonus'
            result['Fortitude1'] = "1d1e1"
        if Fortitude > 1:
            result['Fortitude2'] = "1d1e1"
        if Fortitude > 2:
            result['Fortitude3'] = "1d1e1"
        if Fortitude > 3:
            result['Fortitude4'] = "1d1e1"
        if Fortitude > 4:
            result['Fortitude5'] = "1d1e1"

        Melpominee = int(char.get('Melpominee', 0))
        if Melpominee > 0:  # TODO
            result['Melpominee1'] = "1d1e1"  # automatic, no roll
        if Melpominee > 1:
            result['Melpominee2'] = "#Wits#Performance f7"  # spend 1 blood
        if Melpominee > 2:
            result['Melpominee3'] = "#Charisma#Performance f7"
        if Melpominee > 3:
            result['Melpominee4'] = "#Manipulation#Performance"
            # Extended, resisted roll, Diff depending on target #Willpower
            # Resisted with Willpower roll (difficulty equal to the singer’s #Appearance#Performance)
        if Melpominee > 4:
            result['Melpominee5'] = "#Stamina#Performance d1e1"  # spend 1 blood for every five targets beyond the first
        # TODO level 6 and 7

        Mytherceria = int(char.get('Mytherceria', 0))
        if Mytherceria > 0:  # TODO
            result['Mytherceria1'] = "1d1e1"  # deliberate auto-success, no roll
        if Mytherceria > 1:
            result['Mytherceria2'] = "1d1e1"  # automatic, no roll
        if Mytherceria > 2:
            result['Mytherceria3'] = "#Perception#Empathy"  # diff at GM discretion
        if Mytherceria > 3:
            result['Mytherceria4'] = "#Intelligence#Larceny f7"
            # for inanimate object. use subject’s current Willpower +2 otherwise
            # resist with #Wits#Investigation f8
        if Mytherceria > 4:
            result['Mytherceria5'] = "#Manipulation#Occult"  # difficulty is the victim’s current Willpower
            # TODO level 6,7 and 8

        Necromancy = int(char.get('Necromancy', 0))
        if Necromancy > 0:  # hausregeln!
            result['Necromancy1'] = "#Perception#Alertness f5"
        if Necromancy > 1:
            result['Necromancy2'] = "#Manipulation#Occult"
        if Necromancy > 2:
            result['Necromancy3'] = "#Occult"
        if Necromancy > 3:
            result['Necromancy4'] = "#Willpower"
        if Necromancy > 4:
            result['Necromancy5'] = "1d1e1"

        Obeah = int(char.get('Obeah', 0))
        if Obeah > 0:  # TODO
            result['Obeah1'] = "#Perception#Empathy f7"
        if Obeah > 1:
            result['Obeah2'] = "#Willpower"  # for willing subject, #Willpower f8 otherwise, spend 1 blood in any case
        if Obeah > 2:
            result['Obeah3'] = "1d1e1"  # no roll, spend 1 blood, more for bigger wounds
        if Obeah > 3:
            result['Obeah4'] = "1d1e1"  # no roll, spend  two  Willpower
            # resist in extended, resisted Willpower roll battle, first to be 3 successes in front of the other wins
        if Obeah > 4:
            result['Obeah5'] = "#Intelligence#Empathy f8"  # spend  two  blood

        Obfuscate = int(char.get('Obfuscate', 0))
        if Obfuscate > 0:
            result['Obfuscate1'] = "#Dexterity#Stealth"
        if Obfuscate > 1:
            result['Obfuscate2'] = "#Dexterity#Stealth"
        if Obfuscate > 2:
            result['Obfuscate3'] = "#Manipulation#Performance f7"
        if Obfuscate > 3:
            result['Obfuscate4'] = "#Charisma#Stealth"
        if Obfuscate > 4:
            result['Obfuscate5'] = "#Stealth d1e1"

        Obtenebration = int(char.get('Obtenebration', 0))
        if Obtenebration > 0:
            result['Obtenebration1'] = "1d1e1"
        if Obtenebration > 1:
            result['Obtenebration2'] = "#Manipulation#Occult f7"
        if Obtenebration > 2:
            result['Obtenebration3'] = "#Manipulation#Occult f7"
        if Obtenebration > 3:
            result['Obtenebration4'] = "#Manipulation#Courage f7"
        if Obtenebration > 4:
            result['Obtenebration5'] = "1d1e1"

        Potence = int(char.get('Potence', 0))
        # TODO
        # grants extra dice for strength rolls, not a roll by itself for levels 5 and lower,
        # optional powers _xor_ more dice at 6 and beyond
        if Potence > 0:
            result['str'] = 'Strength Potence strbonus'
            result['Potence1'] = "1d1e1"
        if Potence > 1:
            result['Potence2'] = "1d1e1"
        if Potence > 2:
            result['Potence3'] = "1d1e1"
        if Potence > 3:
            result['Potence4'] = "1d1e1"
        if Potence > 4:
            result['Potence5'] = "1d1e1"
        # TODO levels 6,7 and 8

        Presence = int(char.get('Presence', 0))
        if Presence > 0:
            result['Presence1'] = "#Charisma#Performance f7"
        if Presence > 1:
            result['Presence2'] = "#Charisma#Intimidation"
        if Presence > 2:
            result['Presence3'] = "#Appearance#Empathy"
        if Presence > 3:
            result['Presence4'] = "#Charisma#Subterfuge"
        if Presence > 4:
            result['Presence5'] = "1d1e1"

        Protean = int(char.get('Protean', 0))
        if Protean > 0:
            result['Protean1'] = "1d1e1"  # no roll
        if Protean > 1:
            result['Protean2'] = "1d1e1"  # spend 1 blood
        if Protean > 2:
            result['Protean3'] = "1d1e1"  # spend 1 blood
        if Protean > 3:
            result['Protean4'] = "1d1e1"  # spend 1 blood, up to 3 to transform faster
        if Protean > 4:
            result['Protean5'] = "1d1e1"  # spend 1 blood, up to 3 to transform faster
        # TODO levels up to 9

        Quietus = int(char.get('Quietus', 0))
        if Quietus > 0:
            result['Quietus1'] = "1d1e1"
        if Quietus > 1:
            result['Quietus2'] = "#Willpower"
        if Quietus > 2:
            result['Quietus3'] = "#Stamina"
        if Quietus > 3:
            result['Quietus4'] = "1d1e1"
        if Quietus > 4:
            result['Quietus5'] = "#Stamina#Athletics"
        # TODO levels up to 9

        Serpentis = int(char.get('Serpentis', 0))
        if Serpentis > 0:
            result['Serpentis1'] = "#Willpower f9"
        if Serpentis > 1:
            result['Serpentis2'] = "1d1e1"  # no roll
        if Serpentis > 2:
            result['Serpentis3'] = "1d1e1"  # spend one blood and one Willpower
        if Serpentis > 3:
            result['Serpentis4'] = "1d1e1"  # spend 1 blood
        if Serpentis > 4:
            result['Serpentis5'] = "1d1e1"  # no roll

        Temporis = int(char.get('Temporis', 0))
        if Temporis > 0:
            result['Temporis1'] = "1d1e1"
        if Temporis > 1:
            result['Temporis2'] = "1d1e1"
        if Temporis > 2:
            result['Temporis3'] = "1d1e1"
        if Temporis > 3:
            result['Temporis4'] = "1d1e1"
        if Temporis > 4:
            result['Temporis5'] = "1d1e1"

        Thaumaturgy = int(char.get('Thaumaturgy', 0))
        if Thaumaturgy > 0:
            result['Thaumaturgy1'] = "#Willpower f4"
        if Thaumaturgy > 1:
            result['Thaumaturgy2'] = "#Willpower f5"
        if Thaumaturgy > 2:
            result['Thaumaturgy3'] = "#Willpower f6"
        if Thaumaturgy > 3:
            result['Thaumaturgy4'] = "#Willpower f7"
        if Thaumaturgy > 4:
            result['Thaumaturgy5'] = "#Willpower f8"

        Vicissitude = int(char.get('Vicissitude', 0))
        if Vicissitude > 0:
            result['Vicissitude1'] = "#Intelligence#Medicine"  # spend one blood point for each body part to be changed
            # #Perception#Medicine f8 if trying to imitate someones face or voice
        if Vicissitude > 1:
            result['Vicissitude2'] = "#Dexterity#Medicine"  # spend 1 blood, variable difficulty
        if Vicissitude > 2:
            result['Vicissitude3'] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
        if Vicissitude > 3:
            result['Vicissitude4'] = "1d1e1"  # no roll, spend two blood points
        if Vicissitude > 4:
            result['Vicissitude5'] = "1d1e1"  # roll system insufficient, this is all about blood
        # TODO up to level 9

        Visceratica = int(char.get('Visceratica', 0))
        if Visceratica > 0:
            result['Visceratica1'] = "#1d1e1"  # spend one blood, +5 stealth for scene
        if Visceratica > 1:
            result['Visceratica2'] = "#1d1e1"  # spend 1 blood, variable difficulty
        if Visceratica > 2:
            result['Visceratica3'] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
        if Visceratica > 3:
            result['Visceratica4'] = "#1d1e1"  # no roll, spend two blood points
        if Visceratica > 4:
            result['Visceratica5'] = "#1d1e1"  # roll system insufficient, this is all about blood

        return result
