import random


class WoDDice(object):
    def __init__(self, maxroll=None, difficulty=6, subone=1, explodeon=0, minroll=1, rerolls=0, selectors=None):
        try:
            if isinstance(maxroll, dict):
                info = maxroll
                self.min = info.get('additivebonus', 1)  # unlikely to get implemented
                self.max = int(info.get('sidedness', 10)) + self.min - 1
                self.difficulty = info.get('difficulty', difficulty)
                self.subone = info.get('onebehaviour', subone)
                self.returnfun = info.get('return')
                self.sort = info.get('sort', None)
                self.explodeon = self.max + 1 - info.get('explode', explodeon)
                self.amount = info.get('amount', None)
            else:
                self.min = minroll
                self.max = maxroll if maxroll is not None else 10
                self.difficulty = difficulty  # 0 means sum; -1 means highest
                self.subone = subone
                self.explodeon = explodeon
                self.returnfun = ""
                self.amount = None
            self.rerolls = rerolls  # only used for fenrolls
            self.selectors = selectors
            if "," in self.selectors:
                self.selectors = self.selectors.split(",")  # only used for fenrolls
                self.selectors = [max(min(int(x), self.amount or 0), 0) for x in self.selectors]
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
                self.roll_next(int(maxroll.get('amount')))
        except Exception as e:
            print("exception during die creation:", e.args, e.__traceback__.tb_lineno,
                  e.__traceback__.tb_next.tb_lineno)
            raise

    def resonance(self, resonator: int):
        return self.r.count(resonator) - 1

    @property
    def name(self):
        if len(self.r) == 0:
            amount = ""
        else:
            amount = "#" + str(len(self.r))
        return amount + "d" + str(self.max) + ((("f" if self.subone else "e") + str(self.difficulty)
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
                'sidedness': self.max,
                'difficulty': self.difficulty,
                'onebehaviour': self.subone,
                'return': self.returnfun,
                'explode': self.max - self.explodeon - 1,
                'amount': self.amount
            })

    def reroll(self):
        self.roll_next(self.amount)
        return self.result

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
            self.log += str(self.r[-1])
            if not self.selectors:
                if not self.returnfun:
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
        reroll = self.rerolls
        if reroll:
            self.log[-1:] = ';'
            self.log += " reroll selection: "
        while reroll != 0:
            direction = reroll / abs(reroll)
            reroll -= reroll / abs(reroll)
            self.log += " "
            sel = min(self.r) if direction > 0 else max(self.r)
            self.log += str(sel)
            self.r.remove(sel)
            if reroll == 0:
                self.log += "; "
        if self.sort:
            self.r = sorted(self.r)
            self.log += "sorted: " + ", ".join(str(x) for x in self.r)

    @staticmethod
    def botchformat(succ, antisucc):
        if succ > 0:
            if succ <= antisucc:
                return 0
            else:
                return succ - antisucc
        else:
            return 0 - antisucc

    def roll_nv(self):  # non-verbose, returns int
        return self.botchformat(self.succ, self.antisucc)

    def roll_v(self):  # verbose
        log = ""
        rolled = self.r
        log += ", ".join(str(x) for x in rolled)
        if len(self.r) < 1:
            return " ==> 0"
        log = log[:-2] + " ==> " + str(self.result if not len(self.selectors) else self.roll_sel())
        return log

    def roll_vv(self):  # very verbose
        log = self.log
        if self.sort:
            log += "\n"
            log += ", ".join(str(x) for x in self.r) + " "
        log += "==> " + str(self.result)
        return log

    def roll_max(self):  # returns max nonverbose as int
        return max(self.r)

    def roll_sel(self):
        if "," in self.selectors:
            self.selectors = self.selectors.split(",")
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
        return self.roll_sel() if self.selectors else \
            self.roll_nv() if not self.returnfun else \
                max(self.r) if self.returnfun == "max" else \
                    min(self.r) if self.returnfun == "min" else \
                        sum(self.r) if self.returnfun == "sum" else None

    def roll(self, amount):
        self.roll_next(amount)
        return self.result
