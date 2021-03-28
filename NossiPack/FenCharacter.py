import base64
import itertools
import time

__author__ = "maric"

from collections import OrderedDict

from typing import List, Tuple

from Fantasy.Item import Item
from NossiPack.DiceParser import fullparenthesis
from NossiPack.MDPack import split_md, extract_tables, confine_to_tables, total_table
from NossiPack.krypta import is_int


class FenCharacter:
    Inventory: List[Item]
    description_headings = [
        "charakter",
        "character",
        "beschreibung",
        "description",
    ]
    value_headings = ["werte", "values", "statistics", "stats"]
    inventory_headings = ["inventar", "inventory"]
    doublepoint_sections = ["quellen", "sources"]
    halfpoint_sections = ["forma"]
    fullpoint_sections = ["fähigkeiten", "skills", "aspekte", "aspects"]
    onepoint_sections = ["vorteile", "perks", "zauber", "spells"]
    experience_headings = ["erfahrung", "experience", "xp"]
    wound_headings = ["wunden", "wounds", "damage", "schaden"]

    def __init__(
        self,
        name="",
    ):
        self.definitions = None
        self.Tags = ""
        self.Name = name
        self.Character = OrderedDict()
        self.Meta = OrderedDict()
        self.Categories = OrderedDict()
        self.Inventory = []
        self.Notes = ""
        self.Storage = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")
        self._xp_cache = {}
        self.errors = []

    def stat_definitions(self) -> dict:
        """
        :return: simplified dictionary of stats and their values
        """
        if self.definitions is not None:
            return self.definitions
        definitions = {}
        for catname, cat in self.Categories.items():
            for secname, sec in cat.items():
                for statname, stat in sec.items():
                    stat = stat.strip(" _")
                    if statname.strip() and is_int(stat):
                        qualifier = str(
                            base64.b64encode(
                                ".".join(
                                    [catname.strip(), secname.strip(), statname.strip()]
                                ).encode()
                            )
                        )
                        if definitions.get(statname, None) is None:
                            definitions[statname.strip()] = qualifier
                            definitions[statname.strip().lower()] = qualifier
                            definitions[
                                ".".join(
                                    [catname.strip(), secname.strip(), statname.strip()]
                                )
                            ] = qualifier
                        definitions[qualifier] = stat
        self.definitions = definitions
        return definitions

    @staticmethod
    def cost(
        att: Tuple[int, ...], internal_costs: List[int], internal_penalty: List[int]
    ) -> int:
        """
        tuple of attributes to xp costs

        :param att: attributes
        :param internal_costs: absolute cost of each level
        :param internal_penalty: point costs for all attributes beyond the first to reach that level
        :return: total fp costs
        """
        pen = 0
        for ip, p in enumerate(internal_penalty):
            pen += (max(sum(1 for a in att if a > ip), 1) - 1) * p
        return sum(internal_costs[a - 1] if a > 0 else 0 for a in att) + pen

    @staticmethod
    def cost_calc(inputstring, costs=None, penalty=None, width=3):
        """
        returns fp cost of attributes if given a , separated list of attributes
        if given a single integer (or a integer representing string) it will output possible
        attribute distributions for those costs and penalties

        :param inputstring:  or output of points
        :param costs: absolute cost for each level
        :param penalty: point costs for all attributes beyond the first to reach that level
        :param width: amount of attributes
        :return: list -> int, int -> list of lists
        """
        if costs:
            costs = [int(x) for x in costs.split(",")]
        else:
            costs = [0, 15, 35, 60, 100]  # default are attribute costs
        if penalty:
            penalty = [int(x) for x in penalty.split(",")]
        else:
            penalty = [0, 0, 0, 50, 100]
        xp = [int(x or 0) for x in str(inputstring).split(",")]
        if len(xp) == 1:
            xp = xp[0]
            allconf = set(
                tuple(sorted(x, reverse=True))
                for x in itertools.product(range(6), repeat=int(width))
            )
            correct = [
                [y for y in x]
                for x in allconf
                if FenCharacter.cost(x, costs, penalty) <= xp
            ]
            i = 0
            j = len(correct)
            maximal = correct[:]
            while i < j:
                for u in range(len(maximal[i])):
                    upg = list(maximal[i])
                    upg[u] = upg[u] + 1
                    # upg = tuple(upg)
                    if upg in correct:
                        del maximal[i]
                        i -= 1
                        j -= 1
                        break
                i += 1
            return [c for c in maximal]
        return FenCharacter.cost(tuple(xp), costs, penalty)

    def magicwidth(self, name) -> int:
        c = self.Categories[name]
        f = {}
        for k in c.keys():
            if k.lower() in ["konzepte", "concepts"]:
                f.update(c[k])
        return len(f)

    def points(self, name) -> int:
        """
        total fp for a given category.
        members with a _ prefix are treated differently, according to their type

        :param name: the CATEGORY name to calculate
        :return: number of FP (full for the already skilled ones and partial for those written down in the xp table)
        """
        res = 0
        c = self.Categories[name]
        f = {}
        for k in c.keys():
            if k.lower() in self.fullpoint_sections:
                f.update(c[k])
        for k, v in f.items():
            res += self.get_xp_for(k)
            try:
                res += int(v) * 10
            except ValueError:

                if v and v[0].lower() == "_":
                    try:
                        res += int(v[1:]) * 5
                    except ValueError:
                        pass
        f = {}
        for k in c.keys():
            if k.lower() in self.doublepoint_sections:
                f.update(c[k])
        for k, v in f.items():
            res += self.get_xp_for(k)
            try:
                res += int(v) * 20
            except ValueError:
                pass

        f = {}
        for k in c.keys():
            if k.lower() in self.halfpoint_sections:
                f.update(c[k])
        for k, v in f.items():
            res += self.get_xp_for(k)
            try:
                res += int(v) * 5
            except ValueError:
                pass

        f = {}
        for k in c.keys():
            if k.lower() in self.onepoint_sections:
                f.update(c[k])
        for k, v in f.items():
            try:
                res += int(v)
            except ValueError:
                if k.strip() and (not v or v[0] != "_"):
                    res += 1
        return res

    def get_xp_for(self, name) -> int:
        """
        :param name: name of some stat
        :return: total amount of xp associated with that name
        """
        return self._xp_cache.get(name, 0)

    @staticmethod
    def parse_xp(s):
        """
        every letter is one xp, parenthesis mean the xp is conditional and will not be counted
        entries in [] are counted as , separated and allow for longer names
        """
        res = 0
        paren = ""
        while paren != s:
            if paren:
                pos = s.find(paren)
                s = s.replace(s[max(0, pos - 1) : pos + len(paren)], "", 1)
            paren = fullparenthesis(s, include=True)
        paren = ""
        while paren != s:
            if paren.strip():
                res += 1 + paren.count(",")
            s = s.replace("[" + paren + "]", "", 1)
            paren = fullparenthesis(s, "[", "]")
        res += sum([1 for x in s if x.strip()])
        return res

    def load_from_md(self, body, flash=None):
        """
        takes in the entire character sheet and constructs the Fencharacter object from it

        :param flash: function to call for each error
        :param body: md string with the charactersheet
        :return:
        """
        if not flash:

            def flash(err):
                self.errors.append(err)

        sheetparts = extract_tables(split_md(body), flash)

        # inform about things that should not be there
        if sheetparts[0].strip():
            flash("Loose Text: " + sheetparts[0])
        if sheetparts[2]:
            for t in sheetparts[2]:
                if t:
                    flash(
                        "Loose Table:"
                        + "\n".join("\t".join(x for x in row) for row in t)
                    )

        for s in sheetparts[1].keys():
            if s.lower().strip() in self.value_headings:
                d, errors = confine_to_tables(sheetparts[1][s], headers=False)
                self.Categories.update(d)
                for e in errors:
                    flash(e)
            else:
                if s.strip().lower() in self.description_headings:
                    d, errors = confine_to_tables(sheetparts[1][s], headers=False)
                    self.Character = d
                    for e in errors:
                        flash(e)
                else:
                    self.Meta[s] = sheetparts[1][s]

        self.post_process(flash)

    def post_process(self, flash):
        # tally inventory
        for k in self.Meta.keys():
            if k.lower() in self.inventory_headings:
                self.process_inventory(self.Meta[k], flash)
                self.Meta[k][2].insert(0, self.inventory_table())
            if k.lower() in self.experience_headings:
                if not self._xp_cache:  # generate once
                    self._xp_cache = {}
                    self.process_xp(self.Meta[k])

    def process_inventory(self, node, flash):
        for table in node[2]:
            self.Inventory += Item.process_table(table, flash)
        for content in node[1].values():
            self.process_inventory(content, flash)

    def process_xp(self, node):
        for table in node[2]:
            first = True
            for row in table:
                if len(row) < 2:
                    continue  # skip invalid rows
                self._xp_cache[row[0]] = self.parse_xp(row[1])
                if first:
                    row.append("=")
                    first = False
                else:
                    row.append(self._xp_cache[row[0]])
        for content in node[1].values():
            self.process_xp(content)

    @classmethod
    def from_md(cls, arg, flash=None):
        res = cls()
        res.load_from_md(arg, flash)
        return res

    def inventory_table(self):
        inv_table = [
            ["Name", "Anzahl", "Gewicht", "Preis", "Gewicht Gesamt", "Preis Gesamt"]
        ]
        for i in self.Inventory:
            inv_table.append(
                [
                    f"[ {i.name} [[q:-: {i.name} :-]]]",
                    f"{i.count:g}",
                    i.singular_weight,
                    i.singular_price,
                    i.total_weight,
                    i.total_price,
                ]
            )
        inv_table.append(["Gesamt", "", "", "", "", ""])
        total_table(inv_table, print)
        return inv_table

    def wounds(self):
        for k in self.Character.keys():
            if k.lower() in self.wound_headings:
                wounds = self.Character[k]
                header = k
                return header, wounds
        else:
            return None, {}
