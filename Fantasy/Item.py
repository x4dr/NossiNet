import math
from typing import Union


class Item:
    name: str
    weight: float
    price: Union[float, None]

    def __init__(self, name: str, weight: float, price: float):
        self.name = name
        self.weight = weight
        self.price = price


def fenconvert(inp: str) -> float:
    """
    converts numeric measurements found in pages of the fen wiki into their
    number representation from this point units/types are implicit and only given by context.
    Money has the suffixes c,s and g and is converted into copper coins.
    Weight has the suffixes t,kg and gr and will be converted into grams.
    All outputs are floats, inputs can be suffixed or not
    :param inp: the inputstring containing optional suffixes
    :return: float number to be treated as implicitly typed
    """
    weight = {"gr": 1, "kg": 10 ** 3, "t": 10 ** 6}
    money = {"c": 1, "s": 10 ** 2, "g": 10 ** 4}
    conversions = {**weight, **money}  # merge dicts, duplicates will be clobbered
    inp = inp.strip()
    for k, length in sorted(
        [(str(k), len(k)) for k in conversions.keys()], key=lambda x: x[1], reverse=True
    ):
        if inp.endswith(k):
            return float(inp[:-length]) * conversions[k]
    return float(inp)


def fendeconvert(val: float, conv: str) -> str:
    """
    undoes fenconvert while choosing the units
    :param val: base unit for a category of units
    :param conv: category name
    """
    conversions = {
        "weight": (10 ** 3, {"gr": 1, "kg": 10 ** 3, "t": 10 ** 6}),
        "money": (10 ** 2, {"c": 1, "s": 10 ** 2, "g": 10 ** 4}),
    }.get(conv, None)
    if conversions:
        units = [
            x[1]
            for x in sorted(
                [(val, key) for key, val in conversions[1].items()], key=lambda x: x[0]
            )
        ]
        base = conversions[0]
        exp = int(math.log(val, base)) if val > 0 else 0  # no log possible
        exp = min(len(units) - 1, exp)  # biggest unit for all that are too big
        return f"{val / conversions[1][units[exp]]:.10g}" + units[exp]
    return str(val)
