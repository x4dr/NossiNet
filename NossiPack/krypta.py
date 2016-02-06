

import os
import random
import struct

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


def roll(low=0, high=0, attribute=0, ability=0):
    output = 0
    if high != 0:
        output = random.Random().randint(low, high)
    if attribute != 0:
        if ability == 0:
            return d10(attribute - 1)
        else:
            return d10(attribute + ability)
    return output


def randomlyspend(count, start, maximum, points):
    tmp = []
    for i in range(count):
        tmp.append(start)
    while points > 0:
        i = random.Random().randrange(0, len(tmp))
        if tmp[i] >= maximum:
            if all([t >= maximum for t in tmp]):
                break
            continue
        tmp[i] += 1
        points += -1
    return tmp
