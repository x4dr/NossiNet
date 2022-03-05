import importlib.resources
import json
import pathlib
import pickle

DATABASE = "./NN.db"


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
