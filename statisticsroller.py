import random
import sys
import NossiPack.WoDParser

import time
from typing import DefaultDict


def d10(amt, diff, ones=True):  # faster than the WoDDice
    succ = 0
    anti = 0
    for i in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if ones and x == 1:
            anti += 1
    if anti > 0:
        if succ > anti:
            return succ - anti
        else:
            if succ > 0:
                return 0
            else:
                return 0 - anti
    else:
        return succ


def d10fnolossguard(amt, diff):  # faster than the normal d10
    succ = 0
    anti = 0
    for i in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if x == 1:
            anti += 1

    return succ - anti


def plot(data):
    success = sum([v for k, v in data.items() if k > 0])
    zeros = sum([v for k, v in data.items() if k == 0])
    botches = sum([v for k, v in data.items() if k < 0])
    total = sum([v for k, v in data.items()])
    pt = total / 100
    print("Of the %d rolls, %d where successes, %d where failures and %d where botches, averaging %.2f" % (
        total, success, zeros, botches, (sum([k * v for k, v in data.items()]) / total)))
    print("The percentages are:\n+ : %f.3%%\n0 : %f.3%%\n- : %f.3%%" % (success / pt, zeros / pt, botches / pt))
    width = 1
    barsuc = int((success / pt) / width)
    barbot = int((botches / pt) / width)
    barzer = int(100 / width - barsuc - barbot)
    print("+" * barsuc + "0" * barzer + "-" * barbot)
    lowest = min(data.keys())
    highest = max(data.keys())
    for i in range(lowest, highest):
        if i == 0:
            print()
        print("%2d : %7.3f%% " % (i, data[i] / pt), end="")
        print("#" * int((data[i] / pt) / width))
        if i == 0:
            print()


def run():
    duration = 1
    amount = 5
    difficulty = 6
    roller = d10
    if len(sys.argv) > 2:
        duration = float(sys.argv[1])
        amount = int(sys.argv[2])
        difficulty = int(sys.argv[3])
        if len(sys.argv) > 3:
            roller = d10fnolossguard
    successes = DefaultDict[lambda: 0]
    i = 0
    time1 = time.time()
    while True:
        i += 1
        successes[roller(amount, difficulty)] += 1
        if i % 10000 == 0:
            if time.time() - time1 >= duration:
                break
    print("rolling %d dice against %d for %.1f seconds" % (amount, difficulty, duration))
    plot(dict(successes))


def count_sets(dice_throw, specific=None):
    dice_throw = sorted(dice_throw) + [None]
    m = []
    runlength = 1
    for x in range(1, len(dice_throw)):
        if dice_throw[x] == dice_throw[x - 1] and (dice_throw[x] == specific if specific else True):
            runlength += 1
        else:
            m.append(runlength)
            runlength = 1
    return " ".join(str(n) for n in sorted(m))


res = {}
a = []
t = time.time()
i = 0
j = 0
hits = 0
crits = {x: 0 for x in range(21)}
onecount = 0
for weenie_throw in [1, 2, 3, 4, 5, 6, 7, 7, 7, 7]:
    for current_throw in [(a + 1, b + 1, c + 1, d + 1, e + 1)
                          for a in range(10)
                          for b in range(10)
                          for c in range(10)
                          for d in range(10)
                          for e in range(10)]:
        current_throw = sorted(current_throw)
        r = count_sets(current_throw, 7)
        res[r] = res.get(r, 0) + 1
        i += 1
        if 1 in current_throw:
            onecount += 1
        if i % 10000 == 0:
            print(i / 10000, "%")
        if current_throw[4]*2 <= weenie_throw*2:
            hits += 1

print(100* hits / i, 100* onecount / i)
print("groupings")
for k in sorted(res.keys()):
    print((k + "                   ")[:10] + ": " + str(res[k] * 100 / i) + "%")
print(time.time() - t, "seconds")
exit()

# run()
p = NossiPack.WoDParser({})
r = p.make_roll("1,2@5")

rep = 1
t = time.time()
import sys

last = 0
for RER in range(0, 3):
    val = 0
    for i in range(rep):
        r = p.make_roll("1,1@5R" + str(RER))
        val += r.result
        if (i / rep) * 100 == int((i / rep) * 100):
            print(int((i / rep) * 100), "%")
    if abs(last - val) < 2:
        print(last - val)
        break
    else:
        last = val
print(RER)
print(round(val / rep, 2))
print("seconds:", time.time() - t)
