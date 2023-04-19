import collections
import random
import sys
import time
from itertools import combinations

from gamepack.fasthelpers import plot
from math import ceil
from typing import Tuple

from gamepack.DiceParser import DiceParser


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

        if i % 10 == 0 and time.time() - time1 >= duration:
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
        if i % 10000 == 0 and time.time() - time1 >= duration:
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
                if quickperks[state - 1] and bowmana >= transitions[state - 1]:
                    bowmana -= transitions[state]
                    continue  # getto goto what is wrong with me
            break
    return damage


exp_t = []


def experiments(maxtime, stats, discoveries=0):
    p = DiceParser({})
    r = p.make_roll(",".join(stats) + "@5")
    status = 0
    for i in range(maxtime):
        status += r.roll_next().result
        if status >= 10 + i * 2 + discoveries:
            status -= 10 + i * 2 + discoveries
            discoveries += 1
        if len(exp_t) <= i:
            exp_t.append(discoveries)
        else:
            exp_t[i] += discoveries
    return discoveries


def studies(modifier, cumulative, stats, discoveries, capacity, quality=0):
    p = DiceParser({})
    r = p.make_roll(",".join(stats) + "@5R" + str(quality))
    status = 0
    running_mod = 0
    capacity -= discoveries // 2  # capacity is rounded up by rounding discoveries down
    while capacity > 0:
        capacity -= 1
        status += r.roll_next().result
        if cumulative:
            status += running_mod  # running mod is 0 for first operation
            running_mod += modifier
        else:
            status += modifier
        if status >= 15:
            status -= 15
            discoveries += 1
    return discoveries


def batch(duration, func, params):
    res = collections.defaultdict(lambda: 0)
    time1 = time.time()
    i = 0
    while True:
        i += 1
        res[func(*params)] += 1
        if i % 10 == 0 and time.time() - time1 >= duration:
            break
    print(
        f"rolling dice for {time.time() - time1} seconds yielded {sum(res.values())} results"
    )
    print(plot(dict(res)))
    print(f"avg: {sum(k * v for k, v in res.items()) / sum(res.values())}")


def comboresearch(
    experimentfirst,
    maxtime,
    discoveries,
    stats,
    cumulative,
    modifier,
    capacity,
    quality,
):
    if experimentfirst:
        discoveries = experiments(maxtime, stats, discoveries)
    discoveries = studies(modifier, cumulative, stats, discoveries, capacity, quality)
    if not experimentfirst:
        discoveries = experiments(maxtime, stats, discoveries)
    return discoveries


def d10(amt, diff, ones=True):  # faster than the Dice
    succ = 0
    anti = 0
    for _ in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if ones and x == 1:
            anti += 1
    if anti > 0:
        if succ > anti:
            return succ - anti
        if succ > 0:
            return 0
        return 0 - anti
    return succ
