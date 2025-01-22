import json
import logging
import pathlib
import sqlite3
from contextlib import closing
from importlib import resources
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
    db = g.get("db")
    if db:
        return db
    dbpath = DATABASE
    if source != "before request":
        logger.info(f"connecting to {dbpath} from {source}")
    if not Path(dbpath).exists():
        Path(dbpath).touch()
        init_db()
    g["db"] = sqlite3.connect(dbpath, check_same_thread=False)
    return g["db"]


def close_db():
    db = g.get("db")
    if db:
        db.close()
        g["db"] = None


def get_str(res: str):
    with resources.files(__name__).joinpath(res).open("r") as data:
        return data.read()


def handle(res):
    try:
        path = resources.files(__name__).joinpath(res)
        return str(path)
    except FileNotFoundError as e:
        path = pathlib.Path(e.filename)
        path.touch()
        return path.as_posix()


def getlocale_data():
    return json.loads(get_str("EN.json"))


def getschema():
    return get_str("schema.sql")


def getnossihelp():
    return get_str("nossibot.help")


def getcardhelp():
    return get_str("cards.help")
