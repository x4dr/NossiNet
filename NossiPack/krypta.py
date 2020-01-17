import random

from NossiPack.WoDParser import WoDParser


def d10bulk(amount, rep, difficulty=6):
    roll = WoDParser({}).make_roll(str(amount) + "d10f" + str(difficulty))
    res = []
    while rep >= 1:
        res.append(roll.roll())
        rep -= 1
    return res


def sumdict(inp):
    result = 0
    try:
        for e in inp.keys():
            result += int(inp[e])
    except:
        result = sum(inp)
    return result


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


'''
time1 = time()
res1 = []
times = 10000
for i in range(times):
    res1.append(d10(10, 10))
time2 = time()
#res2 = d10bulk(999, 10000)
time3 = time()
print("single fast:", sum(res1)/times, "successes and", time2 - time1, "seconds")
#print("bulkslow:", sum(res2), "successes and", time3 - time1, "seconds")
'''
