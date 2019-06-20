import random
import sys
import time
from itertools import combinations
import collections

from plotly.offline import offline

from NossiPack.WoDParser import WoDParser
import plotly.graph_objs as go
import plotly.plotly as py

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


def selector(sel):
    sel = [str(x) for x in sel]
    p = WoDParser({})
    r = p.make_roll(",".join(sel) + "@5")
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
        if i not in data.keys():
            data[i] = 0
        print("%2d : %7.3f%% " % (i, data[i] / pt), end="")
        print("#" * int((data[i] / pt) / width))
        if i == 0:
            print()
    print("dmgmods(adjusted):")
    for i in range(1, highest):
        print(data[i] / success, end=" ")
    print()


def run_duel():
    successes = collections.defaultdict(lambda: 0)
    i = 0
    time1 = time.time()
    duration = 60
    while True:
        i += 1
        delta = selector([2, 3]) - selector([2, 3])
        delta = delta if delta > 0 else 0
        successes[delta] += 1
        if i % 10000 == 0:
            if time.time() - time1 >= duration:
                break
    print("rolling 3,3 against 3,3 for %.1f seconds" % duration)
    plot(dict(successes))


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


def modify_dmg(modifiers, dmgstring, type, armor):
    dmg = [int(x) for x in dmgstring.split("|") if x.strip()]
    total = 0
    effectivedmg = []
    for d in dmg:
        if type == "Stechen":
            effectivedmg.append(0 if d <= armor else d)
        elif type == "Schlagen":
            e = d - int(armor / 2)
            effectivedmg.append(e if e > 0 else 0)
        else:
            e = d - armor
            effectivedmg.append(e if e > 0 else 0)

    for i, d in enumerate(effectivedmg):
        total += d * modifiers[i]
    return total


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
    repeats = 0
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


# run_duel()

experimental_modifiers = [0.17202107691263938, 0.1613333634862842, 0.14626744159750332, 0.12806712046857685,
                          0.10685904249304598, 0.08603089169813881, 0.06636966010086162, 0.04910106515298854,
                          0.033171261222551394, 0.050770030982156995]

dmgraw = """
###Kurzschwert
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |   
| [Stechen](damage#p-stechen)      | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 |   
| [Schneiden](weapons#c-schneiden) | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 7 |   
| [Schlagen](damage#b-stumpf)      | 2 | 2 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 |   


###Langschwert
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 5 | 5 | 6 | 6 | 7 | 8| 9| 10| 11 | 12 |   
| [Stechen](damage#p-stechen)      | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 | 7 | 8 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 7 | 8 |   
| [Schlagen](damage#b-stumpf)      | 3 | 4 | 4 | 5 | 5 | 6 | 7 | 8 | 9 | 10 |   

###Dolch
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 1 | 2 | 3 | 4 | 6 | 8 | 10 | 12 | 14 | 16 |   
| [Stechen](damage#p-stechen)      | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10| 12 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5  |   
| [Schlagen](damage#b-stumpf)      | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 3 | 10 |  

###Hammer
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  
| [Stechen](damage#p-stechen)      | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Schneiden](weapons#c-schneiden) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| [Schlagen](damage#b-stumpf)      | 4 | 4 | 5 | 5 | 6 | 7 | 8 | 10 | 12 | 15 | 

###Axt
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 6 | 6 | 7 | 7 | 8 | 8 | 9 | 11 | 13 | 15 |   
| [Stechen](damage#p-stechen)      | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Schneiden](weapons#c-schneiden) | 2 | 2 | 3 | 3 | 4 | 5 | 6 | 7 | 8 | 10 |
| [Schlagen](damage#b-stumpf)      | 2 | 3 | 4 | 5 | 6 | 6 | 6 | 6 | 6 | 6 | 

###Säbel
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |   
| [Stechen](damage#p-stechen)      | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 5 | 6 | 7 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |    
| [Schlagen](damage#b-stumpf)      | 3 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 |  

###Kurzspeer
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Stechen](damage#p-stechen)      | 3 | 4 | 5 | 5 | 6 | 7 | 8 | 9 | 11 | 13 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5  |   
| [Schlagen](damage#b-stumpf)      | 2 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 | 7 |  """

weapons = {}
for dmgsect in dmgraw.split("###"):
    if not dmgsect.strip():
        continue
    weapon = dmgsect[:dmgsect.find("\n")].strip()
    weapons[weapon] = {}
    for dmgline in dmgsect.split("\n"):
        if "Wert" in dmgline or "---" in dmgline or len(dmgline) < 50:
            continue
        dmgtype = dmgline[dmgline.find("[") + 1:dmgline.find("]")].strip()
        weapons[weapon][dmgtype] = modify_dmg(experimental_modifiers, dmgline[35:], dmgtype, 3)

weaponnames = list(weapons.keys())
types = list(weapons[weaponnames[0]].keys())

a = []
for t in types:
    a.append(
        go.Bar(x=weaponnames,
               y=[weapons[x][t] for x in weaponnames],
               name=t)
    )
offline.plot(a, include_mathjax=False, image_filename="weapontypes")
