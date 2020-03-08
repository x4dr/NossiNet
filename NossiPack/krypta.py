import ctypes
import os
import random
import sqlite3
from contextlib import closing
from pathlib import Path

import Data


class DescriptiveError(Exception):
    pass


def terminate_thread(thread):
    """Terminates a python thread from another thread.

    :param thread: a threading.Thread instance
    """
    if not thread.isAlive():
        return

    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res == 0:
        raise ValueError("nonexistent thread id")
    if res > 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def init_db():
    print("initializing DB")
    with closing(connect_db("initialization")) as db:
        db.cursor().executescript(Data.getschema())
        db.commit()


g = {}  # module level caching


def close_db():
    db = g.get("db", None)
    if db:
        db.close()
        g["db"] = None


def connect_db(source) -> sqlite3.Connection:
    """db connection singleton"""
    db = g.get("db", None)
    if db:
        return db
    dbpath = Data.DATABASE
    if source != "before request":
        print("connecting to", dbpath, "from", source)
    if not Path(dbpath).exists():
        Path(dbpath).touch()
        init_db()
    g["db"] = sqlite3.connect(dbpath)
    return g["db"]


def write_nonblocking(path, data):
    path = Path(path)
    if path.is_dir():
        path = path / "_"
    i = 0
    while (path.with_suffix(f".{i}")).exists():
        i += 1
    with path.with_suffix(f".{i}").open(mode="x") as x:
        x.write(data + "\n")
        x.write("DONE")  # mark file as ready


def read_nonblocking(path):
    path = Path(path)
    if path.is_dir():
        path = path / "_"
    result = []
    file: Path
    for file in sorted(path.parent.glob(str(path.stem) + "*")):
        with file.open(mode="r") as f:
            lines = f.readlines()
            if lines[-1] != "DONE":
                break  # file not read yet or fragmented
            result += lines[:-1]
        os.remove(str(file.absolute()))
    return result


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


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
    for _ in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if ones and x == 1:
            anti += 1
    if anti > 0:
        if succ > anti:
            return succ - anti
        if succ > 0:
            return 0
        return 0 - anti
    return succ
