import ctypes
import logging
import random
import threading
from decimal import ROUND_HALF_UP, Decimal

import numexpr
from gamepack.Dice import DescriptiveError

logger = logging.getLogger(__name__)


def terminate_thread(thread: threading.Thread):
    """
    Terminates a python thread from another thread
    :param thread: a threading.Thread instance
    """
    if not thread.is_alive():
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


def calculate(calc, par=None):
    loose_par = [0]  # last pop ends the loop
    if par is None:
        par = {}
    else:
        loose_par += [x for x in par.split(",") if ":" not in x]
        par = {
            x.upper(): y
            for x, y in [pair.split(":") for pair in par.split(",") if ":" in pair]
        }
    for k, v in par.items():
        calc = calc.replace(k, v)
    calc = calc.strip()
    missing = None
    res = 0
    while len(loose_par) > 0:
        try:
            res = numexpr.evaluate(calc, local_dict=par, truediv=True).item()
            missing = None  # success
            break
        except KeyError as e:
            missing = e
            par[e.args[0]] = float(loose_par.pop())  # try autofilling
    if missing:
        raise DescriptiveError("Parameter " + missing.args[0] + " is missing!")
    return Decimal(res).quantize(1, ROUND_HALF_UP)


def d10(amt, diff, ones=True):  # faster than the Dice
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
