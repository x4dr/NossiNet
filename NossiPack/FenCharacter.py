import base64
import itertools
import pickle
import re
import time
from collections import OrderedDict

__author__ = "maric"

from typing import List, Tuple

from NossiPack.WoDParser import fullparenthesis
from NossiPack.krypta import is_int


def tryfloatbeginning(param, default: float) -> float:
    while param:
        try:
            return float(param)
        except ValueError:
            param = param[:-1]
            continue
    return default


class FenCharacter:
    def __init__(self, name="", meta=None):
        self.Tags = ""
        self.Name = name
        self.Character = OrderedDict()
        self.Meta = meta or OrderedDict()
        self.Categories = OrderedDict()
        self.Wounds = []
        self.Modifiers = OrderedDict()
        self.Inventory = OrderedDict()
        self.Notes = ""
        self.Timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")
        self._xp_cache = None

    @staticmethod
    def sublvl():
        return OrderedDict(
            [
                ("Attribute", OrderedDict()),
                ("Fähigkeiten", OrderedDict()),
                ("Vorteile", OrderedDict()),
            ]
        )

    def unify(self):
        unified = OrderedDict()
        for kind in self.Categories.keys():
            for cat in self.Categories[kind].keys():
                for spec in self.Categories[kind][cat].keys():
                    unified[spec] = self.Categories[kind][cat][spec]
        return unified

    def stat_definitions(self):
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
        return definitions

    def process_trigger(self, trigger):
        pass  # for when triggers are being built in

    @staticmethod
    def cost(
        att: Tuple[int, ...], internal_costs: List[int], internal_penalty: List[int]
    ) -> int:
        pen = 0
        for ip, p in enumerate(internal_penalty):
            pen += (max(sum(1 for a in att if a > ip), 1) - 1) * p
        return sum(internal_costs[a - 1] if a else 0 for a in att) + pen

    @staticmethod
    def cost_calc(inputstring: str, costs=None, penalty=None, width=3):
        if costs:
            costs = [int(x) for x in costs.split(",")]
        else:
            costs = [0, 15, 35, 60, 100]
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
            return [str(c) for c in maximal]
        return FenCharacter.cost(tuple(x - 1 for x in xp), costs, penalty)

    def points(self, name) -> int:
        res = 0
        c = self.Categories[name]
        f = c.get("Fähigkeiten", {}) or c.get("Aspekte", {})
        for k, v in f.items():
            res += self.seekxp(k)
            try:
                res += int(v) * 10
            except ValueError:
                if v[0].lower() == "_":
                    try:
                        res += int(v[1:]) * 5
                    except ValueError:
                        pass
        f = c.get("Quellen", {})
        for k, v in f.items():
            res += self.seekxp(k)
            try:
                res += int(v) * 20
            except ValueError:
                pass

        f = c.get("Vorteile", {}).copy()
        f.update(c.get("Zauber", {}))
        for v in f.values():
            try:
                res += int(v)
            except ValueError:
                if not v or v[0] != "_":
                    res += 1
        return res

    def seekxp(self, name) -> int:
        res = 0
        for catname, cat in self.Categories.items():
            for secname, sec in cat.items():
                if secname.lower().strip() in ["erfahrung", "experience", "xp"]:
                    if sec.get(name, None):
                        res += self.parse_xp(sec[name])
        try:
            for k in self.Meta.keys():
                if k.lower().strip() in ["erfahrung", "experience", "xp"]:
                    self._xp_cache = self._xp_cache or self.parse_part(
                        "\n".join(
                            [
                                "\n".join(x)
                                for x in self.Meta[k].values()
                                if len(x) and isinstance(x[0], str)
                            ]
                        ),
                        True,
                    )
                    if self._xp_cache.get(name, None):
                        res += self.parse_xp(self._xp_cache.get(name, None))
            return res
        except:
            print("XPERROR", k, self.Meta.keys())
            return -9999999

    @staticmethod
    def parse_xp(s):
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

    @staticmethod
    def parse_part(s, parse_table):
        result = OrderedDict()
        categories = [
            x
            for x in re.split(r"\n##(?!#)", "\n" + s, maxsplit=1000, flags=re.MULTILINE)
            if x.strip()
        ]
        for category in categories:
            firstline = category.find("\n")
            categoryname = category[:firstline].strip()
            category = category[firstline + 1 :].strip()
            result[categoryname] = OrderedDict()
            for section in [
                x
                for x in re.split(r"\n###(?!#)", "\n" + category, 1000, re.MULTILINE)
                if x.strip()
            ]:
                firstline = section.find("\n")
                sectionname = section[:firstline].strip()
                section = section[firstline + 1 :].strip()
                result[categoryname][sectionname] = OrderedDict()
                result[categoryname][sectionname]["_lines"] = []
                tablestate = 0
                for line in section.split("\n"):
                    line = line.strip()
                    candidate = [x.strip() for x in line.split("|")]
                    candidate = (
                        candidate
                        if len(candidate) == 2
                        else line[
                            1
                            if line.startswith("|")
                            else 0 : -1
                            if line.endswith("|")
                            else len(line)
                        ].split("|")
                    )
                    if parse_table and len(candidate) == 2:
                        tablestate += 1
                        if tablestate > 2:  # 1: header, 2: alignment
                            while candidate[0] in result[categoryname][sectionname]:
                                candidate[0] = "_" + candidate[0]
                            result[categoryname][sectionname][candidate[0].strip()] = (
                                candidate[1]
                            ).strip()
                    else:
                        tablestate = 0
                        result[categoryname][sectionname]["_lines"].append(line)
                table = FenCharacter.parse_matrix(result[categoryname][sectionname])
                if table:
                    if len(table[0]) > 1:
                        result[categoryname][sectionname]["_table"] = table
                    else:
                        result[categoryname][sectionname]["_lines"].extend(
                            x[0] for x in table
                        )
                if len(result[categoryname][sectionname]["_lines"]) == 0:
                    del result[categoryname][sectionname]["_lines"]
                if not sectionname:
                    for k, v in result[categoryname][sectionname].items():
                        result[categoryname][k] = v
                    del result[categoryname][sectionname]
            if (
                len(result[categoryname].keys()) == 1
                and "_lines" in result[categoryname].keys()
            ):
                result[categoryname] = list(result[categoryname].values())[0]
        for cn in list(result.keys()):
            if not cn:
                if isinstance(result[cn], dict):
                    for k, v in result[cn].items():
                        result[k] = v
                    del result[cn]
            else:
                result.move_to_end(cn, True)
        return result

    def load_from_md(self, title, tags, body):
        self.Name = title
        self.Tags = tags
        self._xp_cache = None
        sheetparts = re.split(r"\n#(?!#)", "\n" + body, re.MULTILINE)
        if len(sheetparts) == 0:
            sheetparts = [body]
        for s in sheetparts:
            firstline = s.find("\n")
            partname = s[:firstline]
            s = s[firstline:]
            if partname.strip().startswith("Werte") or len(sheetparts) == 1:
                parsed_parts = self.parse_part(s, True)
                self.Categories.update(parsed_parts)
            else:
                if partname.strip() in ["", "Charakter"]:
                    self.Character = self.parse_part(s, True)
                else:
                    parsed_parts = self.parse_part(s, False)
                    self.Meta[partname] = parsed_parts
        for catname, catv in list(self.Categories.items()):
            secv = []
            try:
                for secv in list(catv.values()):
                    for itemn, itemv in list(secv.items()):
                        if itemn == "_lines":
                            secv[""] = "\n".join(itemv)
                            del secv["_lines"]
            except AttributeError:
                d = OrderedDict()
                for s in secv:
                    s = s.strip()
                    if " " in s:
                        k, v = s.rsplit(" ", 1)
                    else:
                        k, v = s, {}
                    d[k] = v
                self.Categories[catname] = d
        return self.Categories

    def validate_char(self,):
        comment = self.Name + "NOT IMPLEMENTED"
        return comment

    def setfromform(self, form):  # accesses internal dicts
        form = dict(form)
        self.Notes = form.pop("Notes")[0]
        self.Name = form.pop("Name")[0]
        self.Meta = [
            ("Species", form.pop("Species", [""])[0]),
            ("XP", form.pop("XP", [""])[0]),
            ("Home", form.pop("Home", [""])[0]),
            ("Story", form.pop("Story", [""])[0]),
            ("Size", form.pop("Size", [""])[0]),
            ("Weight", form.pop("Weight", [""])[0]),
            ("Concept", form.pop("Concept", [""])[0]),
            ("Player", form.pop("Player", [""])[0]),
        ]

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

    @staticmethod
    def parse_matrix(param):
        lines = param.get("_lines", [])
        if not lines:
            return []
        output = None
        copy = lines[:]
        while lines:
            line = lines.pop(0)
            if not line.strip():
                continue
            parts = line.strip().split("|")
            if output is None or len(output[-1]) == len(parts):
                output = (output or []) + [parts]
            else:
                if len(output[-1]) - len(parts) <= 2:
                    output = output + [parts + ["", ""]][: len(output[-1])]
                param["_lines"] = copy
                return []
        if all(not x[0] for x in output):
            output = [x[1:] for x in output]
        if all(not x[-1] for x in output):
            output = [x[:-1] for x in output]
        if output[-1][0].lower().strip() in ["total", "summe", "gesamt"]:
            for i in range(1, len(output[-1])):
                output[-1][i] = (
                    "{}".format(
                        round(
                            sum(
                                tryfloatbeginning(outputline[i], 0)
                                for outputline in output[:-1]
                            ),
                            6,
                        )
                    )
                    + output[-1][i]
                )
        return output
