import pickle
import time
from collections import OrderedDict

__author__ = "maric"


class FenCharacter(object):
    def __init__(self, name="", meta=None):
        self.Tags = ""
        self.Name = name
        self.Meta = meta
        self.Categories = {"Stärke": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Fortschritt": {}},
                           "Können": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Fortschritt": {}},
                           "Magie": {"Quelle": {}, "Konzepte": {}, "Aspekte": {}, "Vorteile": {}, "Fortschritt": {}},
                           "Weisheit": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Fortschritt": {}},
                           "Charisma": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Fortschritt": {}},
                           "Schicksal": {"Attribute": {}, "Fähigkeiten": {}, "Vorteile": {}, "Fortschritt": {}}}
        self.Wounds = []
        self.Modifiers = {}
        self.Inventory = {}
        self.Notes = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

    @staticmethod
    def costs(cat, val):
        if cat == "Attribute":
            return (-20 if val < 2 else
                    0 if val == 2 else
                    FenCharacter.costs(cat, val - 1) + (val - 2) * 20)  # [-20, 0, 20, 60, 120],
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
        return abs(self.allcosts()) + 1

    def unify(self):
        unified = {}
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        # print("unified fensheet:", unified)
        return unified

    def process_trigger(self, trigger):
        pass  # for when triggers are being built in

    def load_from_md(self, templatemd, title, tags, body):
        cursec = ""
        subsection = ""
        self.Name = title
        self.Tags = tags
        f = templatemd.split("\n")
        for b in body.split("###"):
            print("->",b[:100])
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
        form = dict(form)
        self.Notes = form.pop("Notes")[0]
        self.Name = form.pop("Name")[0]
        self.Meta = {"Species": form.pop("Species", [""])[0],
                     "XP": form.pop("XP", [""])[0],
                     "Home": form.pop("Home", [""])[0],
                     "Story": form.pop("Story", [""])[0],
                     "Size": form.pop("Size", [""])[0],
                     "Weight": form.pop("Weight", [""])[0],
                     "Concept": form.pop("Concept", [""])[0],
                     "Player": form.pop("Player", [""])[0]}
        for key, val in form.items():
            s = key.split("_")
            if len(s) != 3:
                continue
            k = key.split("_")[0]
            sub_key = key.split("_")[1]
            if form.get(key + "_val"):
                if self.Categories.get(k, None) is None:
                    self.Categories[k] = {}
                if self.Categories[k].get(sub_key, None) is None:
                    self.Categories[k][sub_key] = {}
                self.Categories[k][sub_key][val[0]] = int(form.get(key + "_val")[0])

    def getdictrepr(self):
        character = {'Categories': self.Categories,
                     'Wounds': self.Wounds,
                     'Modifiers': self.Modifiers,
                     'Inventory': self.Inventory,
                     'Notes': self.Notes,
                     'Type': "FEN"}
        # print("character:", character)
        return character

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        return tmp
