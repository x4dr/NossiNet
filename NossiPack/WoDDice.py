import random
from typing import List, Union


def str_to_slice(inp):
    s = [int(x) if x else None for x in inp.split(":")]
    if len(s) == 1:
        s.append(s[0] + 1)
    return slice(*s)


class WoDDice(object):
    selectors: Union[List[int], str]

    def __init__(self, info):
        try:

            self.min = info.get('additivebonus', 1)  # unlikely to get implemented
            self.max = int(info['sides']) + self.min - 1
            self.difficulty = info['difficulty']
            self.subone = info['onebehaviour']
            self.returnfun = info['return']
            self.explodeon = self.max + 1 - info.get('explode', 0)
            self.sort = info.get('sort')
            self.amount = info['amount']
            self.rerolls = int(info.get("rerolls", 0))  # only used for fenrolls
            self.selectors = info.get("selectors", [])
            if "," in self.selectors:
                self.selectors = [max(min(int(x), self.amount or 0), 0) for x in self.selectors.split(",")]
            self.r = []
            self.log = ""
            self.dbg = ""
            self.comment = ""
            self.show = False
            self.rolled = False
            self.succ = 0
            self.antisucc = 0
            self.maxamount = 100
            if self.explodeon <= self.min:
                self.explodeon = self.max + 1
            if self.amount is not None:
                self.roll_next(int(info.get('amount')))
        except KeyError as e:
            raise Exception("Missing Parameter: " + str(e.args[0]))
        except Exception as e:
            print("exception during die creation:", e.args, e.__traceback__)
            raise

    def resonance(self, resonator: int):
        return self.r.count(resonator) - 1

    @property
    def name(self):
        if len(self.r) == 0:
            amount = ""
        else:
            amount = "#" + str(len(self.r))
        return amount + "d" + str(self.max) + ((("f" if self.subone == 1 else
                                                 "e" if self.subone == 0 else
                                                 "no 1 behaviour") + str(self.difficulty)
                                                ) if not self.returnfun else
                                               "h" if self.returnfun == "max" else
                                               "l" if self.returnfun == "min" else
                                               "g" if self.returnfun == "sum" else "") + (
                   (" exploding on " + str(self.explodeon)) if self.explodeon <= self.max else "")

    def another(self):
        if not self.amount:
            raise Exception("No Amount set for reroll!")
        else:
            return WoDDice({
                'sides': self.max,
                'difficulty': self.difficulty,
                'onebehaviour': self.subone,
                'return': self.returnfun,
                'explode': self.max - self.explodeon - 1,
                'amount': self.amount
            })

    def roll_next(self, amount):
        self.maxamount += amount
        i = 0
        self.rolled = True
        self.log = ""
        self.r = []
        self.succ = 0
        self.antisucc = 0
        while i < amount + abs(self.rerolls):
            if self.max < self.min:
                self.r.append(0)
                self.log += "no dice "
                self.dbg += str(self.max) + " sided dice...?"
                break
            else:
                self.r.append(random.randint(self.min, self.max))
            if self.returnfun == "threshhold":
                self.log += str(self.r[-1])
                self.log += ": "
                if self.r[-1] >= self.difficulty:  # last die face >= than the difficulty
                    self.succ += 1
                    self.log += "success "
                elif self.r[-1] <= self.subone:
                    self.antisucc += 1
                    self.log += "subtract "
                if self.r[-1] >= self.explodeon:
                    amount += 1
                    self.log += "exploding!"
                self.log += "\n"
            else:
                self.log += " "
            if i >= self.maxamount:
                break
            i += 1
        self.log += "\n"

        if self.rerolls:
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
                    if x in tofilter and (direction < 0 and self.r[i:].count(x) <= tofilter.count(x)) or direction > 0:
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
                self.log += tempstr + "\n"
            for sel in filtered:
                self.r.remove(sel)
        else:
            if self.sort:
                self.r = sorted(self.r)
                self.log += ", ".join(str(x) for x in self.r)

    @staticmethod
    def botchformat(succ, antisucc):
        if succ > 0:
            if succ <= antisucc:
                return 0
            else:
                return succ - antisucc
        else:
            return 0 - antisucc

    def roll_wodsuccesses(self):  # non-verbose, returns int
        return self.botchformat(self.succ, self.antisucc) if not len(self.selectors) else self.roll_sel()

    def roll_v(self):  # verbose

        log = [x for x in self.log.split("\n") if x][-1].strip()
        if not log:
            log += ", ".join(str(x) for x in self.r)
        res = self.result
        if res is not None:
            if len(self.r) < 1:
                return " ==> 0"
            log += " ==> " + str(res)
        return log

    def roll_vv(self, logslice=None):  # very verbose
        log = self.log
        if 0 and self.sort:
            log += "\n"
            log += ", ".join(str(x) for x in self.r) + " "
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
        if "," in self.selectors:
            self.selectors = [max(min(int(x), self.amount or 0), 0) for x in self.selectors.split(",")]
        self.selectors = [max(min(int(x), len(self.r)), 0) for x in self.selectors]
        return sum(sorted(self.r)[s - 1] for s in self.selectors)

    def roll_vmax(self):  # returns max verbose as int
        log = ""
        for n in self.r:
            log += str(n) + ", "
        self.log = log[:-2] + "= " + str(self.roll_max())
        return self.roll_max()

    def roll_sum(self):  # returns sum nonverbose as int
        return sum(self.r)

    def roll_vsum(self):  # returns sum verbose 
        log = ""
        for n in self.r:
            log += str(n) + " + "
        self.log = log[:-2] + "= " + str(self.roll_sum())

    @property
    def result(self):
        return (self.roll_sel() if self.selectors else
                self.roll_wodsuccesses() if self.returnfun == "threshhold" else
                max(self.r) if self.returnfun == "max" else
                min(self.r) if self.returnfun == "min" else
                sum(self.r) if self.returnfun == "sum" else None)

    def roll(self, amount):
        self.roll_next(amount)
        return self.result
