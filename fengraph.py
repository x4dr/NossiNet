import io
import json
import math
from _md5 import md5
from math import ceil
from typing import List

import requests
import ast


def modify_dmg(specific_modifiers, dmgstring, damage_type, armor):
    dmg = [int(x) for x in dmgstring.split("|") if x.strip()]
    total_damage = 0
    effectivedmg = []
    for damage_instance in dmg:
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
    dmgtypes = ["Hacken", "Stechen", "Schneiden", "Schlagen"]
    weapons = {}
    for dmgsect in dmgraw.split("###"):
        if not dmgsect.strip():
            continue

        if not all(x in dmgsect for x in ["Wert"] + dmgtypes):
            continue
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


def chances(selector, modifier=0, img=False):
    selector = tuple(sorted(selector))
    occurrences = {}
    try:
        with open("unordered_data") as f:
            for line in f.readlines():
                if line.startswith(str(selector)):
                    occurrences = ast.literal_eval(line[len(str(selector)):])[modifier]
                    break
            if not occurrences:
                print("did not find", selector)
                raise Exception("no data found")
    except Exception as e:
        print(e)
        with open("unordered_data", "w") as f:
            for s1 in range(1, 6):
                for s2 in range(0, s1 + 1):
                    occurrences = {}
                    for mod in range(-5, 6):
                        df = dataset(mod)
                        occ = {k: 0 for k in range(1, 21)}
                        for row, series in df.iterrows():
                            k, v = select_modified([s1, s2], series)
                            occ[k] += v
                        occurrences[mod] = occ
                    print("writing", str(tuple(sorted([x for x in [s2, s1] if x]))), occurrences)
                    f.write(str(tuple(sorted([x for x in [s2, s1] if x]))) + str(occurrences) + "\n")
        return
    max_val = max(occurrences.values())
    total = sum(occurrences.values())
    res = ""
    for k in sorted(occurrences):
        if occurrences[k]:
            res += f"{k:5d} {100 * occurrences[k] / total: >5.2f} {'#' * int(40 * occurrences[k] / max_val)}\n"
    print(res)
    if not img:
        return res
    else:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.bar(range(1, 21), [100*x/total for x in occurrences.values()],
                facecolor='green', alpha=0.75, linewidth=1)
        plt.xticks(range(1, 21))
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        return buf


if "__main__" == __name__:
    supply_graphdata()
