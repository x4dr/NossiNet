from random import Random
import urllib
import re
import collections

__author__ = 'maric'

import pickle


class Character(object):
    def __init__(self, name="", attributes=None, meta=None, abilities=None,
                 virtues=None, backgrounds=None, disciplines=None,
                 humanity=0, bloodmax=0, blood=0, merits=None):
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
        self.humanity = humanity
        self.bloodmax = bloodmax
        self.blood = blood
        if merits is None:
            self.merits = []
        else:
            self.merits = merits

    def dictlist(self):
        return [self.attributes, self.abilities['Skills'],
                self.abilities['Talents'], self.abilities['Knowledges'],
                self.virtues, self.disciplines]

    def setfromform(self, form):  # accesses internal dicts
        self.attributes = self.zero_attributes()
        self.abilities = self.zero_abilities()
        self.disciplines = collections.OrderedDict()
        self.backgrounds = collections.OrderedDict()
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

            print("error inserting a key!", field + ":", value)

        self.disciplines = collections.OrderedDict(x for x in sorted(self.disciplines.items()) if x[0] != "")
        self.backgrounds = collections.OrderedDict(x for x in sorted(self.backgrounds.items()) if x[0] != "")

    def getdictrepr(self):
        print("compiling dict")
        character = {'Meta': self.meta,
                     'Attributes': self.attributes,
                     'Abilities': self.abilities,
                     'Disciplines': self.disciplines,
                     'Virtues': self.virtues,
                     'Backgrounds': self.backgrounds,
                     'BGVDSCP_combined': self.combine_BGVDSCP()}
        print("dictrepresentation compiled")
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
    def zero_meta():
        meta = {'Name': "",
                'Nature': "",
                'Generation': "",
                'Player': "",
                'Demeanor': "",
                'Haven': "",
                'Chronicle': "",
                'Clan': "",
                'Concept': ""}
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
