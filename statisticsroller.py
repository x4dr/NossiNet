import collections
import random
import sys
import time
from itertools import combinations
from math import ceil
from typing import Tuple

import pydealer

from NossiPack.DiceParser import DiceParser
from NossiPack.fengraph import plot
from NossiPack.krypta import d10


def selector(sel, addon=""):
    sel = [str(x) for x in sel]
    p = DiceParser({})
    r = p.make_roll(",".join(sel) + "@5" + addon)
    return r.result


def d10fnolossguard(amt, diff):  # faster than the normal d10
    succ = 0
    anti = 0
    for _ in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if x == 1:
            anti += 1

    return succ - anti


def run_duel(a, b, c=None, d=None, duration=60):
    if c is None:
        c = a
    if d is None:
        d = b

    weapon1 = [0, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8]  # shortsword
    weapon2 = [0, 3, 3, 3, 3, 3, 3, 7, 7, 7, 7]  # hammer => blunt
    successes = collections.defaultdict(lambda: 0)
    i = 0
    time1 = time.time()
    while True:
        i += 1
        lp1 = lp2 = 20
        armor1 = armor2 = 0
        shield1 = 0
        shield2 = 0
        stun = 0
        while lp1 > 0 and lp2 > 0:
            r1 = selector([a, b]) - stun
            r2 = selector([c, d])
            off1 = r1
            off2 = r2
            def1 = r1 + shield1
            def2 = r2 + shield2
            stun = 0
            if off1 > def2:
                delta = off1 - def2
                dmg = weapon1[max(0, min(delta, 10))]  # shield does not add damage
                dmg = max(dmg - armor2, 0)
                lp2 -= dmg
                # hack damage
            if off2 > def1:
                delta = off2 - def1
                dmg = weapon2[max(0, min(delta, 10))]
                stun = round(dmg / 2)
                # blunt damage
                dmg = max(dmg - round(armor1 / 2), 0)
                lp1 -= dmg
        if lp1 > lp2:
            successes[0] += 1

        if lp1 < lp2:
            successes[1] += 1

        if i % 10 == 0:
            if time.time() - time1 >= duration:
                break
    print(f"rolling {a},{b} against {c},{d} for {time.time() - time1} seconds")
    print(sum(successes.values()))
    return plot(dict(successes))


def run_sel(sel, addon=""):
    total = []
    for _ in range(100000):
        total.append(selector(sel, addon))
    pr = {
        x: (total.count(x) if x in total else 0)
        for x in range(min(total), max(total) + 1)
    }
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
    print(
        "rolling %d dice against %d for %.1f seconds" % (amount, difficulty, duration)
    )
    plot(dict(successes))


def get_multiples(xs):
    ys = sorted(xs) + [None]
    m = []
    i = 1
    for n in range(1, len(ys)):
        if ys[n] == ys[n - 1]:
            i += 1
        else:
            if i > 1:
                m.append((ys[n - 1], i - 1))
                i = 1
    return m


def process_hand(stack: pydealer.Stack):
    transl = {"D": "Order", "C": "Matter", "H": "Energy", "S": "Entropy"}
    result = {"Order": [], "Matter": [], "Energy": [], "Entropy": []}
    for c in stack:
        result[transl[c.abbrev[-1]]].append(
            11
            if (c.abbrev[:-1] == "A")
            else (int(c.abbrev[:-1]) if c.abbrev[:-1].isdigit() else 10)
        )

    return result


