import random
from warnings import warn

from NossiPack.krypta import DescriptiveError


def str_to_slice(inp):
    s = [int(x) if x else None for x in inp.split(":")]
    if len(s) == 1:
        s.append(s[0] + 1)
    return slice(*s)


class WoDDice:
    returnfun: str

    def __init__(self, info):
        try:
            self.sign = 1
            self.min = info.get("additivebonus", 1)  # unlikely to get implemented
            self.returnfun = info.get("return", None)
            try:
                self.amount = int(info["amount"])
            except KeyError:
                raise DescriptiveError("No amount of dice!!")
            try:
                self.max = int(info["sides"]) + self.min - 1
            except KeyError:
                if self.returnfun != "id":
                    raise DescriptiveError("Dice without sides!")
            self.difficulty = info.get("difficulty", None)
            self.subone = info.get("onebehaviour", 0)

            self.explodeon = self.max + 1 - info.get("explosion", 0)
            self.sort = info.get("sort")

            self.rerolls = int(info.get("rerolls", 0))  # only used for fenrolls
            self.r = []
            self.log = ""
            self.dbg = ""
            self.comment = ""
            self.show = False
            self.rolled = False
            if self.explodeon <= self.min:
                self.explodeon = self.max + 1
            if self.returnfun == "id":
                self.max = 1
            if self.amount is not None:
                self.roll_next(int(self.amount))

        except KeyError as e:
            raise DescriptiveError("Missing Parameter: " + str(e.args[0]))
        except Exception as e:
            print("exception during die creation:", e.args, e.__traceback__)
            raise

    def resonance(self, resonator: int):
        return self.r.count(resonator) - 1

    def __repr__(self):
        return self.name

    @property
    def name(self):
        if len(self.r) == 0:
            amount = ""
        else:
            amount = str(len(self.r))
        name = (
            (
                (",".join(str(x) for x in self.returnfun) + "@")
                if isinstance(self.returnfun, list)
                else ""
            )
            + amount
            + "d"
            + str(self.max)
            + ("R" + str(self.rerolls) if self.rerolls != 0 else "")
            + (
                (
                    ("f" if self.subone == 1 else "e" if self.subone == 0 else "-")
                    + str(self.difficulty)
                )
                if self.returnfun == "threshhold"
                else "h"
                if self.returnfun == "max"
                else "l"
                if self.returnfun == "min"
                else "g"
                if self.returnfun == "sum"
                else ""
            )
            + (
                (" exploding on " + str(self.explodeon))
                if self.explodeon <= self.max
                else ""
            )
        )
        if self.returnfun == "id":
            name = (amount or "0") + "len"
        if name.endswith("d1g"):
            name = name[:-3] + "sum"
        return name

    def another(self):
        if not self.amount:
            raise DescriptiveError("No Amount set for reroll!")

        return WoDDice(
            {
                "sides": self.max,
                "difficulty": self.difficulty,
                "onebehaviour": self.subone,
                "return": self.returnfun,
                "explode": self.max - self.explodeon - 1,
                "amount": self.amount,
                "additivebonus": self.min,
                "sort": self.sort,
                "rerolls": self.rerolls,
            }
        )

    def rolldie(self):
        return random.randint(self.min, self.max)

    def modified_amount(self, amount):
        return (
            amount
            + abs(self.rerolls)
            + sum(1 if x >= self.explodeon else 0 for x in self.r)
        )

    def process_rerolls(self):
        self.log = ""
        direction = int(self.rerolls / abs(self.rerolls))
        filtered = []
        reroll = self.rerolls
        tempr = self.r.copy()
        while reroll != 0:
            reroll -= direction
            sel = min(tempr) if direction > 0 else max(tempr)
            filtered.append(sel)
            tempr.remove(sel)

        if self.sort:
            self.r = sorted(self.r)

        if filtered:
            tempstr = ""
            tofilter = filtered.copy()
            par = False
            for i in range(len(self.r)):
                x = self.r[i]
                if x in tofilter and (
                    (direction < 0 and self.r[i:].count(x) <= tofilter.count(x))
                    or direction > 0
                ):
                    if not par:
                        par = True
                        tempstr += "("
                    tofilter.remove(x)
                else:
                    if par:
                        par = False
                        tempstr = tempstr[:-2] + "), "
                tempstr += str(x) + ", "
            tempstr = tempstr[:-2] + (")" if par else "")
            self.log += tempstr
        for sel in filtered:
            self.r.remove(sel)

    def roll_next(self, amount=None):
        if amount is None:
            amount = self.amount
        self.rolled = True
        self.log = ""
        self.r = []
        if amount < 0:
            amount = abs(amount)
            self.sign = -1
        else:
            self.sign = 1
        if self.max == 1:
            self.r = [1] * amount
            return self
        while len(self.r) < self.modified_amount(amount):
            self.r += [
                self.rolldie()
                for _ in range(self.modified_amount(amount) - len(self.r))
            ]

        self.log = ", ".join(str(x) for x in self.r)

        if self.rerolls:
            self.process_rerolls()
        else:
            if self.sort:
                self.log = ""
                self.r = sorted(self.r)
                self.log += ", ".join(str(x) for x in self.r)
        return self

    @staticmethod
    def botchformat(succ, antisucc):
        if succ > 0:
            if succ <= antisucc:
                return 0
            return succ - antisucc
        return 0 - antisucc

    def roll_wodsuccesses(self) -> int:
        succ, antisucc = 0, 0
        for x in self.r:
            self.log += str(x) + ": "
            try:
                diff = int(self.difficulty)
            except:
                raise DescriptiveError("No Difficulty set!")
            if self.r[-1] >= diff:  # last die face >= than the difficulty
                succ += 1
                self.log += "success "
            elif self.r[-1] <= self.subone:
                antisucc += 1
                self.log += "subtract "
            if self.r[-1] >= self.explodeon:
                self.log += "exploding!"
            self.log += "\n"
        return (self.botchformat(succ, antisucc)) * self.sign

    def roll_v(self) -> str:  # verbose
        log = ""
        if self.max == 0:
            return log
        if not (self.name.endswith("sum") or self.name.endswith("len")):
            if not log or self.returnfun == "threshhold":
                log = ", ".join(str(x) for x in self.r)
            elif log:
                log = [x for x in self.log.split("\n") if x][-1].strip()
        res = self.result
        if res is not None:
            if len(self.r) < 1:
                return " ==> 0"
            log += " ==> " + str(res)
        return log

    def roll_vv(self, logslice=None):  # very verbose
        log = self.log
        if isinstance(logslice, str):
            slices = (str_to_slice(x) for x in logslice.split(";"))
            loglines = log.split("\n")
            log = "\n".join("\n".join(loglines[s]) for s in slices)

        res = self.result
        if res is not None:
            log += " ==> " + str(res)
        return log

    def roll_max(self):  # returns max nonverbose as int
        return max(self.r)

    def roll_sel(self):
        selectors = [
            max(min(int(x), len(self.r)), 0) for x in self.returnfun[:-1].split(",")
        ]
        selectors = [x - 1 if x > 0 else None for x in selectors]
        return sum(sorted(self.r)[s] for s in selectors if s is not None) * self.sign

    def roll_vmax(self):  # returns max verbose as int
        log = ""
        for n in self.r:
            log += str(n) + ", "
        self.log = log[:-2] + "= " + str(self.roll_max())
        return self.roll_max()

    def result_sum(self):  # returns sum nonverbose as int
        return sum(self.r)

    def result_vsum(self):  # returns sum verbose
        log = ""
        for n in self.r:
            log += str(n) + " + "
        self.log = log[:-2] + "= " + str(self.result_sum())

    def __int__(self):
        res = self.result
        if self.result is None:
            warn("None roll converted to 0")
            return 0
        return res

    @property
    def result(self) -> int:
        return (
            self.roll_sel()
            if self.returnfun.endswith("@")
            else self.roll_wodsuccesses()
            if self.returnfun == "threshhold"
            else max(self.r) * self.sign
            if self.returnfun == "max"
            else min(self.r) * self.sign
            if self.returnfun == "min"
            else sum(self.r) * self.sign
            if self.returnfun == "sum"
            else None
            if self.returnfun in ["", "None", "none", None]
            else self.amount  # not flipped if negative
            if self.returnfun in ["id"]
            else error("No return function!")
        )

    def roll(self, amount=None):
        if amount is None:
            amount = self.amount
        if not amount:
            raise Exception("No Amount saved!")
        self.roll_next(amount)
        return self.result

    @classmethod
    def empty(cls) -> "WoDDice":
        return WoDDice({"max": 0, "amount": 0, "return": "", "sides": 0})

    def isempty(self):
        return len(self.r) == 0 and self.amount == 0


def error(err):
    raise DescriptiveError(err)
