import html
import random
import time

from flask import (
    request,
    session,
    flash,
    redirect,
    url_for,
    Response,
    render_template,
    Blueprint,
)

from NossiPack.Cards import Cards
from NossiPack.User import Userlist
from NossiPack.VampireCharacter import VampireCharacter
from NossiSite.base import log
from NossiSite.helpers import checklogin
from gamepack.Dice import DescriptiveError

views = Blueprint("extra", __name__)


def numbertomatrix(number: int, length: int) -> list[int]:
    return [int(x) for x in bin(number)[2:].rjust(length, "0")]


def randommatrix(length: int) -> list[int]:
    return [random.randint(0, 1) for _ in range(length)]


def togglelock(matrix: list[int], position: int) -> (list[int], list[int]):
    # toggles the bit at position number and its neighbors if interpreted as a square matrix
    length = int(len(matrix) ** 0.5)
    pos = [position]
    if pos[0] > length - 1:
        pos.append(pos[0] - length)
    if pos[0] < len(matrix) - length:
        pos.append(pos[0] + length)
    if pos[0] % length > 0:
        pos.append(pos[0] - 1)
    if pos[0] % length < length - 1:
        pos.append(pos[0] + 1)
    for p in pos:
        matrix[p] = 1 - matrix[p]
    return matrix, pos


@views.route("/lock/<int:sides>")
def lock(sides=5):
    if sides > 50:
        sides = 50
    f = [0] * int(sides**2)
    for i, x in enumerate(randommatrix(sides**2)):
        if x:
            f, _ = togglelock(f, i)
    session["lock"] = f
    return render_template("misc/lock.html", sidelen=sides, field=f)


@views.route("/lockclick/<int:pos>")
def lockinteract(pos: int):
    if "lock" not in session:
        return redirect(url_for("extra.lock"))

    f = session["lock"]
    if pos >= len(f):
        return redirect(url_for("extra.lock"))
    f, p = togglelock(f, pos)
    session["lock"] = f
    return render_template(
        "misc/lockfield.html", field=f, sidelen=int(len(f) ** 0.5), toupdate=p
    )


@views.route("/setfromsource/")
def setfromsource():
    checklogin()
    source = request.args.get("source")
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    try:
        new = VampireCharacter()
        if new.setfromdalines(source[-7:]):
            u.sheetid = u.savesheet(new)
            ul.saveuserlist()
            flash("character has been overwritten with provided Dalines sheet!")
        else:
            flash("problem with " + source)
    except Exception:
        log.exception("setfromsource:")
        flash(
            "Sorry " + session.get("user").capitalize() + ", I can not let you do that."
        )
    return redirect(url_for("views.charsheet"))


@views.route("/timetest")
def timetest():
    return str(time.time())


@views.route("/boardgame<int:size>_<seed>.json")
@views.route("/boardgame<int:size>_.json")
def boardgamemap(size, seed=""):
    if size > 100:
        size = 100
    rx = random.Random()
    if seed:
        rx.seed(str(size) + str(seed))

    def r(a=4):
        for _ in range(a):
            yield rx.randint(1, 10)

    def e(inp, dif):
        for i in inp:
            yield 2 if i == 10 else (1 if i >= dif else 0)

    def fpik(inp, pref="FPIK"):
        vals = list(inp)
        vals = [(v if v != 2 else (2 if sum(vals) < 4 else 1)) for v in vals]
        for i, p in enumerate(pref):
            yield '"' + p + '": ' + str(vals[i])

    def cell():  # i, j):
        difficulty = 8
        """6 + (
            (9 if i == j else
             8)
            if i in [0, size - 1] and j in [0, size - 1] else
            (7 if j in [0, size - 1] else
             (6 if j % 2 == 1 and (i in [0, size - 1] or j in [0, size - 1]) else
              (5 if 0 < i < size - 1 else 8))))"""

        for li in fpik(e(r(), difficulty)):
            yield li

    first = True

    def notfirst():
        nonlocal first
        if first:
            first = False
            return True
        return False

    def resetfirst():
        nonlocal first
        first = True

    def generate():
        yield '{"board": ['
        for x in range(size):
            yield ("," if not first else "") + "["
            resetfirst()
            for y in range(size):
                yield (
                    "" if notfirst() else ","
                ) + f'{{ "x":{x:d}, "y":{y:d}, ' + ",".join(
                    cell(
                        # x, y
                    )
                ) + "}"
            yield "]"
        yield "]}"

    return Response(generate(), mimetype="text/json")


