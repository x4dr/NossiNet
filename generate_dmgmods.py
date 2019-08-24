import collections
import math
import multiprocessing
import time

dice = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(100000):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [4, 3, 2, 1, 0]]))
    dice[tuple(r)] = dice.get(tuple(r), 0) + 1


def selector(sel, r):
    return sum(r[s - 1] for s in sel)


def calc_mods(data, showdmgmods=False):
    total = sum(data.values())
    lowest = min(data.keys())
    highest = max(data.keys())
    for i in range(lowest, highest + 1):
        if i not in data.keys():
            data[i] = 0
    dmgmods = [data[i // 2 * ((-1) ** (i % 2))] / total for i in range(1, len(data) + 1)]
    print(list(i // 2 * ((-1) ** (i % 2)) for i in range(1, len(data) + 1)))
    if showdmgmods:
        print("dmgmods(adjusted):")
        print(dmgmods)
    return dmgmods


def comparison(sel):
    sel1, sel2 = sel
    print(f"starting {sel1}, {sel2}")
    occurences = collections.defaultdict(lambda: 0)
    j = 0
    global dice
    time1 = time.time()
    for i in dice.keys():
        for k in dice.keys():
            j += 1
            delta = selector(sel1, i) - selector(sel2, k)
            # delta = min(10, max(delta, 0))  # clamp to 0-10
            occurences[delta] += dice[k] * dice[i]
    print(f"rolling {sel1} against {sel2} for {time.time() - time1:.4} seconds")
    return sel, dict(occurences), time.time() - time1


tuples = []
for a in range(1, 6):
    for b in range(1, a + 1):
        tuples.append((a, b))
tuplecombos = []
for t1 in tuples:
    for t2 in tuples:
        tuplecombos.append((t1, t2))
if __name__ == '__main__':
    pool = multiprocessing.Pool(processes=4)
    time0 = time.time()
    results = pool.map(comparison, tuplecombos)
    cumulativetime = sum([x[2] for x in results])
    results = [(x[0], x[1]) for x in results]
    try:
        with open("results_full", "w") as f:
            for r in sorted(results, key=lambda x: (x[0][0][0] * 1000) + (x[0][0][1] * 100)
                                                   + (x[0][1][0] * 10) + x[0][1][1] * 1):
                f.write(str(r) + "\n")
    except:
        raise
    finally:
        print("Total time taken:", time.time() - time0,"/", cumulativetime)
