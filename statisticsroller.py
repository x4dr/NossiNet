"""Legacy dice statistics and simulation utilities (reference code, do not import)."""

import collections
import random
import sys
import time
from collections.abc import Callable
from itertools import combinations
from typing import Any

# This code is only here for reference to various explorative legacy coding sessions. Do not Import.
from math import ceil

from gamepack.DiceParser import DiceParser
from gamepack.fasthelpers import plot


def selector(sel: list[Any], addon: str = "") -> Any:
    """Roll dice using a DiceParser selector string."""
    sel = [str(x) for x in sel]
    p = DiceParser({})
    r = p.make_roll(",".join(sel) + "@5" + addon)
    return r.result


def d10fnolossguard(amt: int, diff: int) -> int:
    """Roll amt d10 dice against diff, returning successes minus ones (no loss guard)."""
    succ = 0
    anti = 0
    for _ in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if x == 1:
            anti += 1

    return succ - anti


def run_duel(a: int, b: int, c: int | None = None, d: int | None = None, duration: int | float = 60) -> Any:
    """Simulate a duel between two combatants and plot the results.

    Args:
        a: First attacker stat.
        b: First defender stat.
        c: Second attacker stat (defaults to a).
        d: Second defender stat (defaults to b).
        duration: Maximum simulation time in seconds.

    """
    if c is None:
        c = a
    if d is None:
        d = b

    weapon1 = [0, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8]  # shortsword
    weapon2 = [0, 3, 3, 3, 3, 3, 3, 7, 7, 7, 7]  # hammer => blunt
    successes: collections.defaultdict[int, int] = collections.defaultdict(lambda: 0)
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


def run_sel(sel: list[Any], addon: str = "") -> None:
    """Run selector 100,000 times and plot the result distribution."""
    total = []
    for _ in range(100000):
        total.append(selector(sel, addon))
    pr = {x: (total.count(x) if x in total else 0) for x in range(min(total), max(total) + 1)}
    plot(pr)
    print(sum(total) / 100000)


def run() -> None:
    """Run a dice simulation for a given duration and plot results."""
    duration: float = 1.0
    amount = 5
    difficulty = 6
    roller: Callable[..., int] = d10
    if len(sys.argv) > 2:
        duration = float(sys.argv[1])
        amount = int(sys.argv[2])
        difficulty = int(sys.argv[3])
        if len(sys.argv) > 3:
            roller = d10fnolossguard
    successes: collections.defaultdict[int, int] = collections.defaultdict(lambda: 0)
    i = 0
    time1 = time.time()
    while True:
        i += 1
        successes[roller(amount, difficulty)] += 1
        if i % 10000 == 0 and time.time() - time1 >= duration:
            break
    print(f"rolling {amount:d} dice against {difficulty:d} for {duration:.1f} seconds")
    plot(dict(successes))


def get_multiples(xs: list[int]) -> list[tuple[int, int]]:
    """Find consecutive duplicate values in a sorted list.

    Returns:
        List of (value, count) tuples for values appearing more than once.

    """
    ys = sorted(xs)
    m: list[tuple[int, int]] = []
    i = 1
    for n in range(1, len(ys)):
        if ys[n] == ys[n - 1]:
            i += 1
        elif i > 1:
            m.append((ys[n - 1], i - 1))
            i = 1
    if i > 1:
        m.append((ys[-1], i - 1))
    return m


def subsetsum(items: list[int], target: int) -> tuple[int, ...]:
    """Find the smallest subset of items that sums exactly to target."""
    for length in range(1, len(items)):
        for subset in combinations(items, length):
            if sum(subset) == target:
                return subset
    return ()


def subsetsumany(items: list[int], target: int) -> tuple[int, ...]:
    """Find the smallest subset of items that sums to at least target."""
    for length in range(1, len(items) + 1):
        for subset in combinations(items, length):
            if sum(subset) >= target:
                return subset
    return ()