@views.route("/gameboard/<int:size>/")
@views.route("/gameboard/<int:size>/<seed>")
def gameboard(size, seed=""):
    if size > 20:
        size = 20
    return render_template("misc/gameboard.html", size=size, seed=seed)


@views.route("/vamp_chargen/standard")
def standardchar():
    return redirect(
        url_for("extra.chargen", a=3, b=5, c=7, abia=5, abib=9, abic=13, shuffle=1)
    )


@views.route("/cards/", methods=["GET"])
@views.route("/cards/<command>", methods=["POST", "GET"])
def cards(command: str = None):
    checklogin()
    deck = Cards.getdeck(session["user"])
    try:
        if request.method == "GET":
            if command is None:
                return deck.serialized_parts
        elif request.method == "POST":
            par = html.escape(
                request.get_json()["parameter"]
            )  # escape html to prevent XSS
            if command == "draw":
                return {"result": list(deck.draw(par))}
            elif command == "spend":
                return {"result": list(deck.spend(par))}
            elif command == "returnfun":
                return {"result": list(deck.pilereturn(par))}
            elif command == "dedicate":
                if ":" not in par:
                    par += ":"
                return {"result": list(deck.dedicate(*par.split(":", 1)))}
            elif command == "remove":
                return {"result": list(deck.remove(par))}
            elif command == "free":
                message = deck.undedicate(par)
                for m in message:
                    flash("Affected Dedication: " + m)
                    return {"result": "ok", "messages": list(message)}
            elif command == "free":
                affected, message = deck.free(par)
                for m in message:
                    flash("Affected Dedication: " + m)
                return {
                    "result": list(affected),
                    "messages": message,
                }
            else:
                return {"result": "error", "error": f"invalid command {command}"}

        return render_template("misc/cards.html", cards=deck)
    except DescriptiveError as e:
        return {"result": "error", "error": e.args[0]}
    except TypeError:
        return {"result": "error", "error": "Parameter is not in a valid Format"}
    finally:
        Cards.savedeck(session["user"], deck)


@views.route("/vamp_chargen", methods=["GET", "POST"])
def chargen_menu():
    if request.method == "POST":
        f = dict(request.form)
        if not f.get("vampire", None):
            return redirect(
                url_for(
                    "vamp_chargen",
                    a=f["a"],
                    b=f["b"],
                    c=f["c"],
                    abia=f["abia"],
                    abib=f["abib"],
                    abic=f["abic"],
                    shuffle=1 if f.get("shuffle", 0) else 0,
                )
            )
        return redirect(
            url_for(
                "vamp_chargen",
                a=f["a"],
                b=f["b"],
                c=f["c"],
                abia=f["abia"],
                abib=f["abib"],
                abic=f["abic"],
                shuffle=1 if f["shuffle"] else 0,
                vamp=f["discipline"],
                back=f["back"],
            )
        )
    return render_template("sheets/generate_dialog.html")


@views.route("/vamp_chargen/<a>,<b>,<c>,<abia>,<abib>,<abic>,<shuffle>")
@views.route("/vamp_chargen/<a>,<b>,<c>,<abia>,<abib>,<abic>,<shuffle>,<vamp>,<back>")
def chargen(a, b, c, abia, abib, abic, shuffle, vamp=None, back=None):
    """
    Redirects to the charactersheet/ editor(if logged in) of a randomly
    generated character
    :param a: points to be allocated in the first attribute group
    :param b: points to be allocated in the second attribute group
    :param c: points to be allocated in the third attribute group
    :param abia: points to be allocated in the first ability group
    :param abib: points to be allocated in the second ability group
    :param abic: points to be allocated in the third ability group
    :param shuffle: if the first/second/third groups should be shuffled (each)
    :param vamp: if not None, character will be a vampire, int(vamp)
    is the amount of discipline points
    :param back:  background points
    """
    try:
        char = VampireCharacter.makerandom(
            1,
            5,
            int(a),
            int(b),
            int(c),
            int(abia),
            int(abib),
            int(abic),
            int(shuffle),
        )
        if vamp is not None:
            char.makevamprandom(vamp, back)
        if session.get("logged_in", False):
            return render_template(
                "sheets/vampsheet_editor.html",
                character=char.getdictrepr(),
                Clans=VampireCharacter.get_clans(),
                Backgrounds=VampireCharacter.get_backgrounds(),
                New=True,
            )
        return render_template("sheets/vampsheet.html", character=char.getdictrepr())
    except Exception as e:
        flash("ERROR" + "\n".join(e.args))
        raise
