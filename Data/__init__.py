import importlib.resources
import json
import logging
import pathlib
import pickle
import sqlite3
from contextlib import closing
from pathlib import Path


DATABASE = "./NN.db"
g = {}  # module level caching
logger = logging.getLogger(__name__)


def init_db():
    logger.info("initializing DB")
    with closing(connect_db("initialization")) as db:
        db.cursor().executescript(getschema())
        db.commit()


def connect_db(source) -> sqlite3.Connection:
    """db connection singleton"""
    db = g.get("db", None)
    if db:
        return db
    dbpath = DATABASE
    if source != "before request":
        logger.info(f"connecting to {dbpath} from {source}")
    if not Path(dbpath).exists():
        Path(dbpath).touch()
        init_db()
    g["db"] = sqlite3.connect(dbpath)
    return g["db"]


def close_db():
    db = g.get("db", None)
    if db:
        db.close()
        g["db"] = None


def get_str(res):
    with importlib.resources.open_text("Data", pathlib.Path(res)) as data:
        return data.read()


def get_roll_freq_dict(mod):
    lines = get_str(f"roll_frequencies_{mod}.csv")
    return {
        tuple(x[:5]): int(x[5])
        for x in [[int(z) for z in y.split(",")] for y in lines.splitlines()]
    }


def handle(res):
    path: pathlib.Path
    try:
        with importlib.resources.path("Data", pathlib.Path(res)) as path:
            return path.as_posix()
    except FileNotFoundError as e:
        path = pathlib.Path(e.filename)
        path.touch()
        return path.as_posix()


def check(res):
    try:
        with importlib.resources.path("Data", pathlib.Path(res)) as path:
            return path.as_posix()
    except FileNotFoundError:
        return ""


def append(res, d):
    with open(handle(res), "a") as data:
        data.write(d)


def set_str(res, d):
    with open(handle(res), "w") as data:
        data.write(d)


def getlocale_data():
    return json.loads(get_str("EN.json"))


def getschema():
    return get_str("schema.sql")


def getnossihelp():
    return get_str("nossibot.help")


def getcardhelp():
    return get_str("cards.help")


def write(name, obj):
    with open(handle(name), "wb") as data:
        pickle.dump(obj, data)


def read(name):
    try:
        with open(handle(name), "rb") as data:
            return pickle.load(data)
    except EOFError:
        return None
