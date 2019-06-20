import random
import sys
import time
from itertools import combinations
from typing import DefaultDict

import pydealer


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


def process_hand(stack: pydealer.Stack):
    transl = {"D": "Order", "C": "Matter", "H": "Energy", "S": "Entropy"}
    result = {"Order": [], "Matter": [], "Energy": [], "Entropy": []}
    for c in stack:
        result[transl[c.abbrev[-1]]].append(11 if (c.abbrev[:-1] == "A") else (
            int(c.abbrev[:-1]) if c.abbrev[:-1].isdigit() else 10))

    return result


spells = {"Bend": {"Order": "3+", "Matter": "4+", "Energy": "0", "Entropy": "3+"},
          "Morph": {"Order": "9+", "Matter": "9+", "Energy": "0", "Entropy": "0"},
          "Calcify": {"Order": "0", "Matter": "4+", "Energy": "4+", "Entropy": "0"},
          "Calcination": {"Order": "0", "Matter": "0", "Energy": "8", "Entropy": "11"},
          "Solution": {"Order": "10", "Matter": "7", "Energy": "0", "Entropy": "0+"},
          "Separation": {"Order": "9", "Matter": "0+", "Energy": "1+", "Entropy": "6"},
          "Conjunction": {"Order": "9", "Matter": "0+", "Energy": "1+", "Entropy": "6"},
          "Putrefaction": {"Order": "0", "Matter": "14+", "Energy": "14+", "Entropy": "0"},
          "Sublimation": {"Order": "0", "Matter": "9+", "Energy": "0+", "Entropy": "12"},
          "Multiplication": {"Order": "10", "Matter": "0", "Energy": "0", "Entropy": "10"},
          "Buoyancy": {"Order": "0", "Matter": "5+", "Energy": "10+", "Entropy": "0"},
          "Knallpulver": {"Order": "9+", "Matter": "0", "Energy": "0", "Entropy": "9"},
          "Schreipulver": {"Order": "0", "Matter": "9+", "Energy": "0", "Entropy": "9"},
          "Griffpulver": {"Order": "11", "Matter": "16+", "Energy": "0", "Entropy": "0"},
          "Atemmaske": {"Order": "11", "Matter": "0", "Energy": "0", "Entropy": "8+"},
          "Leuchtpulver": {"Order": "0", "Matter": "11", "Energy": "16+", "Entropy": "0"},
          "Schnellfackel": {"Order": "0", "Matter": "0", "Energy": "1+", "Entropy": "1+"},
          "Durstsand": {"Order": "17", "Matter": "10+", "Energy": "0", "Entropy": "0"},

          "Feuersee": {"Order": "0", "Matter": "0", "Energy": "5+", "Entropy": "5+"},
          "Pandemonium": {"Order": "0", "Matter": "0", "Energy": "0", "Entropy": "11", "Any": "20"},
          "Statische Entladung": {"Order": "5+", "Matter": "0", "Energy": "5+", "Entropy": "0"},
          "Ordnen": {"Order": "5+", "Matter": "0", "Energy": "0", "Entropy": "0"},
          "Gefrieren": {"Order": "3+", "Matter": "3+", "Energy": "0", "Entropy": "0"},
          "Magnetisieren": {"Order": "3+", "Matter": "0", "Energy": "3+", "Entropy": "0"},
          "Essenz des Glücks": {"Order": "3+", "Matter": "0", "Energy": "0", "Entropy": "3+"},
          "Härten": {"Order": "0", "Matter": "5+", "Energy": "0", "Entropy": "0"},
          "Beschleunigen": {"Order": "0", "Matter": "3+", "Energy": "3+", "Entropy": "0"},
          "Verfall": {"Order": "0", "Matter": "3+", "Energy": "0", "Entropy": "3+"},
          "Statischer Schlag": {"Order": "0", "Matter": "0", "Energy": "5+", "Entropy": "0"},
          "Destabilisieren": {"Order": "0", "Matter": "0", "Energy": "3+", "Entropy": "3+"},
          "Änderung": {"Order": "0", "Matter": "0", "Energy": "0", "Entropy": "5+"}
          }


def subsetsum(items, target):
    for length in range(1, len(items)):
        for subset in combinations(items, length):
            if sum(subset) == target:
                return subset
    return []


def subsetsumany(items, target):
    for length in range(1, len(items)+1):
        for subset in combinations(items, length):
            if sum(subset) >= target:
                return subset
    return []


repeats = 1000000
total = 0
casted_spells = {x: 0 for x in spells.keys()}

used_mana = {"Order": 0, "Matter": 0, "Energy": 0, "Entropy": 0, "Any": 0}

for repeat in range(repeats):
    deck = pydealer.Deck()
    deck.shuffle()
    hand = deck.deal(6)
    hand = process_hand(hand)
    casted = 0
    # hand = {"Order": [9, 5], "Matter": [2], "Energy": [], "Entropy": [10, 11]}

    if 1000 * repeat / repeats % 10 == 0:
        print(int(100 * repeat / repeats), "%")
    # print("O {} M {} E {} N {}".format(hand["Order"], hand["Matter"], hand["Energy"], hand["Entropy"]))
    for s in spells.keys():
        casteable = True
        for x in spells[s].keys():  # Order, Matter, Energy, Entropy
            code = spells[s][x]
            if code == "0":
                continue
            if code[-1] == "+":
                if x == "Any":
                    if int(code[:-1]) > sum(hand[i] for i in hand.keys()):
                        casteable = False
                        break
                else:
                    ssum = subsetsumany(hand[x], int(code[:-1]))
                    if not ssum:
                        casteable = False
                        break
                    else:
                        used_mana[x] += sum(ssum)
            else:
                if x == "Any":
                    ssum = subsetsum([a for magictype in hand.keys() for a in hand[magictype]], int(code))
                    if not ssum:
                        casteable = False
                        break
                    else:
                        used_mana[x] += int(code)

                else:
                    ssum = subsetsum(hand[x], int(code))
                    if not ssum:
                        casteable = False
                        break
                    else:
                        used_mana[x] += int(code)
        if casteable:
            casted += 1
            casted_spells[s] += 1
    total += casted
    # print()


print(total / repeats)
for x in sorted(casted_spells.items(), key=lambda k: k[1]):
    print("{:<20} {:>5.1f}%".format(x[0], 100 * casted_spells[x[0]] / repeats))
print(used_mana)
