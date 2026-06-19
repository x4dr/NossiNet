"""Database access and initialization for NossiNet."""

import json
import logging
import os
import pathlib
import sqlite3
from contextlib import closing
from importlib import resources
from pathlib import Path
from typing import Any

DATABASE = os.environ.get("DATABASE", "./NN.db")
g: dict[str, Any] = {}  # module level caching
logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initialize the database with the schema from schema.sql."""
    logger.info("initializing DB")
    with closing(connect_db("initialization")) as db:
        db.cursor().executescript(getschema())
        db.commit()


def connect_db(source: str) -> sqlite3.Connection:
    """Db connection singleton."""
    db = g.get("db")
    if db:
        assert isinstance(db, sqlite3.Connection)
        return db
    dbpath = DATABASE
    if source != "before request":
        logger.info(f"connecting to {dbpath} from {source}")
    if not Path(dbpath).exists():
        Path(dbpath).touch()
        init_db()
    conn = sqlite3.connect(dbpath, check_same_thread=False)
    g["db"] = conn
    return conn


def close_db() -> None:
    """Close the database connection if open."""
    db = g.get("db")
    if db:
        db.close()
        g["db"] = None


def get_str(res: str) -> str:
    """Read a data file from the package and return its content as a string."""
    with resources.files(__name__).joinpath(res).open("r") as data:
        return data.read()


def handle(res: str) -> str:
    """Resolve a resource path, creating the file if it does not exist."""
    try:
        path = resources.files(__name__).joinpath(res)
        return str(path)
    except FileNotFoundError as e:
        path = pathlib.Path(e.filename)
        path.touch()
        return path.as_posix()


def getlocale_data() -> dict[str, Any]:
    """Load and return the locale data from EN.json."""
    return json.loads(get_str("EN.json"))  # type: ignore[no-any-return]


def getschema() -> str:
    """Load and return the database schema from schema.sql."""
    return get_str("schema.sql")


def getnossihelp() -> str:
    """Load and return the NossiBot help text."""
    return get_str("nossibot.help")


def getcardhelp() -> str:
    """Load and return the cards help text."""
    return get_str("cards.help")
