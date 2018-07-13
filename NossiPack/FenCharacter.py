import pickle
import time
from collections import OrderedDict

__author__ = "maric"


class FenCharacter(object):
    def __init__(self, name="", meta=None):
        self.Tags = ""
        self.Name = name
        self.Meta = meta
        self.Categories = {"Stärke": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}},
                           "Können": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}},
                           "Magie": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}},
                           "Weisheit": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}},
                           "Charisma": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}},
                           "Schicksal": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Zeit": {}}}
        self.Wounds = []
        self.Modifiers = {}
        self.Inventory = {}
        self.Notes = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

    @staticmethod
    def costs(cat, val):
        if cat == "Attribute":
            return -20 if val < 2 else \
                0 if val == 2 else \
                    FenCharacter.costs(cat, val - 1) + (val - 2) * 20  # [-20, 0, 20, 60, 120],
        elif cat == "Fähigkeiten":
            return 0 if val == 0 else \
                FenCharacter.costs(cat, val - 1) + 5 * val  # [5, 15, 30, 50, 75],
        elif cat == "Quellen":
            return 0 if val == 0 else \
                5 if val == 1 else \
                    FenCharacter.costs(cat, val - 1) * 2  # [5, 10, 20, 40, 80]
        elif cat == "Konzepte":
            return 0 if val == 0 else \
                5 if val == 1 else \
                    FenCharacter.costs(cat, val - 1) * 2 + 15  # [5, 15, 45, 135, 405],
        elif cat == "Aspekte":
            return 0 if val == 0 else \
                FenCharacter.costs(cat, val - 1) + 5 * val  # [5, 15, 30, 50, 75],
        elif cat == "Zauber":  # [5, 5, 5, 5, 5],
            return 5
        elif cat == "Vorteile":
            return 3 * val  # [3, 6, 9, 12, 15],
        elif cat == "Talente":  # [5, 11, 18, 26, 35]
            return 0 if val == 0 else \
                FenCharacter.costs(cat, val - 1) + 5 + (val - 1)
        else:
            return 100000  # default value for unknown categories

    def allcosts(self):
        result = 0
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    result += self.costs(cat, self.Categories[kind][cat][spec])

        return result

    def checksum(self):
        return self.allcosts()

    def unify(self):
        unified = {}
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        print("unified fensheet:", unified)
        return unified

    def load_from_md(self, templatemd, title, tags, body):
        cursec = ""
        subsection = ""
        self.Name = title
        self.Tags = tags
        f = templatemd.split("\n")
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("*") and subsection:
                item = line[2:]
                self.Categories[cursec][subsection][item] = 0
            else:
                subsection = ""
            if line.startswith("##") and not line.startswith("###"):
                cursec = line[2:]
                self.Categories[cursec] = OrderedDict()
            if line.startswith("###") and cursec:
                subsection = line[3:]
                self.Categories[cursec][subsection] = OrderedDict()

        cursec = ""
        subsection = ""
        keys = []

        for line in (body + "\n").split("\n"):
            line = line.strip()
            if "|" in line and subsection:
                line = line.strip("|")
                key = line.split("|")
                try:
                    value = key[1]
                except Exception:
                    value = "0"
                key = key[0]
                keys.append(key)
                try:
                    self.Categories[cursec][subsection][key] = int(value)
                except Exception:
                    pass
                continue
            else:
                if subsection:  # table ends found process the current one and empty subsection
                    try:
                        for k in self.Categories[cursec][subsection].keys():
                            if k not in keys:
                                if subsection.startswith("Attribute"):
                                    self.Categories[cursec][subsection][k] = 2
                                else:
                                    self.Categories[cursec][subsection][k] = 0
                    except KeyError:
                        pass
                    finally:
                        subsection = ""

            if line.startswith("##") and not line.startswith("###"):
                if cursec:  # if new section found, process the current table and continue
                    for subsect in self.Categories[cursec].keys():
                        if self.Categories[cursec].get(subsect, None) is None:
                            for newitem in self.Categories[cursec][subsect]:
                                if subsection.startswith("Attribute"):
                                    self.Categories[cursec][subsection][newitem] = 2
                                else:
                                    self.Categories[cursec][subsection][newitem] = 0

                cursec = line.strip('#')
                self.Categories[cursec] = self.Categories.get(cursec, OrderedDict())

            if line.startswith("###") and cursec:
                subsection = line[3:]
                self.Categories[cursec][subsection] = self.Categories[cursec].get(cursec, OrderedDict())

        return self.Categories

    def validate_char(self, ):
        comment = self.Name + "NOT IMPLEMENTED"
        return comment

    def get_diff(self, old=None):
        return old.allcosts() - self.allcosts()

    def setfromform(self, form):  # accesses internal dicts
        print(form)
        self.Categories["editing"] = {"is not": {"implemented yet": 1}}
        self.Notes=form.get("Notes")
        pass

    def getdictrepr(self):
        character = {'Categories': self.Categories,
                     'Wounds': self.Wounds,
                     'Modifiers': self.Modifiers,
                     'Inventory': self.Inventory,
                     'Notes': self.Notes,
                     'Type': "FEN"}
        return character

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        return tmp
