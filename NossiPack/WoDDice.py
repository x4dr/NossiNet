import random


class WoDDice(object):
    def __init__(self, maxroll=10, minroll=1):
        self.min = minroll
        self.max = maxroll
        self.r = []
        self.log = ""
        self.succ = 0
        self.antisucc = 0
        self.infinity = max(100, maxroll * 10)

    def roll_next(self, amount, difficulty=6, subone=1, explodeon=0):
        if explodeon <= self.min:
            explodeon = self.max + 1
        if self.infinity < amount:
            self.infinity = amount
        i = 0
        log = ""
        r = []
        successes = 0
        antisuccess = 0
        while i < amount:
            r.append(random.randint(self.min, self.max))
            log += str(r[-1]) + ": "
            if r[-1] >= difficulty:
                successes += 1
                log += "success"
            elif r[-1] <= subone:
                antisuccess += 1
                log += "subtract"
            if r[-1] >= explodeon:
                amount += 1
                log += ", exploding!"
            log += "\n"
            if i >= self.infinity:
                break
            i += 1

            self.r = r
            self.log = log
            self.succ = successes
            self.antisucc = antisuccess

    @staticmethod
    def botchformat(succ, antisucc):
        if succ > 0:
            if succ <= antisucc:
                return 0
            else:
                return succ
        else:
            return antisucc

    def roll_nv(self):
        return self.botchformat(self.succ, self.antisucc)

    def roll_v(self):
        res = ""
        for i in self.r:
            res += str(i) + ", "
        res = res[:-2] + " ==> " + str(self.botchformat(self.succ, self.antisucc))
        return res

    def roll_vv(self):
        log = self.log
        log += "==> " + str(self.botchformat(self.succ, self.antisucc))
        return log

    def roll(self, amount, difficulty=6, subone=1, explodeon=0):
        self.roll_next(amount, difficulty, subone, explodeon)
        return self.roll_v()
