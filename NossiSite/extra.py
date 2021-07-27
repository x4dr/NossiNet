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
)

from NossiPack.Cards import Cards
from NossiPack.User import Userlist
from NossiPack.VampireCharacter import VampireCharacter
from NossiPack.krypta import DescriptiveError
from NossiSite.base import app as defaultapp, log
from NossiSite.helpers import checklogin


def register(app=None):
    if app is None:
        app = defaultapp

    @app.route("/setfromsource/")
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
                "Sorry "
                + session.get("user").capitalize()
                + ", I can not let you do that."
            )
        return redirect(url_for("charsheet"))

    @app.route("/timetest")
    def timetest():
        return str(time.time())

    @app.route("/boardgame<int:size>_<seed>.json")
    @app.route("/boardgame<int:size>_.json")
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
                    yield ("" if notfirst() else ",") + '{ "x":%d, "y":%d, ' % (
                        x,
                        y,
                    ) + ",".join(
                        cell(
                            # x, y
                        )
                    ) + "}"
                yield "]"
            yield "]}"

        return Response(generate(), mimetype="text/json")

    @app.route("/gameboard/<int:size>/")
    @app.route("/gameboard/<int:size>/<seed>")
    def gameboard(size, seed=""):
        if size > 20:
            size = 20
        return render_template("gameboard.html", size=size, seed=seed)

    @app.route("/chargen/standard")
    def standardchar():
        return redirect(
            url_for("chargen", a=3, b=5, c=7, abia=5, abib=9, abic=13, shuffle=1)
        )

    @app.route("/cards/", methods=["GET"])
    @app.route("/cards/<command>", methods=["POST", "GET"])
    def cards(command: str = None):
        checklogin()
        deck = Cards.getdeck(session["user"])
        try:
            if request.method == "GET":
                if command is None:
                    return deck.serialized_parts
            elif request.method == "POST":
                par = request.get_json()["parameter"]
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

            return render_template("cards.html", cards=deck)
        except DescriptiveError as e:
            return {"result": "error", "error": e.args[0]}
        except TypeError:
            return {"result": "error", "error": "Parameter is not in a valid Format"}
        finally:
            Cards.savedeck(session["user"], deck)

    @app.route("/chargen", methods=["GET", "POST"])
    def chargen_menu():
        if request.method == "POST":
            f = dict(request.form)
            if not f.get("vampire", None):
                return redirect(
                    url_for(
                        "chargen",
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
                    "chargen",
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
        return render_template("generate_dialog.html")

    @app.route("/chargen/<a>,<b>,<c>,<abia>,<abib>,<abic>,<shuffle>")
    @app.route("/chargen/<a>,<b>,<c>,<abia>,<abib>,<abic>,<shuffle>,<vamp>,<back>")
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
            print(vamp)
            if vamp is not None:
                char.makevamprandom(vamp, back)
            print(char.getdictrepr())
            if session.get("logged_in", False):
                return render_template(
                    "vampsheet_editor.html",
                    character=char.getdictrepr(),
                    Clans=VampireCharacter.get_clans(),
                    Backgrounds=VampireCharacter.get_backgrounds(),
                    New=True,
                )
            return render_template("vampsheet.html", character=char.getdictrepr())
        except Exception as e:
            flash("ERROR" + "\n".join(e.args))
            raise
