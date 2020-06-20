import importlib.resources
import json
import pathlib

DATABASE = "./NN.db"


def get(res):
    with importlib.resources.open_text("Data", pathlib.Path(res)) as data:
        return data.read()


def get_roll_freq_dict(mod):
    lines = get(f"roll_frequencies_{mod}.csv")
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


def append(res, d):
    with open(handle(res), "a") as data:
        data.write(d)


def set(res, d):
    with open(handle(res), "w") as data:
        data.write(d)


def getlocale_data():
    return json.loads(get("EN.json"))


def getschema():
    return get("schema.sql")


def getnossihelp():
    return get("nossibot.help")


def getcardhelp():
    return get("cards.help")
