import os
import random
from time import time

from NossiPack.WoDParser import WoDParser
from NossiSite.helpers import connect_db, init_db


def d10bulk(amount, rep, difficulty=6):
    roll = WoDParser({}).make_roll(str(amount) + "d10f" + str(difficulty))
    res = []
    while rep >= 1:
        res.append(roll.reroll())
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


def gendicedata(amount, difficulty, minimumocc=20, maxrolls=10000000):
    oldsuc = {}

    def addpacked(a, b):
        a = [int(x) for x in a.split(" ") if x]
        b = [int(x) for x in b.split(" ") if x]
        if len(a) > len(b):  # if not all values are present, they are incompatible, prefer longer
            return " ".join([str(x) for x in a])
        if len(b) > len(a):
            return " ".join([str(x) for x in b])
        return " ".join([str(a[x] + b[x]) for x in range(len(a))])

    def writetodb(inp):
        nonlocal amount, difficulty
        db = connect_db()
        init_db()
        data = pack(inp)
        try:
            cur = db.execute('SELECT * '
                             'FROM dice '
                             'WHERE amount = ? AND difficulty = ?',
                             (amount, difficulty))
            existingdata = cur.fetchall()[0][2]
            data = addpacked(data, existingdata)
            db.execute("UPDATE dice "
                       "SET data = ?"
                       "WHERE amount = ? AND difficulty = ?",
                       (data, amount, difficulty))

            print("updated data for amount %d, difficulty %d: \t%s " % (amount, difficulty, data))
        except Exception as inst:
            print("no data found for amount %d, difficulty %d, inserted new " % (amount, difficulty))
            db.execute("INSERT INTO dice (amount, difficulty, data)"
                       "VALUES (?,?,?)", (amount, difficulty, data))
        db.commit()  # for x in successes.keys():

    def recheck(successes):
        delta = 0
        newsuc = {}
        total = sumdict(successes)
        nonlocal oldsuc

        for e in range(len(successes)):
            newsuc[e] = successes[e] / total
        for e in range(len(newsuc)):
            delta += abs(newsuc[e] - oldsuc.get(e, 0))  # normalizes large discrepancies
        for e in range(len(successes)):
            if successes[e] < minimumocc:  # want a few of each at least
                delta += 1
        oldsuc = newsuc

        return delta

    def pack(inp):
        result = ""
        for i in range(len(inp)):
            result += str(inp[i]) + " "

        return result

    def getindex(x):
        if x >= 0:
            return x * 2
        else:
            return (-1) * x * 2 - 1

    i = 0
    successes = [0] * (amount * 2 + 1)
    delta = 1

    while delta > 0.1:
        x = d10(amount, difficulty)
        successes[getindex(x)] += 1
        i += 1
        if i % 10000 == 0:
            delta = recheck(successes)
            if i >= maxrolls:
                break
    print(successes)
    print(i, "rolls ended with delta", delta)

    writetodb(successes)


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