import math
from typing import Union, List


class Item:
    name: str
    weights: float
    price: Union[float, None]
    item_cache = {}  # to be injected  from outside
    total_row_marker = ("gesamt", "total", "summe", "sum")
    table_name = ("objekt", "object", "name", "gegenstand", "item")
    table_weight = ("gewicht", "weight")
    table_money = ("preis", "kosten", "price", "cost")
    table_amount = ("zahl", "anzahl", "menge", "amount", "count", "stück")

    def __init__(self, name: str, weight: float, price: float, count: float = 1.0):
        self.name = name
        self.weight = tryfloatdefault(weight)
        self.price = tryfloatdefault(price)
        self.count = tryfloatdefault(count, 1)

    def __repr__(self):
        return f"{self.count:g} {self.name}"

    @property
    def singular_weight(self):
        return fendeconvert(self.weight, "weight")

    @property
    def singular_price(self):
        return fendeconvert(self.price, "money")

    @property
    def total_weight(self):
        return fendeconvert(self.weight * self.count, "weight")

    @property
    def total_price(self):
        return fendeconvert(self.price * self.count, "money")

    @classmethod
    def process_table(cls, table: List[List[str]], flash) -> List["Item"]:
        def get_offset(reqs, optional=False):
            if offs.get(reqs, "default") == "default":
                for req in reqs:
                    if req in headers:
                        offs[reqs] = headers.index(req)
                        break
                else:
                    if not optional:
                        flash(
                            f"none of {', '.join(reqs)} found in {', '.join(headers)}."
                        )
                    offs[reqs] = None
            return offs[reqs]

        def get_cell(r, req):
            o = get_offset(req)
            if o is None:
                return ""
            return r[o]

        headers = [x.lower() for x in table[0]]
        offs = {}
        res = []
        get_offset(cls.table_amount, True)  # preload with nonoptional
        if get_offset(cls.table_name) is not None:
            for row in table[1:]:
                if row[0].lower() in cls.total_row_marker:
                    continue
                try:
                    if not get_cell(row, cls.table_weight) and not get_cell(
                        row, cls.table_money
                    ):
                        cached = cls.item_cache.get(get_cell(row, cls.table_name), None)
                        if cached is not None:
                            cached = cached.copy()
                            cached.count = float(get_cell(row, cls.table_amount)) or 1
                            res.append(cached)
                        else:
                            res.append(
                                Item(
                                    get_cell(row, cls.table_name),
                                    0,
                                    0,
                                    count=get_cell(row, cls.table_amount) or 1,
                                )
                            )
                    else:
                        res.append(
                            cls(
                                row[get_offset(cls.table_name)],
                                fenconvert(get_cell(row, cls.table_weight)),
                                fenconvert(get_cell(row, cls.table_money)),
                                count=get_cell(row, cls.table_amount) or 1,
                            )
                        )
                except Exception:
                    flash("|".join(row) + " is not a valid item")
        return res

    def copy(self):
        return Item(self.name, self.weight, self.price, self.count)


weights = {"g": 1, "kg": 10**3, "t": 10**6}
currencies = {"k": 1, "s": 10**2, "a": 10**4}


def tryfloatdefault(inp, default=0):
    if not inp:
        return default
    try:
        return float(inp)
    except:
        return tryfloatdefault(inp[:-1])


def value_category(inp: str) -> str:
    """
    gets the type of unit used

    :param inp: full measurement
    :return: weight or money
    """
    for end in weights.keys():
        if inp.endswith(end):
            return "weight"
    for end in currencies.keys():
        if inp.endswith(end):
            return "money"
    return ""


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
    conversions = {**weights, **currencies}  # merge dicts, duplicates will be clobbered
    inp = inp.strip()
    for k, length in sorted(
        [(str(k), len(k)) for k in conversions.keys()], key=lambda x: x[1], reverse=True
    ):
        if inp.lower().endswith(k):
            return float(inp[:-length]) * conversions[k]

    return tryfloatdefault(inp, 0)


def fendeconvert(val: float, conv: str) -> str:
    """
    undoes fenconvert while choosing the units
    :param val: base unit for a category of units
    :param conv: category name
    """
    conversions = {"weight": (10**3, weights), "money": (10**2, currencies)}.get(
        conv, None
    )
    sign = 1 if val >= 0 else -1
    val = abs(val)
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
        return f"{sign*val / conversions[1][units[exp]]:.10g}" + units[exp]
    return str(sign * val)
