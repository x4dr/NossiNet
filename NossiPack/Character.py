from random import Random
import urllib
import re
import collections
import time

__author__ = 'maric'

import pickle


class Character(object):
    def __init__(self, name="", attributes=None, meta=None, abilities=None,
                 virtues=None, backgrounds=None, disciplines=None,
                 special=None, notes=None):
        self.name = name
        if attributes is None:
            self.attributes = self.zero_attributes()
        else:
            self.attributes = attributes
        if abilities is None:
            self.abilities = self.zero_abilities()
        else:
            self.abilities = abilities
        if meta is None:
            self.meta = self.zero_meta()
        else:
            self.meta = meta
        if backgrounds is None:
            self.backgrounds = collections.OrderedDict({"Background": 0})
        else:
            self.backgrounds = backgrounds
        if disciplines is None:
            self.disciplines = collections.OrderedDict({"Discipline": 0})
        else:
            self.disciplines = disciplines
        if virtues is None:
            self.virtues = self.zero_virtues()
        else:
            self.virtues = virtues
        if special is None:
            self.special = self.zero_specials()
        else:
            self.special = special

        self.timestamp = time.strftime("%c")

    @staticmethod
    def calc_cost(val1, val2, cost, cost0):
        lower = min(val1, val2)
        higher = max(val1, val2)
        result = 0
        while (higher - lower) > 0:
            if lower == 0:
                result += cost0
                lower += 1
                continue
            result += cost * lower
            lower += 1
        return result

    def get_clandisciplines(self):
        return {
            "Assamite": "Celerity, Obfuscate, Quietus",
            "Brujah": "Celerity, Potence, Presence",
            "Setite": "Obfuscate, Presence, Serpentis",
            "Gangrel": "Animalism, Fortitude, Protean",
            "Giovanni": "Dominate, Necromancy, Potence",
            "Lasombra": "Dominate, Obtenebration, Potence",
            "Malkavian": "Auspex, Dementation, Obfuscate",
            "Nosferatu": "Animalism, Obfuscate, Potence",
            "Ravnos": "Animalism, Chimerstry, Fortitude",
            "Toreador": "Auspex, Celerity, Presence",
            "Tremere": "Auspex, Dominate, Thaumaturgy",
            "Tzimisce": "Animalism, Auspex, Vicissitude",
            "Ventrue": "Dominate, Fortitude, Presence",
            "Daughter of Cacophony": "Fortitude, Melpominee, Presence",
            "Gargoyle": "Flight, Fortitude, Potence, Visceratika",
            "Kiasyd": "Dominate, Mytherceria, Obtenebration",
            "Salubri": "Auspex, Fortitude, Obeah",
            "Sage": "Potence, Presence, Temporis",
            "Cappadocian": "Auspex,Fortutude,Necromancy"
        }.get(self.meta["Clan"], 'No Clan')

    @property
    def validate_char(self):
        comment = ""
        if self.meta["Clan"] == "Nosferatu":
            self.attributes['appearance'] = 0
        att = [self.attributes['strength'] + self.attributes['dexterity'] + self.attributes['stamina'],
               self.attributes['charisma'] + self.attributes['manipulation'] + self.attributes['appearance'],
               self.attributes['perception'] + self.attributes['intelligence'] + self.attributes['wits']]
        if self.meta["Clan"] == "Nosferatu":
            att[1] += 1  # clan weakness
        att.sort()
        attgrphigh = att[0] - 10
        attgrpmedium = att[1] - 8
        attgrplow = att[2] - 6
        if attgrphigh < 0:
            comment += "highest priority attribute group still needs %d points allocated. \n" % (-attgrphigh)
        if attgrpmedium < 0:
            comment += "medium priority attribute group still needs %d points allocated. \n" % (-attgrpmedium)
        if attgrplow < 0:
            comment += "lowpriority attribute group still needs %d points allocated. \n" % (-attgrplow)

        ski = 0
        for i in self.abilities["Skills"].values():
            ski += i
        kno = 0
        for i in self.abilities["Knowledges"].values():
            ski += i
        tal = 0
        for i in self.abilities["Talents"].values():
            tal += i
        abi = [ski, kno, tal]
        abi.sort()
        abigrphigh = abi[0] - 13
        abigrpmedium = abi[1] - 9
        abigrplow = abi[2] - 5
        if abigrphigh < 0:
            comment += "highest priority ability group still needs %d points allocated. \n" % (-abigrphigh)
        if abigrpmedium < 0:
            comment += "medium priority ability group still needs %d points allocated. \n" % (-abigrpmedium)
        if abigrplow < 0:
            comment += "lowpriority ability group still needs %d points allocated. \n" % (-abigrplow)
        bac = 0
        vir = 0
        dis = 0
        for b in self.backgrounds.values():
            bac += b
        for v in self.virtues.values():
            vir += v
        for d in self.disciplines.values():
            dis += d
        bac -= 5
        vir -= 10
        dis -= 3
        if bac < 0:
            comment += "backgrounds still need %d points allocated" % bac
        if vir < 0:
            comment += "virtues still need %d points allocated" % vir
        if dis < 0:
            comment += "disciplines still need %d points allocated" % dis
        hum = self.special["Humanity"] - self.virtues["Conscience"] - self.virtues["Self Control"]
        wil = self.special["Willmax"] - self.virtues["Courage"]

        if hum < 0:
            comment += "humanity still needs %d points allocated" % hum
        if wil < 0:
            comment += "willpower still needs %d points allocated" % wil

        if comment == "":
            freebs = 15 - attgrphigh * 5 - attgrpmedium * 5 - attgrplow * 5 - abigrphigh * 2 - abigrpmedium * 2 - attgrplow * 2 \
                     - bac * 1 - vir * 2 - dis * 7 - hum * 1 - wil * 1
            if freebs < 0:
                comment = "You have spend %d Freebies too many!" % freebs
            if freebs > 0:
                comment = "You have spend %d Freebies to few!" % freebs
        return comment

    def get_diff(self, old=None):
        xpdiff = 0
        if old is None:
            return self.validate_char

        for a in self.attributes.keys():
            xpdiff += self.calc_cost(self.attributes[a],
                                     old.attributes[a],
                                     4, 1000)
        for b in self.abilities.keys():
            for a in self.abilities[b].keys():
                xpdiff += self.calc_cost(self.abilities[b][a],
                                         old.abilities[b][a],
                                         2, 3)
        for a in self.disciplines.keys():
            cost = 7
            b = self.get_clandisciplines()
            if b == "No Clan":
                c = 6
            elif a in b:
                c = 5
            xpdiff += self.calc_cost(self.disciplines[a], old.disciplines[a], c, 10)

            xpdiff += self.calc_cost(self.special["Willmax"], old.special["Willmax"], 1, 1000)
        return xpdiff

    def dictlist(self):
        return [self.attributes, self.abilities['Skills'],
                self.abilities['Talents'], self.abilities['Knowledges'],
                self.virtues, self.disciplines]

    def setfromform(self, form):  # accesses internal dicts
        self.attributes = self.zero_attributes()
        self.abilities = self.zero_abilities()
        self.disciplines = collections.OrderedDict()
        self.backgrounds = collections.OrderedDict()
        self.special = self.zero_specials()
        for field in form:
            value = form[field]
            if field in self.meta.keys():
                if value is not None:
                    self.meta[field] = value
                continue
            if field in self.attributes.keys():
                if value is not None:
                    self.attributes[field] = intdef(value)
                continue
            if field in self.abilities['Skills'].keys():
                if value is not None:
                    self.abilities['Skills'][field] = intdef(value)
                continue
            if field in self.abilities['Talents'].keys():
                if value is not None:
                    self.abilities['Talents'][field] = intdef(value)
                continue
            if field in self.abilities['Knowledges'].keys():
                if value is not None:
                    self.abilities['Knowledges'][field] = intdef(value)
                continue
            if "background_name_" in field:
                if (value is not None) and (field != "background_name_"):  # no empty submits
                    try:
                        self.backgrounds[value] = \
                            int(form["background_value_" + re.match(r'background_name_(.*)', field).group(1)])
                    except:
                        self.backgrounds[value] = 0
                continue
            if "discipline_name_" in field:
                if (value is not None) and (field != "discipline_name_"):  # no empty submits
                    try:
                        self.disciplines[value] = \
                            int(form["discipline_value_" + re.match(r'discipline_name_(.*)', field).group(1)])
                    except:
                        self.disciplines[value] = 0
                continue
            if "virtue_name_" in field:
                if (value is not None) and (field != "virtue_name_"):  # no empty submits
                    try:
                        self.virtues[value] = \
                            int(form["virtue_value_" + re.match(r'virtue_name_(.*)', field).group(1)])
                    except:
                        self.virtues[value] = 0
                continue
            if "discipline_value_" in field:
                continue
            if "background_value_" in field:
                continue
            if "virtue_value_" in field:
                continue
            if field in self.special.keys():
                if value is not None:
                    self.special[field] = intdef(value)
                    continue

            print("error inserting a key!", field + ":", value)

        self.disciplines = collections.OrderedDict(x for x in sorted(self.disciplines.items()) if x[0] != "")
        self.backgrounds = collections.OrderedDict(x for x in sorted(self.backgrounds.items()) if x[0] != "")

    def getdictrepr(self):
        character = {'Meta': self.meta,
                     'Attributes': self.attributes,
                     'Abilities': self.abilities,
                     'Disciplines': self.disciplines,
                     'Virtues': self.virtues,
                     'Backgrounds': self.backgrounds,
                     'BGVDSCP_combined': self.combine_BGVDSCP(),
                     'Special': self.special}
        return character

    def combine_BGVDSCP(self):
        combined = []
        for i in range(max(len(self.backgrounds), len(self.disciplines.keys()), len(self.virtues.keys()))):
            combined.append({})
            try:
                combined[i]['Background'] = list(self.backgrounds.keys())[i]
            except:
                combined[i]['Background'] = ""
            try:
                combined[i]['Background_Value'] = self.backgrounds[list(self.backgrounds.keys())[i]]
            except:
                combined[i]['Background_Value'] = 0
            try:
                combined[i]['Discipline'] = list(self.disciplines.keys())[i]
            except:
                combined[i]['Discipline'] = ""
            try:
                combined[i]['Discipline_Value'] = self.disciplines[list(self.disciplines.keys())[i]]
            except:
                combined[i]['Discipline_Value'] = 0
            try:
                combined[i]['Virtue'] = list(self.virtues.keys())[i]
            except:
                combined[i]['Virtue'] = ""
            try:
                combined[i]['Virtue_Value'] = self.virtues[list(self.virtues.keys())[i]]
            except:
                combined[i]['Virtue_Value'] = 0

        return combined

    @staticmethod
    def zero_attributes():
        attributes = {
            'strength': 0,
            'dexterity': 0,
            'stamina': 0,
            'charisma': 0,
            'manipulation': 0,
            'appearance': 0,
            'perception': 0,
            'intelligence': 0,
            'wits': 0}
        return attributes

    @staticmethod
    def zero_abilities():
        abilities = {'Talents': {}, 'Skills': {}, 'Knowledges': {}}
        abilities['Talents']['Alertness'] = 0
        abilities['Skills']['AnimalKen'] = 0
        abilities['Knowledges']['Academics'] = 0
        abilities['Talents']['Athletics'] = 0
        abilities['Skills']['Crafts'] = 0
        abilities['Knowledges']['Computer'] = 0
        abilities['Talents']['Brawl'] = 0
        abilities['Skills']['Drive'] = 0
        abilities['Knowledges']['Finance'] = 0
        abilities['Talents']['Dodge'] = 0
        abilities['Skills']['Etiquette'] = 0
        abilities['Knowledges']['Investigation'] = 0
        abilities['Talents']['Empathy'] = 0
        abilities['Skills']['Firearms'] = 0
        abilities['Knowledges']['Law'] = 0
        abilities['Talents']['Expression'] = 0
        abilities['Skills']['Melee'] = 0
        abilities['Knowledges']['Linguistics'] = 0
        abilities['Talents']['Intimidation'] = 0
        abilities['Skills']['Performance'] = 0
        abilities['Knowledges']['Medicine'] = 0
        abilities['Talents']['Leadership'] = 0
        abilities['Skills']['Security'] = 0
        abilities['Knowledges']['Occult'] = 0
        abilities['Talents']['Streetwise'] = 0
        abilities['Skills']['Stealth'] = 0
        abilities['Knowledges']['Politics'] = 0
        abilities['Talents']['Subterfuge'] = 0
        abilities['Skills']['Survival'] = 0
        abilities['Knowledges']['Science'] = 0
        return abilities

    @staticmethod
    def zero_specials():
        special = {'Humanity': 0,
                   'Willpower': 0,
                   'Willmax': 0,
                   'Bloodpool': 0,
                   'Bloodmax': 10,
                   'Bashing': 0,
                   'Lethal': 0,
                   'Aggravated': 0}
        return special

    @staticmethod
    def zero_meta():
        meta = {'Name': "",
                'Nature': "",
                'Generation': "",
                'Player': "",
                'Demeanor': "",
                'Haven': "",
                'Chronicle': "",
                'Clan': "",
                'Concept': "",
                'Notes': "notes",
                'Merits': "merits and flaws",
                'Gear': "Gear"}
        return meta

    @staticmethod
    def zero_virtues():
        return collections.OrderedDict({'Conscience': 0, 'Self Control': 0, 'Courage': 0})

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        return pickle.loads(serialized)


def makechar(min, cap, prioa, priob, prioc):
    response = urllib.request.urlopen(
        "http://www.behindthename.com/random/random.php?number=2&gender=both&surname=&randomsurname=yes&all=no&"
        "usage_ger=1&usage_myth=1&usage_anci=1&usage_bibl=1&usage_hist=1&usage_lite=1&usage_theo=1&usage_goth=1&"
        "usage_fntsy=1")
    char = Character()
    prio = [prioa, priob, prioc]
    Random().shuffle(prio)

    names = re.compile('<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......')
    a = str(response.read())

    result = names.search(a)
    try:
        char.name = (result.group(1) + ", " + result.group(2) + ", " + result.group(3))
    except:
        char.name = "think for yourself"
    return char


def intdef(s, default=0):
    try:
        return int(s)
    except Exception as inst:
        return default


def upsert(list, index, value, min=3):
    if index >= len(list):
        list.append("")
        index = len(list) - 1
    if value != "":
        list[index] = value
    else:
        list.pop(index)
    if not ("".join(list[(-1 * min):]) == ""):
        list.append("")
    return list
