import os
import random
import struct
import math
from helpers import connect_db, init_db

from Crypto.Cipher import AES

__author__ = 'maric'
'''original encrypt and decrypt from Eli Bendersky'''


def encrypt_file(key, in_filename, out_filename=None, chunksize=64 * 1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        in_filename:
            Name of the input file

        out_filename:
            If None, '<in_filename>.enc' will be used.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """
    if not out_filename:
        out_filename = in_filename + '.enc'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(in_filename)

    with open(in_filename, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))


def decrypt_file(key, in_filename, out_filename=None, chunksize=24 * 1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be in_filename without its last extension
        (i.e. if in_filename is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """
    if not out_filename:
        out_filename = os.path.splitext(in_filename)[0]

    with open(in_filename, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(origsize)


def d10(amount, difficulty=6, mode=""):
    successes = 0
    ones = 0
    i = 0
    while i < amount:
        i += 1
        r = random.Random().randint(1, 10)
        if r >= difficulty:
            successes += 1
        if r == 1:
            ones += 1
        if "X10" in mode:
            if r == 10:
                amount += 1
        if "X9" in mode:
            if r == 9:
                amount += 1
        if "X8" in mode:
            if r == 8:
                amount += 1
        if "X7" in mode:
            if r == 7:
                amount += 1
    if successes > 0:
        if successes > ones:
            return successes - ones
        else:
            return 0
    else:
        return -ones


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

    def pack(inp):
        result = ""
        for i in range(len(inp)):
            result += str(inp[i]) + " "

        return result

    def getindex(x):
        if x >= 0:
            return x * 2
        else:
            return (-1)*x * 2 - 1

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


def roll(low=0, high=0, attribute=0, ability=0):  # not used right now
    output = 0
    if high != 0:
        output = random.Random().randint(low, high)
    if attribute != 0:
        if ability == 0:
            return d10(attribute - 1)
        else:
            return d10(attribute + ability)
    return output
