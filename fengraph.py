import io
import json
import math
from _md5 import md5
from math import ceil

import numpy
import requests
import ast

from scipy.integrate import quad
from scipy.interpolate import interp1d
from scipy.optimize import fsolve


def modify_dmg(specific_modifiers, dmgstring, damage_type, armor):
    dmg = [[int(y) for y in x.split(";")] for x in dmgstring.split("|") if x.strip()]
    total_damage = 0
    effectivedmg = []
    for damage_instance in dmg:
        if len(damage_instance) > 1:
            effective_dmg = damage_instance[0] - max(0, armor - damage_instance[1])
            effectivedmg.append(effective_dmg if effective_dmg > 0 else 0)
        else:
            damage_instance = damage_instance[0]
            if damage_type == "Stechen":
                effectivedmg.append(0 if damage_instance <= armor else math.ceil(damage_instance / 2))
            elif damage_type == "Schlagen":
                effective_dmg = damage_instance - int(armor / 2)
                effectivedmg.append(effective_dmg if effective_dmg > 0 else 0)
            elif damage_type == "Schneiden":
                effective_dmg = damage_instance - armor
                effectivedmg.append(effective_dmg + ceil(effective_dmg / 5) * 3 if effective_dmg > 0 else 0)
            else:
                effective_dmg = damage_instance - armor
                effectivedmg.append(effective_dmg if effective_dmg > 0 else 0)

    # print(specific_modifiers, dmgstring, dmgtype, armor)
    for i, damage_instance in enumerate(effectivedmg):
        total_damage += damage_instance * specific_modifiers[i]
    return total_damage


def supply_graphdata():
    try:
        import os
        with open(os.path.expanduser("~/wiki/weapons.md")) as f:
            dmgraw = f.read()
            print("successfully loaded", len(dmgraw), "weapons.md locally")
    except Exception as e:
        r = requests.get("http://nosferatu.vampir.es/wiki/weapons/raw")
        dmgraw = r.content.decode()
        print("loaded weapons.md via web, because", e, e.args)
    armormax = 14
    dmgtypes = ["Hacken", "Stechen", "Schneiden", "Schlagen", "Stab"]
    weapons = {}
    for dmgsect in dmgraw.split("###"):
        if not dmgsect.strip() or "[TOC]" in dmgsect:
            continue

        # if not all(x in dmgsect for x in ["Wert"] + dmgtypes):
        #    continue
        weapon = dmgsect[:dmgsect.find("\n")].strip()
        weapons[weapon] = {}
        for dmgline in dmgsect.split("\n"):
            if "Wert" in dmgline or "---" in dmgline or len(dmgline) < 50:
                continue
            if "|" not in dmgline:
                break
            dmgtype = dmgline[dmgline.find("[") + 1:dmgline.find("]")].strip()
            weapons[weapon][dmgtype] = dmgline[35:]
        if "##" in dmgsect:
            break

    for weapon in weapons.keys():
        for dt in dmgtypes:
            weapons[weapon][dt] = weapons[weapon].get(dt, "")
        print(weapon, weapons[weapon])
    wmd5 = md5(str(weapons).encode("utf-8")).hexdigest()
    damages = {}
    print(wmd5)
    try:
        with open("weaponstuff_internal") as f:
            nmd5 = f.readline()
            if str(nmd5).strip() == str(wmd5).strip():
                with open("NossiSite/static/graphdata.json") as g:
                    if str(wmd5) in g.read(len(str(wmd5) * 2)):  # find hash at the beginning of the json
                        return
                damages = ast.literal_eval(f.read())
            else:
                print(
                    f"fengraph hashes: {str(nmd5).strip()} != {str(wmd5).strip()}, so graphdata will be regenerated")
                damages = {}
    except SyntaxError as e:
        print("syntax error in weaponstuff_internal, regenerating:", e.msg)
    except FileNotFoundError:
        damages = {}
        # regenerate and write weaponstuff
    maxdmg = 0
    if not damages:

        modifiers = {}
        with open("5d10_ordered_data") as f:
            for line in f.readlines():
                line = ast.literal_eval(line)
                total = sum(line[1].values())
                zero_excluded_positive = [line[1].get(i, 0) for i in range(1, 21)]
                zepc = zero_excluded_positive[:9] + [sum(zero_excluded_positive[9:])]
                zepc_relative = [x / total for x in zepc]
                modifiers[line[0]] = zepc_relative

        print("regenerating weapon damage data")
        for stats, modifier in modifiers.items():
            statstring1 = " ".join([str(x) for x in stats[0]])
            statstring2 = " ".join([str(x) for x in stats[1]])
            damages[statstring1] = damages.get(statstring1, {})
            damages[statstring1][statstring2] = []
            damage = damages[statstring1][statstring2]  # reduce length of calling stuff
            print(stats, modifier)
            for i in range(armormax):
                damage.append({})
                for w in weapons.keys():
                    damage[-1][w] = {}
                    for d in weapons[w].keys():
                        damage[-1][w][d] = modify_dmg(modifier, weapons[w][d], d, i)
        print("writing weaponstuff...")
        with open("weaponstuff_internal", "w") as f:
            f.write(str(wmd5) + "\n")
            f.write(str(damages))

    cmprjsn = {"Hash": wmd5, "Names": list(weapons.keys()), "Types": list(dmgtypes)}
    for attackerstat, defender in (sorted(damages.items())):
        cmprjsn[attackerstat] = {}
        for defenderstat, damage in defender.items():
            cmprjsn[attackerstat][defenderstat] = []
            for per_armor in damage:
                print(per_armor)
                # noinspection PyTypeChecker
                cmprjsn[attackerstat][defenderstat].append(list(
                    list(per_armor[weapon][damagetype]
                         for weapon in cmprjsn["Names"])
                    for damagetype in dmgtypes))
                nm = max(list(max(x for x in [
                    list(per_armor[weapon][damagetype]
                         for weapon in cmprjsn["Names"])
                    for damagetype in dmgtypes])))
                if nm > maxdmg:
                    print("updating maxdmg to", nm)
                    maxdmg = nm
    cmprjsn["max"] = math.ceil(maxdmg)
    with open("NossiSite/static/graphdata.json", "w") as f:
        f.write(json.dumps(cmprjsn))


