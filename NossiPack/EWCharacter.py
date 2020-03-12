import pickle
import time
from collections import OrderedDict

__author__ = "maric"

from pprint import pprint

from typing import List, Tuple


class EWCharacter:
    def __init__(self, name="", meta=None):
        self.Data = {}
        self.Tags = ""
        self.Name = name
        self.Character = OrderedDict()
        self.Meta = meta or OrderedDict()

        def sublvl():
            return OrderedDict(
                [
                    ("Attribute", OrderedDict()),
                    ("Fähigkeiten", OrderedDict()),
                    ("Vorteile", OrderedDict()),
                ]
            )

        self.Categories = OrderedDict()
        self.Wounds = []
        self.Modifiers = OrderedDict()
        self.Inventory = OrderedDict()
        self.Notes = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

    def unify(self):
        unified = OrderedDict()
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        return unified

    def process_trigger(self, trigger):
        pass  # for when triggers are being built in

    @staticmethod
    def cost(
        att: Tuple[int, ...], internal_costs: List[int], internal_penalty: List[int]
    ) -> int:
        pen = 0
        for ip, p in enumerate(internal_penalty):
            pen += (max(sum(1 for a in att if a >= ip), 1) - 1) * p
        return sum(internal_costs[a] for a in att) + pen

    @staticmethod
    def leafparse(leaf):
        lines = []
        table = []
        for line in leaf:
            line = line.strip()
            consider = line.split("|")
            consider = (
                consider
                if len(consider) == 2
                else line[
                    1
                    if line.startswith("|")
                    else 0 : -1
                    if line.endswith("|")
                    else len(line)
                ].split("|")
            )
            if len(consider) > 1:
                if all(all(x == "-" for x in y) for y in consider):
                    table = table[:-1]
                else:
                    table += [consider]
            else:
                lines += [line]
        return [table, lines]

    @staticmethod
    def parse_part(lines: List[str], level: int):
        content = {}
        current = 10 ** 10
        buffer = []
        seen = []
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith("#"):
                if line.count("#") <= current:
                    if buffer:
                        content[buffer[1].strip("# ")] = EWCharacter.parse_part(
                            buffer[2:], level + 1
                        )
                    buffer = [""]
                    current = line.count("#")
            if buffer:
                buffer += [line]
            else:
                seen += [line]
        if buffer:
            content[buffer[1].strip("# ")] = EWCharacter.parse_part(
                buffer[2:], level + 1
            )
        elif not content:
            return EWCharacter.leafparse(seen)  # text only
        if seen:  # mixed node
            tab, lin = EWCharacter.leafparse(seen)
            if any(x for x in tab) or any(x for x in lin):
                content["..."] = [tab, lin]
        return content

    def load_from_md(self, title, tags, body):
        self.Name = title
        self.Tags = tags
        self.Data = self.parse_part(body.splitlines(), 0)
        pprint(self.Data)
        return self.Categories

    def setfromform(self, form):  # accesses internal dicts
        pass

    def getdictrepr(self):
        character = OrderedDict(
            [
                ("Categories", self.Categories),
                ("Wounds", self.Wounds),
                ("Modifiers", self.Modifiers),
                ("Inventory", self.Inventory),
                ("Notes", self.Notes),
                ("Type", "FEN"),
            ]
        )
        return character

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        return tmp
