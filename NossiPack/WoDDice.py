import random


class WoDDice(object):
    def __init__(self, maxroll=10, difficulty=6, subone=1, explodeon=0, minroll=1):
        self.min = minroll
        self.max = maxroll
        self.difficulty = difficulty
        self.subone = subone
        self.explodeon = explodeon
        self.r = []
        self.log = ""
        self.dbg = ""
        self.comment = ""
        self.rolled = False
        self.succ = 0
        self.antisucc = 0
        self.maxamount = 100
        if self.explodeon <= self.min:
            self.explodeon = self.max + 1

    def roll_next(self, amount):
        self.maxamount += amount
        i = 0
        self.rolled = True
        self.log = ""
        self.r = []
        self.succ = 0
        self.antisucc = 0
        while i < amount:
            if self.max < self.min:
                self.r.append(0)
                self.log += "no dice "
                self.dbg += str(self.max) + " sided dice...?"
                break
            else:
                self.r.append(random.randint(self.min, self.max))
            self.log += str(self.r[-1]) + ": "
            if self.r[-1] >= self.difficulty:
                self.succ += 1
                self.log += "success "
            elif self.r[-1] <= self.subone:
                self.antisucc += 1
                self.log += "subtract "
            if self.r[-1] >= self.explodeon:
                amount += 1
                self.log += "exploding!"
            self.log += "\n"
            if i >= self.maxamount:
                break
            i += 1

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
        if self.difficulty:
            return self.botchformat(self.succ, self.antisucc)
        else:
            return sum(self.r)

    def roll_v(self):  # verbose
        log = ""
        for i in self.r:
            log += str(i) + ", "
        if len(self.r) < 1:
            return " ==> 0"
        log = log[:-2] + " ==> " + str(self.roll_nv())
        return log

    def roll_vv(self):  # very verbose
        log = self.log
        log += "==> " + str(self.roll_nv())
        return log

    def roll_sum(self):  # returns sum nonverbose as int
        return sum(self.r)

    def roll_vsum(self):  # returns sum verbose 
        log = ""
        for n in self.r:
            log += str(self.r) + " + "
        log = log[:-2] + "= " + str(self.roll_sum())

    def roll(self, amount):
        self.roll_next(amount)
        return self.roll_v()
