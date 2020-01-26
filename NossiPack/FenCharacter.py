import pickle
import re
import time
from collections import OrderedDict

from NossiPack.krypta import DescriptiveError

__author__ = "maric"


def process_table(table):
    lines = [x.strip() for x in table.split("\n") if x.strip()]
    if not lines:
        return OrderedDict()
    arr = [m.strip().strip("|").split("|") for m in lines]
    headers = arr[0]
    line = headers
    try:
        if len(headers) == 2 and all("-" in m for m in arr[1]):
            result = OrderedDict()
            for line in arr[2:]:
                x, y = line
                result[x] = y
            return result
    except:
        pass
    raise DescriptiveError("Problem with: " + "|".join(line) + "\nin\n" + table)


class FenCharacter(object):
    def __init__(self, name="", meta=None):
        self.Tags = ""
        self.Name = name
        self.Character = OrderedDict()
        self.Meta = meta or OrderedDict()

        def sublvl():
            return OrderedDict([("Attribute", OrderedDict()),
                                ("Fähigkeiten", OrderedDict()),
                                ("Vorteile", OrderedDict())])

        self.Categories = OrderedDict([("Stärke", sublvl()),
                                       ("Können", sublvl()),
                                       ("Magie", OrderedDict([("Quelle", None),
                                                              ("Konzepte", None),
                                                              ("Aspekte", None),
                                                              ("Zauber", None),
                                                              ("Vorteile", None)])),
                                       ("Weisheit", sublvl()),
                                       ("Charisma", sublvl()),
                                       ("Schicksal", sublvl())])
        self.Wounds = []
        self.Modifiers = OrderedDict()
        self.Inventory = OrderedDict()
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
        unified = OrderedDict()
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        # print("unified fensheet:", unified)
        return unified

    def process_trigger(self, trigger):
        pass  # for when triggers are being built in

    @staticmethod
    def parse_part(s, all_lines=False):
        result = OrderedDict()
        categories = [x for x in re.split(r"\n##(?!#)", "\n" + s,
                                          maxsplit=1000, flags=re.MULTILINE) if x.strip()]
        for category in categories:
            firstline = category.find("\n")
            categoryname = category[:firstline].strip()
            category = category[firstline + 1:].strip()
            print("found category:", categoryname)
            result[categoryname] = OrderedDict()
            for section in [x for x in re.split(r"\n###(?!#)", "\n" + category, 1000, re.MULTILINE) if x.strip()]:
                firstline = section.find("\n")
                sectionname = section[:firstline].strip()
                print("found section:", sectionname)
                section = section[firstline + 1:].strip()
                tableslurp = ""
                li = []
                for l in section.split("\n"):
                    li.append(l)
                    if "|" in l or tableslurp and tableslurp[-1] != " ":
                        tableslurp += l.strip() + "\n"
                    else:
                        tableslurp += " "
                tableslurp = tableslurp.strip()
                if tableslurp:
                    result[categoryname][sectionname] = process_table(tableslurp)
                else:
                    if all_lines:
                        result[categoryname][sectionname] = li
                    else:
                        result[categoryname][sectionname] = OrderedDict()
            if len(result[categoryname].keys()) == 1 and not list(result[categoryname].keys())[0].strip():
                result[categoryname] = list(result[categoryname].values())[0]
        return result

    def load_from_md(self, title, tags, body):
        self.Name = title
        self.Tags = tags

        sheetparts = re.split(r"\n#(?!#)", "\n" + body, re.MULTILINE)
        if len("sheetparts") == 0:
            sheetparts = [body]
        for s in sheetparts:
            print("sheetpart:", s[:25] + "/sheetpart")
            firstline = s.find("\n")
            partname = s[:firstline]
            s = s[firstline:]
            if partname.strip().startswith("Werte") or len(sheetparts) == 1:
                tmp = self.parse_part(s)
                self.Categories.update(tmp)
            else:
                if partname.strip() in ["", "Charakter"]:
                    self.Character = self.parse_part(s, True)
                else:
                    self.Meta[partname] = self.parse_part(s, True)
        print(self.Categories.keys(), self.Meta)
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
        self.Meta = [("Species", form.pop("Species", [""])[0]),
                     ("XP", form.pop("XP", [""])[0]),
                     ("Home", form.pop("Home", [""])[0]),
                     ("Story", form.pop("Story", [""])[0]),
                     ("Size", form.pop("Size", [""])[0]),
                     ("Weight", form.pop("Weight", [""])[0]),
                     ("Concept", form.pop("Concept", [""])[0]),
                     ("Player", form.pop("Player", [""])[0])]

        for key, val in form.items():
            s = key.split("_")
            if len(s) != 3:
                continue
            k = key.split("_")[0]
            sub_key = key.split("_")[1]
            if form.get(key + "_val"):
                if self.Categories.get(k, None) is None:
                    self.Categories[k] = OrderedDict()
                if self.Categories[k].get(sub_key, None) is None:
                    self.Categories[k][sub_key] = OrderedDict()
                self.Categories[k][sub_key][val[0]] = int(form.get(key + "_val")[0])

    def getdictrepr(self):
        character = OrderedDict([('Categories', self.Categories),
                                 ('Wounds', self.Wounds),
                                 ('Modifiers', self.Modifiers),
                                 ('Inventory', self.Inventory),
                                 ('Notes', self.Notes),
                                 ('Type', "FEN")])
        # print("character:", character)
        return character

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        return tmp
