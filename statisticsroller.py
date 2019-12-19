import collections
import random
import sys
import time
from itertools import combinations
from math import ceil
from typing import Tuple
from generate_dmgmods import tuples, dice5, dice4, dice3, dice2, dice1, selector as selectorq

import pydealer

from NossiPack.WoDParser import WoDParser


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


def selector(sel, addon=""):
    sel = [str(x) for x in sel]
    p = WoDParser({})
    r = p.make_roll(",".join(sel) + "@5" + addon)
    return r.result


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


def plot(data, showsucc=False, showgraph=True, showdmgmods=False, grouped=1):
    success = sum([v for k, v in data.items() if k > 0])
    zeros = sum([v for k, v in data.items() if k == 0])
    botches = sum([v for k, v in data.items() if k < 0])
    total = sum([v for k, v in data.items()])
    pt = total / 100
    width = 1
    if showsucc:
        print("Of the %d rolls, %d where successes, %d where failures and %d where botches, averaging %.2f" % (
            total, success, zeros, botches, (sum([k * v for k, v in data.items()]) / total)))
        print("The percentages are:\n+ : %f.3%%\n0 : %f.3%%\n- : %f.3%%" % (success / pt, zeros / pt, botches / pt))

        barsuc = int((success / pt) / width)
        barbot = int((botches / pt) / width)
        barzer = int(100 / width - barsuc - barbot)
        print("+" * barsuc + "0" * barzer + "-" * barbot)
    if showgraph:

        lowest = min(data.keys())
        highest = max(data.keys())
        width = 1 / 60 * max(int(data[i] / pt) if i in data else 0 for i in range(lowest, highest + 1))
        for i in range(lowest, highest + 1):
            if i == 0 and showsucc:
                print()
            if i not in data.keys():
                data[i] = 0
            if grouped == 1:
                print("%2d : %7.3f%% " % (i, data[i] / pt), end="")
            else:
                print("%2d-%2d : %7.3f%% " % (i * grouped, (i + 1) * grouped - 1, data[i] / pt), end="")
            print("#" * int((data[i] / pt) / width))
            if i == 0 and showsucc:
                print()
    if showdmgmods:
        print("dmgmods(adjusted):")
        print([data[i] / success for i in range(1, highest + 1)])


def run_duel(a, b, c=None, d=None, duration=60):
    if c is None:
        c = a
    if d is None:
        d = a
    successes = collections.defaultdict(lambda: 0)
    i = 0
    time1 = time.time()
    while True:
        i += 1
        delta = selector([a, b]) - selector([c, d])
        delta = min(10, max(delta, 0))
        successes[delta] += 1
        if i % 10000 == 0:
            if time.time() - time1 >= duration:
                break
    print("rolling %s against %s for %.1f seconds" % (str(a) + ", " + str(b), str(c) + ", " + str(d), duration))
    return plot(dict(successes))


def run_sel(sel, addon=""):
    total = []
    for i in range(100000):
        total.append(selector(sel, addon))
    pr = {x: (total.count(x) if x in total else 0) for x in range(min(total), max(total) + 1)}
    plot(pr)
    print(sum(total) / 100000)


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
    successes = collections.defaultdict(lambda: 0)
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
          "Calcination": {"Order": "0", "Matter": "0", "Energy": "10", "Entropy": "11+"},
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
    for length in range(1, len(items) + 1):
        for subset in combinations(items, length):
            if sum(subset) >= target:
                return subset
    return []


def spell_run():
    repeats = 20000
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
    print({k: 100 * v / sum(used_mana.values()) for k, v in used_mana.items()})


def crafting(effort: int, adverse: int, increase_every: int, stats: Tuple[int, int], addon=""):
    progress = 0
    rolls = 0
    level = 0
    increase_adverse_every = increase_every
    p = WoDParser({})
    craftingroll = p.make_roll(",".join((str(x) for x in stats)) + "@5" + addon)
    while True:
        rolls += 1
        if rolls % increase_adverse_every == 0:
            adverse += 1
        result = craftingroll.roll()
        botch = craftingroll.resonance(1)
        if botch > 0:
            #    print(rolls, "BOTCH:", botch)
            adverse += botch
            progress = ceil(progress / 2)
            if botch > 1:
                progress = 0
            if botch > 2:
                adverse += 2
            if botch > 3:
                print("critical BOTCH!", craftingroll.r)
                break
        # print("{:<3}:{:<3}+{:<3}-{:<2}= {:<3}".format(rolls, progress, result, adverse, progress + result - adverse))
        progress += result - adverse

        if progress >= effort:
            level += 1
            #      print("LEVEL UP TO", level, "AFTER", rolls, "ROLLS")
            progress = 0
        elif progress <= 0:
            #       print(rolls, "FAILURE")
            break
    # print("level", level, "with", rolls, "rolls")
    return rolls, level


def run_craft(total: int, effort: int, adverse: int, increase_every: int, sel: Tuple[int, int], addon: str):
    # run_craft(10, 10, 0, 1, (2, 3), "")
    rolls, levels = [], []
    for i in range(total):
        rol, lev = crafting(effort, adverse, increase_every, sel, addon)
        rolls.append(rol)
        levels.append(lev)
    rolls = {x: (rolls.count(x) if x in rolls else 0) for x in range(min(rolls), max(rolls) + 1)}
    levels = {x: (levels.count(x) if x in levels else 0) for x in range(min(levels), max(levels) + 1)}
    nrolls = {int(x / 5): sum(rolls[x + i] if x + i in rolls else 0 for i in range(5)) for x in
              range(0, max(rolls) + 1, 5)}
    print("rolls")
    plot(nrolls, grouped=5)
    print("levels:")
    plot(levels)
    print("averages=", sum([k * v for k, v in rolls.items()]) / len(rolls),
          sum([k * v for k, v in levels.items()]) / len(rolls))


def target_hit_chance(sel):
    t = {}
    for die, freq1 in dice5.items():
        r = selectorq(sel, die)
        freq1 = freq1 / sum(dice5.values())
        skew = dice5 if 18 < r else \
            dice4 if 14 < r else \
                dice3 if 12 < r else \
                    dice2 if 8 < r else \
                        dice1 if 4 < r else None
        if skew is None:
            t[0] = t.get(0, 0) + freq1 * 1  # always the outcome
            continue
        skewtotal = sum(skew.values())
        for die2, freq2 in skew.items():
            freq2 = freq2 / skewtotal
            deviation = die2[-1]
            t[deviation] = t.get(deviation, 0) + freq1 * freq2
    print(sum(t.values()), sel)
    plot(t)
    return t


if __name__ == "__main__":
    import fengraph

    for x in fengraph.chances([1, 2,3,5,4, 2, 1]):
        print(x)
    exit()
    pars = WoDParser()
    msg = "&loop 2,3@5r-1s 9&&loop 3,3@5r2s 2&"
    r = pars.make_roll(msg)
    if isinstance(pars.altrolls, list) and len(pars.altrolls) > 0:
        print(msg + ":\n" + "\n".join(x.name + ": " + x.roll_v() for x in pars.altrolls))
    if r is not None and pars.triggers.get("verbose", None):
        print(msg + ":\n" + r.name + ": " + r.roll_vv(pars.triggers.get("verbose")))
    elif r is not None:
        print(msg + ":\n" + r.roll_v())
