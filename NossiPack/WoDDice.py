import random


class WoDDice(object):
    def __init__(self, maxroll=10, difficulty=6, subone=1, explodeon=0, minroll=1):
        self.min = minroll
        self.max = maxroll
        self.difficulty = difficulty
        self.subone = subone
        self.explodeon = explodeon
        self.r = []
        self.log = ""
        self.succ = 0
        self.antisucc = 0
        self.infinity = max(100, maxroll * 10)
        if self.explodeon <= self.min:
            self.explodeon = self.max + 1

    def roll_next(self, amount):
        if self.infinity < amount:
            self.infinity = amount
        i = 0
        self.log = ""
        self.r = []
        self.succ = 0
        self.antisucc = 0
        while i < amount:
            self.r.append(random.randint(self.min, self.max))
            self.log += str(self.r[-1]) + ": "
            if self.r[-1] >= self.difficulty:
                self.succ += 1
                self.log += "success"
            elif self.r[-1] <= self.subone:
                self.antisucc += 1
                self.log += "subtract"
            if self.r[-1] >= self.explodeon:
                amount += 1
                self.log += ", exploding!"
            self.log += "\n"
            if i >= self.infinity:
                break
            i += 1

    @staticmethod
    def botchformat(succ, antisucc):
        if succ > 0:
            if succ <= antisucc:
                return 0
            else:
                return succ - antisucc
        else:
            return 0 - antisucc

    def roll_nv(self):
        return self.botchformat(self.succ, self.antisucc)

    def roll_v(self):
        res = ""
        for i in self.r:
            res += str(i) + ", "
        res = res[:-2] + " ==> " + str(self.botchformat(self.succ, self.antisucc))
        return res

    def roll_vv(self):
        log = self.log
        log += "==> " + str(self.botchformat(self.succ, self.antisucc))
        return log

    def roll(self, amount):
        self.roll_next(amount)
        return self.roll_v()

    @staticmethod
    def shorthand():
        return {
            'str': '#Strength#Potence#strbonus',
            'dex': '#Dexterity#Celerity#dexbonus',
            'sta': '#Stamina#Fortitude#stabonus',
            'strbonus': 0,
            'dexbonus': 0,
            'stabonus': 0,
            'cha': '#Charisma',
            'man': '#Manipulation',
            'app': '#Appearance',
            'per': '#Perception',
            'int': '#Intelligence',
            'wit': '#Wits',
            'aler': '#Alertness_',
            'anim': '#AnimalKen_',
            'acad': '#Academics_',
            'athl': '#Athletics_',
            'craf': '#Crafts_',
            'comp': '#Computer_',
            'braw': '#Brawl_',
            'driv': '#Drive_',
            'fina': '#Finance_',
            'dodg': '#Dodge_',
            'etiq': '#Etiquette_',
            'inve': '#Investigation_',
            'empa': '#Empathy_',
            'fire': '#Firearms_',
            'law': '#Law_',
            'expr': '#Expression_',
            'mele': '#Melee_',
            'ling': '#Linguistics_',
            'inti': '#Intimidation_',
            'perf': '#Performance_',
            'medi': '#Medicine_',
            'lead': '#Leadership_',
            'secu': '#Security_',
            'occu': '#Occult_',
            'stre': '#Streetwise_',
            'stea': '#Stealth_',
            'poli': '#Politics_',
            'subt': '#Subterfuge_',
            'surv': '#Survival_',
            'scie': '#Science_',
            'soak': '#sta#armor e6',
            'hack': '#int#comp',
            'shoot': '#dex#fire',
            'punch': '#dex#braw',
            'strike': '#dex#mele',
            'sneak': '#dex#stea'
        }

    # noinspection PyPep8Naming
    @staticmethod
    def disciplines(char):
        result = {}
        Animalism = char.get('Animalism', 0)
        if Animalism > 0:
            result['Animalism1'] = "#Manipulation#AnimalKen"
        if Animalism > 1:
            result['Animalism2'] = "#Charisma#Survival"
        if Animalism > 2:
            if char.get('Intimidation' , 0) > char.get('Empathy', 0):
                result['Animalism3'] = "#Manipulation#Intimidation"
            else:
                result['Animalism3'] = "#Manipulation#Empathy"
        if Animalism > 3:
            result['Animalism4'] = "#Manipulation#AnimalKen"
        if Animalism > 4:
            result['Animalism5'] = "#Manipulation#SelfControl"

        Auspex = char.get('Auspex', 0)
        if Auspex > 0:
            result['Auspex1'] = "#Auspex"
        if Auspex > 1:
            result['Auspex2'] = "#Perception#Empathy f8"
        if Auspex > 2:
            result['Auspex3'] = "#Perception#Empathy"
        if Auspex > 3:
            result['Auspex4'] = "Intelligence#Subterfuge"
        if Auspex > 4:
            result['Auspex5'] = "#Perception#Alertness"

        Celerity = char.get('Celerity', 0)
        if Celerity > 0:
            result['Celerity1'] = "1d1e1"
        if Celerity > 1:
            result['Celerity2'] = "1d1e1"
        if Celerity > 2:
            result['Celerity3'] = "1d1e1"
        if Celerity > 3:
            result['Celerity4'] = "1d1e1"
        if Celerity > 4:
            result['Celerity5'] = "1d1e1"

        Chimerstry = char.get('Chimerstry', 0)
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

        Dementation = char.get('Dementation', 0)
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

        Dominate = char.get('Dominate', 0)
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

        Flight = char.get('Flight', 0)
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

        Fortitude = char.get('Fortitude', 0)
        if Fortitude > 0:
            result['Fortitude1'] = "1d1e1"
        if Fortitude > 1:
            result['Fortitude2'] = "1d1e1"
        if Fortitude > 2:
            result['Fortitude3'] = "1d1e1"
        if Fortitude > 3:
            result['Fortitude4'] = "1d1e1"
        if Fortitude > 4:
            result['Fortitude5'] = "1d1e1"

        Melpominee = char.get('Melpominee', 0)
        if Melpominee > 0:#TODO
            result['Melpominee1'] = "1d1e1"
        if Melpominee > 1:
            result['Melpominee2'] = "1d1e1"
        if Melpominee > 2:
            result['Melpominee3'] = "1d1e1"
        if Melpominee > 3:
            result['Melpominee4'] = "1d1e1"
        if Melpominee > 4:
            result['Melpominee5'] = "1d1e1"

        Mytherceria = char.get('Mytherceria', 0)
        if Mytherceria > 0: #TODO
            result['Mytherceria1'] = "1d1e1"
        if Mytherceria > 1:
            result['Mytherceria2'] = "1d1e1"
        if Mytherceria > 2:
            result['Mytherceria3'] = "1d1e1"
        if Mytherceria > 3:
            result['Mytherceria4'] = "1d1e1"
        if Mytherceria > 4:
            result['Mytherceria5'] = "1d1e1"

        Necromancy = char.get('Necromancy', 0)
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

        Obeah = char.get('Obeah', 0)
        if Obeah > 0:  # TODO
            result['Obeah1'] = "1d1e1"
        if Obeah > 1:
            result['Obeah2'] = "1d1e1"
        if Obeah > 2:
            result['Obeah3'] = "1d1e1"
        if Obeah > 3:
            result['Obeah4'] = "1d1e1"
        if Obeah > 4:
            result['Obeah5'] = "1d1e1"

        Obfuscate = char.get('Obfuscate', 0)
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

        Obtenebration = char.get('Obtenebration', 0)
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

        Potence = char.get('Potence', 0)
        if Potence > 0:
            result['Potence1'] = "1d1e1"
        if Potence > 1:
            result['Potence2'] = "1d1e1"
        if Potence > 2:
            result['Potence3'] = "1d1e1"
        if Potence > 3:
            result['Potence4'] = "1d1e1"
        if Potence > 4:
            result['Potence5'] = "1d1e1"

        Presence = char.get('Presence', 0)
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

        Protean = char.get('Protean', 0)
        if Protean > 0:
            result['Protean1'] = "1d1e1"
        if Protean > 1:
            result['Protean2'] = "1d1e1"
        if Protean > 2:
            result['Protean3'] = "1d1e1"
        if Protean > 3:
            result['Protean4'] = "1d1e1"
        if Protean > 4:
            result['Protean5'] = "1d1e1"

        Quietus = char.get('Quietus', 0)
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

        Serpentis = char.get('Serpentis', 0)
        if Serpentis > 0:
            result['Serpentis1'] = "#Willpower f9"
        if Serpentis > 1:
            result['Serpentis2'] = "1d1e1"
        if Serpentis > 2:
            result['Serpentis3'] = "1d1e1"
        if Serpentis > 3:
            result['Serpentis4'] = "1d1e1"
        if Serpentis > 4:
            result['Serpentis5'] = "1d1e1"

        Temporis = char.get('Temporis', 0)
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

        Thaumaturgy = char.get('Thaumaturgy', 0)
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

        Vicissitude = char.get('Vicissitude', 0)
        if Vicissitude > 0:
            result['Vicissitude1'] = "1d1e1"
        if Vicissitude > 1:
            result['Vicissitude2'] = "1d1e1"
        if Vicissitude > 2:
            result['Vicissitude3'] = "1d1e1"
        if Vicissitude > 3:
            result['Vicissitude4'] = "1d1e1"
        if Vicissitude > 4:
            result['Vicissitude5'] = "1d1e1"

        Visceratika = char.get('Visceratika', 0)
        if Visceratika > 0:
            result['Visceratika1'] = "1d1e1"
        if Visceratika > 1:
            result['Visceratika2'] = "1d1e1"
        if Visceratika > 2:
            result['Visceratika3'] = "1d1e1"
        if Visceratika > 3:
            result['Visceratika4'] = "1d1e1"
        if Visceratika > 4:
            result['Visceratika5'] = "1d1e1"

        return result
