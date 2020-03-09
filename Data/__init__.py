import importlib.resources
import json
import pathlib

DATABASE = "./NN.db"


def get(res):
    with importlib.resources.open_text("Data", pathlib.Path(res)) as data:
        return data.read()


def getlocale_data():
    return json.loads(get("EN.json"))


def getschema():
    return get("schema.sql")


def getnossihelp():
    return get("nossibot_help.help")
