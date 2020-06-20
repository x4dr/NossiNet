import collections
import multiprocessing
import sys
import time

import Data


def selector(sel, roll):
    return sum(roll[s - 1] for s in sel)


def calc_mods(data, showdmgmods=False):
    total = sum(data.values())
    lowest = min(data.keys())
    highest = max(data.keys())
    for i in range(lowest, highest + 1):
        if i not in data.keys():
            data[i] = 0
    dmgmods = [
        data[i // 2 * ((-1) ** (i % 2))] / total for i in range(1, len(data) + 1)
    ]
    print([i // 2 * ((-1) ** (i % 2)) for i in range(1, len(data) + 1)])
    if showdmgmods:
        print("dmgmods(adjusted):")
        print(dmgmods)
    return dmgmods


def comparator(param):
    seltuple, dice = param
    sel1, sel2 = seltuple
    print(f"starting {sel1}, {sel2}")
    occurences = collections.defaultdict(lambda: 0)
    j = 0
    time1 = time.time()
    for roll_left, absolute_left in dice.items():
        for roll_right, absolute_right in dice.items():
            j += 1
            delta = selector(sel1, roll_left) - selector(sel2, roll_right)
            # delta = min(10, max(delta, 0))  # clamp to 0-10
            occurences[delta] += absolute_right * absolute_left
    print(f"comparing {sel1} against {sel2} took {time.time() - time1:.4} seconds")
    sys.stdout.flush()
    return seltuple, dict(occurences), time.time() - time1


tuples = []
for a in range(1, 6):
    for b in range(1, a + 1):
        tuples.append((a, b))
tuplecombos = []
for t1 in tuples:
    for t2 in tuples:
        tuplecombos.append((t1, t2))


def generate(mod=0):
    print("multiprocessing!")
    pool = multiprocessing.Pool(processes=3)
    time0 = time.time()
    dice = Data.get_roll_freq_dict(mod)
    results = pool.map(comparator, [(x, dice) for x in tuplecombos])
    cumulativetime = sum(x[2] for x in results)
    results = [(x[0], x[1]) for x in results]

    def calc(x):
        print(x)
        return (
            (x[0][0][0] * 1000)
            + (x[0][0][1] * 100)
            + (x[0][1][0] * 10)
            + x[0][1][1] * 1
        )

    try:
        Data.set(
            f"5d10r{mod}_ordered_data",
            "\n".join(str(x) for x in sorted(results, key=calc)),
        )
    finally:
        print("Total time taken:", time.time() - time0, "/", cumulativetime)


if __name__ == "__main__":
    generate()