def dataset(modifier):
    import pandas
    return pandas.read_csv("roll_frequencies_" + str(modifier) + ".csv",
                           names=["D1", "D2", "D3", "D4", "D5", "frequency"])


def select_modified(selector, series):
    return sum(series[s - 1] for s in selector if 0 < s < 6), series[-1]


def helper(f, integratedsum, q, lastquant):
    def internalhelper(x):
        try:
            result = quad(f, lastquant, x, limit=200)
            return result[0] - integratedsum * q
        except:
            print("errvals:", q, lastquant, x)
            raise

    return internalhelper


def chances(selector, modifier=0, number_of_quantiles=None):
    selector = tuple(sorted(int(x) for x in selector if 0 < int(x) < 6))
    modifier = int(modifier)
    occurrences = {}
    yield "processing..."
    try:
        with open("unordered_data") as f:
            for line in f.readlines():
                if line.startswith(str(selector)):
                    occurrences = ast.literal_eval(line[len(str(selector)):])[modifier]
                    break
            if not occurrences:
                yield "did not find" + str(selector)
                raise Exception("no data found")
        yield "data found..."
    except Exception as e:
        yield f"generating Data for {selector}..."
        with open("unordered_data", "a") as f:
            occurren = {}
            for mod in range(-5, 6):
                df = dataset(mod)
                occ = {k: 0 for k in range(1, 10 * len(selector) + 1)}
                for row, series in df.iterrows():
                    k, v = select_modified(selector, series)
                    occ[k] += v
                occurren[mod] = occ
            f.write(str(tuple(selector)) + str(occurren) + "\n")
        occurrences = occurren[modifier]
        yield f"Data for {selector} has been generated"
    yield "generating result..."
    max_val = max(list(occurrences.values()))
    total = sum(occurrences.values())
    if number_of_quantiles is None:
        res = ", ".join([str(x) for x in selector]) + "@5" + (("R" + str(modifier)) if modifier else "") + "\n"
        for k in sorted(occurrences):
            if occurrences[k]:
                res += f"{k:5d} {100 * occurrences[k] / total: >5.2f} {'#' * int(40 * occurrences[k] / max_val)}\n"
        yield res
    if number_of_quantiles is not None:
        yield "generating graph..."
        res = ""
        fy = [x / total for x in occurrences.values()]
        fx = sorted(list(occurrences.keys()))
        f = interp1d(fx, fy, kind=2, bounds_error=False, fill_value=0)
        import matplotlib.pyplot as plt
        plt.figure()
        plt.bar(range(1, len(occurrences.values()) + 1), [1 * x / total for x in occurrences.values()],
                facecolor='green', alpha=0.75, linewidth=1)
        linx = numpy.linspace(1, max(occurrences.keys()) + 1, max(occurrences.keys()) * 10)
        integratedsum = 1
        quantiles = [0]
        if number_of_quantiles:
            yield "calculating integrals"
            tries = 0
            while tries < 3:
                try:
                    n = max(min(int(number_of_quantiles), 100), 0) + 1
                    quantiles = [0]
                    for q in [1 / n for _ in range(n - 1)]:
                        quantiles.append(fsolve(func=helper(f, integratedsum, q, quantiles[-1]),
                                                x0=numpy.array([quantiles[-1]] if quantiles[-1]
                                                               else 1)))
                    tries += 3
                except Exception as e:
                    print("exception in calculating:", e, n)
                    raise
                    yield "WARNING: RECALCULATING"
                    tries += 1
        yield "finalizing graph"
        plt.plot(linx, f(linx), "--")
        buf = io.BytesIO()
        for q in quantiles[1:]:
            plt.axvline(q)
        if max(occurrences.keys()) < 31:
            plt.xticks(list(range(1, max(occurrences.keys()) + 1)))
        plt.ylim(ymin=0.0)
        plt.xlim(xmin=0.0)
        plt.title(", ".join([str(x) for x in selector]) + "@5" + (("R" + str(modifier)) if modifier else ""))
        plt.ylabel("%")
        yield "sending data..."
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.show()
        plt.close()
        buf.seek(0)
        yield buf


if "__main__" == __name__:
    supply_graphdata()
