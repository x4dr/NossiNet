import collections
import multiprocessing
import time

dice5 = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(100000):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [4, 3, 2, 1, 0]]))
    dice5[tuple(r)] = dice5.get(tuple(r), 0) + 1

dice4 = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(10000):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [3, 2, 1, 0]]))
    dice4[tuple(r)] = dice5.get(tuple(r), 0) + 1

dice3 = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(1000):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [2, 1, 0]]))
    dice3[tuple(r)] = dice5.get(tuple(r), 0) + 1

dice2 = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(100):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [1, 0]]))
    dice2[tuple(r)] = dice5.get(tuple(r), 0) + 1

dice1 = {}  # define global variable dice, takes less than 1 sec
for roll_id in range(10):
    r = tuple(sorted([(roll_id // (10 ** i)) % 10 or 10 for i in [0]]))
    dice1[tuple(r)] = dice5.get(tuple(r), 0) + 1


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


def comparison(sel):
    sel1, sel2 = sel
    print(f"starting {sel1}, {sel2}")
    occurences = collections.defaultdict(lambda: 0)
    j = 0
    time1 = time.time()
    for i, first in dice5.keys():
        for k, second in dice5.keys():
            j += 1
            delta = selector(sel1, i) - selector(sel2, k)
            # delta = min(10, max(delta, 0))  # clamp to 0-10
            occurences[delta] += second * first
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


def generate():
    print("multiprocessing!")
    pool = multiprocessing.Pool(processes=3)
    time0 = time.time()
    results = pool.map(comparison, tuplecombos)
    cumulativetime = sum(x[2] for x in results)
    results = [(x[0], x[1]) for x in results]

    def calc(x):
        return (
            (x[0][0][0] * 1000)
            + (x[0][0][1] * 100)
            + (x[0][1][0] * 10)
            + x[0][1][1] * 1
        )

    try:
        with open("5d10_ordered_data", "w") as f:
            for result in sorted(results, key=calc):
                f.write(str(result) + "\n")
    finally:
        print("Total time taken:", time.time() - time0, "/", cumulativetime)


if __name__ == "__main__":
    generate()