def crafting(
    effort: int,
    adverse: int,
    increase_every: int,
    stats: tuple[int, int],
    addon: str = "",
) -> tuple[int, int]:
    """Simulate a crafting process, returning total rolls and levels gained.

    Args:
        effort: Effort threshold per level.
        adverse: Starting adverse value.
        increase_every: Frequency at which adverse increases.
        stats: Stat tuple for the crafting roll.
        addon: Optional roll addon string.

    Returns:
        Tuple of (rolls, level).

    """
    progress = 0
    rolls = 0
    level = 0
    increase_adverse_every = increase_every
    p = DiceParser({})
    craftingroll = p.make_roll(",".join(str(x) for x in stats) + "@5" + addon)
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
        progress += (result or 0) - adverse

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
    sel: tuple[int, int],
    addon: str,
) -> None:
    """Run the crafting simulation multiple times and plot the aggregated results."""
    rolls, levels = [], []
    for _i in range(total):
        rol, lev = crafting(effort, adverse, increase_every, sel, addon)
        rolls.append(rol)
        levels.append(lev)
    roll_counts: dict[int, int] = {x: (rolls.count(x) if x in rolls else 0) for x in range(min(rolls), max(rolls) + 1)}
    level_counts: dict[int, int] = {
        x: (levels.count(x) if x in levels else 0) for x in range(min(levels), max(levels) + 1)
    }
    nrolls = {int(x / 5): sum(roll_counts.get(x + i, 0) for i in range(5)) for x in range(0, max(roll_counts) + 1, 5)}
    print("rolls")
    plot(nrolls, grouped=1)
    print("levels:")
    plot(level_counts)
    print(
        "averages=",
        sum(k * v for k, v in roll_counts.items()) / len(rolls),
        sum(k * v for k, v in level_counts.items()) / len(rolls),
    )


def bowdpstest(bowmana_rate: int, draw: int, aim: int, fire: int, quickdraw: int, quickaim: int, quickfire: int) -> int:
    """Simulate a bow DPS rotation over 20 time units and return total damage."""
    bowmana_max = bowmana_rate * 4
    bowmana = bowmana_max
    state = 0
    transitions = [draw, aim, fire, bowmana_max * 2]
    quickperks = [quickdraw, quickaim, quickfire]
    damage = 0
    for _i in range(20):
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


exp_t: list[int] = []


def experiments(maxtime: int, stats: list[str], discoveries: int = 0) -> int:
    """Simulate an experiment research process over maxtime steps."""
    p = DiceParser({})
    r = p.make_roll(",".join(stats) + "@5")
    status = 0
    for i in range(maxtime):
        status += r.roll_next().result or 0
        if status >= 10 + i * 2 + discoveries:
            status -= 10 + i * 2 + discoveries
            discoveries += 1
        if len(exp_t) <= i:
            exp_t.append(discoveries)
        else:
            exp_t[i] += discoveries
    return discoveries


def studies(
    modifier: int, cumulative: bool, stats: list[str], discoveries: int, capacity: int, quality: int = 0
) -> int:
    """Simulate a study research process with given capacity and modifiers."""
    p = DiceParser({})
    r = p.make_roll(",".join(stats) + "@5R" + str(quality))
    status = 0
    running_mod = 0
    capacity -= discoveries // 2  # capacity is rounded up by rounding discoveries down
    while capacity > 0:
        capacity -= 1
        status += r.roll_next().result or 0
        if cumulative:
            status += running_mod  # running mod is 0 for first operation
            running_mod += modifier
        else:
            status += modifier
        if status >= 15:
            status -= 15
            discoveries += 1
    return discoveries


def batch(duration: float, func: Callable[..., int], params: tuple[Any, ...]) -> None:
    """Run a function repeatedly for the given duration and plot result frequencies."""
    res: collections.defaultdict[int, int] = collections.defaultdict(lambda: 0)
    time1 = time.time()
    i = 0
    while True:
        i += 1
        res[func(*params)] += 1
        if i % 10 == 0 and time.time() - time1 >= duration:
            break
    print(
        f"rolling dice for {time.time() - time1} seconds yielded {sum(res.values())} results",
    )
    print(plot(dict(res)))
    print(f"avg: {sum(k * v for k, v in res.items()) / sum(res.values())}")


def comboresearch(
    experimentfirst: bool,
    maxtime: int,
    discoveries: int,
    stats: list[str],
    cumulative: bool,
    modifier: int,
    capacity: int,
    quality: int,
) -> int:
    """Run a combined experiments and studies research simulation."""
    if experimentfirst:
        discoveries = experiments(maxtime, stats, discoveries)
    discoveries = studies(modifier, cumulative, stats, discoveries, capacity, quality)
    if not experimentfirst:
        discoveries = experiments(maxtime, stats, discoveries)
    return discoveries


def d10(amt: int, diff: int, *, ones: bool = True) -> int:
    """Roll amt d10 dice against diff with optional ones tracking (faster than DiceParser)."""
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
