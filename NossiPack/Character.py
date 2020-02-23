import collections
import json
import pickle
import time

from NossiPack.krypta import DescriptiveError

__author__ = "maric"


# Database still uses this, legacy support
class Character(object):
    def __init__(self, name="", attributes=None, meta=None, abilities=None,
                 virtues=None, backgrounds=None, disciplines=None,
                 special=None):
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
            self.backgrounds = collections.OrderedDict()
        else:
            self.backgrounds = backgrounds
        if disciplines is None:
            self.disciplines = collections.OrderedDict()
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

        self.timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

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

    def checksum(self):
        result = 0
        for a in self.unify().values():
            try:
                result += int(a)
            except:
                raise DescriptiveError("could not add up", a)
        return result

    @staticmethod
    def get_backgrounds():
        return ["Allies",
                "Contacts",
                "Retainers",
                "Resources",
                "Status",
                "Influence",
                "Generation",
                "Domain",
                "Fame",
                "Herd",
                "Mentor"]

    def set_attributes_from_int_list(self, att):
        self.attributes['Strength'] = att[0]
        self.attributes['Dexterity'] = att[1]
        self.attributes['Stamina'] = att[2]

        self.attributes['Charisma'] = att[3]
        self.attributes['Manipulation'] = att[4]
        self.attributes['Appearance'] = att[5]

        self.attributes['Perception'] = att[6]
        self.attributes['Intelligence'] = att[7]
        self.attributes['Wits'] = att[8]

    def set_abilities_from_int_list(self, abi):
        i = 0
        for c in reversed(sorted(self.abilities.keys())):
            for a in sorted(self.abilities[c].keys()):
                self.abilities[c][a] = abi[i]
                i += 1

    def validate_char(self, extra=False):
        return ""

    def get_diff(self, old=None, extra=False):
        raise NotImplementedError()

    def dictlist(self):
        raise NotImplementedError()

    def unify(self):
        a = self.dictlist()
        result = {}
        for b in a:
            for i in b.keys():
                result[i] = str(b[i])
        return result

    def setfromform(self, form):  # accesses internal dicts
        raise NotImplementedError()

    def process_trigger(self, trigger):
        raise NotImplementedError()

    def getdictrepr(self):
        raise NotImplementedError()

    def legacy_convert(self):  # this is the legacy section used to update old sheets into new formats
        return True

    @staticmethod
    def zero_attributes():
        attributes = {
            'Strength': 0,
            'Dexterity': 0,
            'Stamina': 0,
            'Charisma': 0,
            'Manipulation': 0,
            'Appearance': 0,
            'Perception': 0,
            'Intelligence': 0,
            'Wits': 0}
        return attributes

    @staticmethod
    def zero_abilities():
        with open('./NossiSite/locales/EN.json') as json_data:
            return json.load(json_data)['abilities']

    @staticmethod
    def zero_specials():
        special = {'Humanity': 0,
                   'Willpower': 0,
                   'Willmax': 1,
                   'Bloodpool': 0,
                   'Bloodmax': 10,
                   'Partialheal': 0,
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
        return collections.OrderedDict({'Conscience': 0, 'SelfControl': 0, 'Courage': 0})

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        tmp.legacy_convert()
        return tmp

    def set_virtues_from_int_list(self, vir):
        self.virtues["Conscience"] = vir[0]
        self.virtues["SelfControl"] = vir[1]
        self.virtues["Courage"] = vir[2]


def intdef(s, default=0):
    try:
        return int(s)
    except Exception:
        return default


def upsert(listinput, index, value, minimum=3):
    if index >= len(listinput):
        listinput.append("")
        index = len(listinput) - 1
    if value != "":
        listinput[index] = value
    else:
        listinput.pop(index)
    if not ("".join(listinput[(-1 * minimum):]) == ""):
        listinput.append("")
    return listinput
