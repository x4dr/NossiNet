from random import Random
import urllib
import re

__author__ = 'maric'

import pickle


class Character(object):
    def __init__(self, name="", attributes=None, meta=None, abilities=None,
                 virtues=None, backgrounds=None, disciplines=None, discipline_values=None,
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
            self.backgrounds = ["", "", ""]
        else:
            self.backgrounds = backgrounds
        if disciplines is None:
            self.disciplines = ["Discipline 1","Discipline 2","Discipline 3"]
        else:
            self.disciplines = disciplines
        if disciplines is None:
            self.discipline_values = [0,0,0]
        else:
            self.discipline_values = discipline_values
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

    def access(self, field, value=None):  # accesses internal dicts
        if field in self.meta.keys():
            if value is not None:
                self.meta[field] = value
            return self.meta[field]
        if field in self.attributes.keys():
            if value is not None:
                self.attributes[field] = intdef(value)
            return self.attributes[field]
        if field in self.abilities['Skills'].keys():
            if value is not None:
                self.abilities['Skills'][field] = intdef(value)
            return self.abilities['Skills'][field]
        if field in self.abilities['Talents'].keys():
            if value is not None:
                self.abilities['Talents'][field] = intdef(value)
            return self.abilities['Talents'][field]
        if field in self.abilities['Knowledges'].keys():
            if value is not None:
                self.abilities['Knowledges'][field] = intdef(value)
            return self.abilities['Knowledges'][field]
        if "background_" in field:
            if value is not None:
                self.backgrounds = upsert(self.backgrounds,
                                          int(re.match(r'background_(.*)', field).group(1)), value)
            return self.backgrounds
 # TODO:       if "discipline_" in field:
 #           if value is not None:
 #               self.disciplines = upsert(self.disciplines,
 #                                         int(re.match(r'discipline_(.*)_', field).group(1)), value)
 #           return self.disciplines
        print("error inserting a key!", field, value, self.dictlist())

    @staticmethod
    def converttodots(inp):
        res = ""
        for i in range(inp):
            res += "●"
        for i in range(5 - len(res)):
            res += "○"
        return res

    @staticmethod
    def convertdicttodots(inp):
        try:
            return Character.converttodots(inp)
        except:
            inp = inp.copy()
            for i in inp.keys():
                inp[i] = Character.convertdicttodots(inp[i])
        return inp

    def getdictrepr(self):
        character = {'Meta': self.meta,
                     'Attributes': Character.convertdicttodots(self.attributes),
                     'Attributes_numbers': self.attributes,
                     'Abilities': Character.convertdicttodots(self.abilities),
                     'Abilities_numbers': self.abilities,
                     'Disciplines': Character.convertdicttodots(self.disciplines),
                     'Disciplines_numbers': self.disciplines,
                     'Virtues': self.virtues,
                     'Backgrounds': self.backgrounds,
                     'BGVDSCP_combined': self.combine_BGVDSCP()}
        return character

    def combine_BGVDSCP(self):
        combined = []
        lastdiscipline = False
        for i in range(max(len(self.backgrounds), len(self.disciplines.keys()), len(self.virtues.keys()))):
            combined.append({})
            try:
                combined[i]['Background'] = self.backgrounds[i]
            except:
                combined[i]['Background'] = ""
            try:
                combined[i]['Discipline'] = self.disciplines.keys()[i]
            except:
                if lastdiscipline:
                    combined[i]['Discipline'] = ""
                else:
                    combined[i]['Discipline'] = " "
                    lastdiscipline = True
            try:
                combined[i]['Discipline_Value'] = Character.convertdicttodots(self.disciplines[self.disciplines.keys()[i]])
            except:
                combined[i]['Discipline_Value'] = ""
            try:
                combined[i]['Discipline_Value_number'] = self.disciplines[self.disciplines.keys()[i]]
            except:
                combined[i]['Discipline_Value_number'] = ""
            try:
                combined[i]['Virtue'] = self.virtues.keys()[i]
            except:
                combined[i]['Virtue'] = ""
            try:
                combined[i]['Virtue_Value'] = Character.convertdicttodots(self.virtues[self.virtues.keys()[i]])
            except:
                combined[i]['Virtue_Value'] = ""
            try:
                combined[i]['Virtue_Value_number'] = self.virtues[self.virtues.keys()[i]]
            except:
                combined[i]['Virtue_Value_number'] = ""

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
        return {'Conscience/Conviction': 0, 'Self Control/Instinct': 0, 'Courage': 0}

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
    print(prio)

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
