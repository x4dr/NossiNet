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


def get_multiples(xs):
    ys = sorted(xs) + [None]
    m = []
    run = 1
    for n in range(1, len(ys)):
        if ys[n] == ys[n - 1]:
            run += 1
        else:
            if run > 1:
                m.append((ys[n - 1], run - 1))
                run = 1
    return m


# run()
t = time.time()
p = NossiPack.WoDParser({})
r1 = p.make_roll("1,1@5")
# r2 = p.make_roll("3,5@3R3")
val1 = 0
mul = [0, 0, 0, 0]
rep = 1000000

for i in range(rep):
    r = [random.randint(1,10)for x in range(5)]
    for m in get_multiples(r):
        mul[m[1] - 1] += 1
    # val2 += 1 if sum(1 for x, y in multiples if y ==1) else 0
    # val3 += 1 if sum(1 for x, y in multiples if y ==2) else 0
    # val4 += 1 if sum(1 for x, y in multiples if y ==3) else 0
    # val5 += 1 if sum(1 for x, y in multiples if y ==4) else 0

print("avg", val1 / rep)
print("group of any 2", 100 * mul[0] / rep)
print("group of any 3", 100 * mul[1] / rep)
print("group of any 4", 100 * mul[2] / rep)
print("group of any 5", 100 * mul[3] / rep)
print(time.time() - t)