spells = {
    "Bend": {"Order": "3+", "Matter": "4+", "Energy": "0", "Entropy": "3+"},
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
    "Pandemonium": {
        "Order": "0",
        "Matter": "0",
        "Energy": "0",
        "Entropy": "11",
        "Any": "20",
    },
    "Statische Entladung": {
        "Order": "5+",
        "Matter": "0",
        "Energy": "5+",
        "Entropy": "0",
    },
    "Ordnen": {"Order": "5+", "Matter": "0", "Energy": "0", "Entropy": "0"},
    "Gefrieren": {"Order": "3+", "Matter": "3+", "Energy": "0", "Entropy": "0"},
    "Magnetisieren": {"Order": "3+", "Matter": "0", "Energy": "3+", "Entropy": "0"},
    "Essenz des Glücks": {"Order": "3+", "Matter": "0", "Energy": "0", "Entropy": "3+"},
    "Härten": {"Order": "0", "Matter": "5+", "Energy": "0", "Entropy": "0"},
    "Beschleunigen": {"Order": "0", "Matter": "3+", "Energy": "3+", "Entropy": "0"},
    "Verfall": {"Order": "0", "Matter": "3+", "Energy": "0", "Entropy": "3+"},
    "Statischer Schlag": {"Order": "0", "Matter": "0", "Energy": "5+", "Entropy": "0"},
    "Destabilisieren": {"Order": "0", "Matter": "0", "Energy": "3+", "Entropy": "3+"},
    "Änderung": {"Order": "0", "Matter": "0", "Energy": "0", "Entropy": "5+"},
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
    casted_spells = {x: 0 for x in spells}

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
        # print("O {} M {} E {} N {}".
        # format(hand["Order"], hand["Matter"], hand["Energy"], hand["Entropy"]))
        for sname, sp in spells.items():
            casteable = True
            for x, xi in sp.items():  # Order, Matter, Energy, Entropy
                code = xi
                if code == "0":
                    continue
                if code[-1] == "+":
                    if x == "Any":
                        if int(code[:-1]) > sum(hand.values()):
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
                        ssum = subsetsum(
                            [
                                a
                                for magictype, contained in hand.items()
                                for a in contained
                            ],
                            int(code),
                        )
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
                casted_spells[sname] += 1
        total += casted
        # print()

    print(total / repeats)
    for x in sorted(casted_spells.items(), key=lambda k: k[1]):
        print("{:<20} {:>5.1f}%".format(x[0], 100 * casted_spells[x[0]] / repeats))
    print({k: 100 * v / sum(used_mana.values()) for k, v in used_mana.items()})


def crafting(
    effort: int, adverse: int, increase_every: int, stats: Tuple[int, int], addon=""
):
    progress = 0
    rolls = 0
    level = 0
    increase_adverse_every = increase_every
    p = DiceParser({})
    craftingroll = p.make_roll(",".join((str(x) for x in stats)) + "@5" + addon)
    while True:
        rolls += 1
        if rolls % increase_adverse_every == 0:
            adverse += 1
        result = craftingroll.roll(5)
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
        # print("{:<3}:{:<3}+{:<3}-{:<2}= {:<3}".
        # format(rolls, progress, result, adverse, progress + result - adverse))
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


def run_craft(
    total: int,
    effort: int,
    adverse: int,
    increase_every: int,
    sel: Tuple[int, int],
    addon: str,
):
    rolls, levels = [], []
    for i in range(total):
        rol, lev = crafting(effort, adverse, increase_every, sel, addon)
        rolls.append(rol)
        levels.append(lev)
    rolls = {
        x: (rolls.count(x) if x in rolls else 0)
        for x in range(min(rolls), max(rolls) + 1)
    }
    levels = {
        x: (levels.count(x) if x in levels else 0)
        for x in range(min(levels), max(levels) + 1)
    }
    nrolls = {
        int(x / 5): sum(rolls[x + i] if x + i in rolls else 0 for i in range(5))
        for x in range(0, max(rolls) + 1, 5)
    }
    print("rolls")
    plot(nrolls, grouped=1)
    print("levels:")
    plot(levels)
    print(
        "averages=",
        sum(k * v for k, v in rolls.items()) / len(rolls),
        sum(k * v for k, v in levels.items()) / len(rolls),
    )


def bowdpstest(bowmana_rate, draw, aim, fire, quickdraw, quickaim, quickfire):
    bowmana_max = bowmana_rate * 4
    bowmana = bowmana_max
    state = 0
    transitions = [draw, aim, fire, bowmana_max * 2]
    quickperks = [quickdraw, quickaim, quickfire]
    damage = 0
    for i in range(20):
        bowmana += bowmana_rate
        bowmana = min(bowmana_max, bowmana)
        while True:
            if bowmana >= transitions[state]:
                bowmana -= transitions[state]
                state += 1
                if state >= len(transitions) - 1:
                    damage += 1
                    state = 0
                if quickperks[state - 1]:
                    if bowmana >= transitions[state - 1]:
                        bowmana -= transitions[state]
                        continue  # getto goto what is wrong with me
            break
    return damage


if __name__ == "__main__":
    run_duel(2, 3, 2, 3, 60)
