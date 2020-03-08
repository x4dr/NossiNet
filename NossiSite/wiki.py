import json
from pathlib import Path

import bleach
import markdown
from flask import render_template, request, redirect, url_for, session, flash, abort
from markupsafe import Markup

from NossiPack.FenCharacter import FenCharacter
from NossiPack.User import User, Userlist
from NossiPack.krypta import DescriptiveError
from NossiSite.base import app as defaultapp
from NossiSite.helpers import (
    wikindex,
    wikiload,
    fill_infolets,
    magicalweapontable,
    weapontable,
    traverse_md,
    log,
)


def register(app=None):
    if app is None:
        app = defaultapp

    @app.route("/index/")
    def wiki_index():
        r = wikindex()
        return render_template(
            "wikindex.html",
            entries=[x.with_suffix("").as_posix() for x in r[0]],
            tags=r[1],
        )

    @app.route("/wiki", methods=["GET", "POST"])
    @app.route("/wiki/<path:page>", methods=["GET", "POST"])
    def wikipage(page=None):
        raw = request.url.endswith("/raw")
        if raw:
            page = page[:4]
        if page is None:
            page = request.form.get("n", None)
            if page is None:
                return wiki_index()
            return redirect(url_for("wikipage", page=page))
        try:
            page = page.lower()
            title, tags, body = wikiload(page)
        except DescriptiveError as e:
            if str(e.args[0]) != page + " not found in wiki.":
                raise
            if session.get("logged_in"):
                entry = dict(id=0, text="", tags="", author=session.get("user"))
                return render_template(
                    "edit_entry.html", mode="wiki", wiki=page, entry=entry
                )
            flash("That page doesn't exist. Log in to create it!")
            return redirect(url_for("wiki_index"))
        if not raw:
            body = bleach.clean(body)
            body = Markup(
                markdown.markdown(body, extensions=["tables", "toc", "nl2br"])
            )
            body = fill_infolets(body)
            return render_template(
                "wikipage.html", title=title, tags=tags, body=body, wiki=page
            )
        return body

    @app.route("/fenweapongraph")
    def graphtest():
        from NossiPack import fengraph

        fengraph.supply_graphdata()
        return render_template("graphs.html")

    @app.route("/fensheet/<c>")
    def fensheet(c):
        try:
            char = FenCharacter()
            char.load_from_md(*wikiload(c + "_character"))
            body = render_template(
                "fensheet.html",
                character=char,
                userconf=User(session.get("user", "")).configs(),
            )
            return fill_infolets(body)
        except DescriptiveError as e:
            flash("Error with your configuration value character_sheet: " + e.args[0])
            return redirect(url_for("showsheet", name=c))

    @app.route("/costcalc/all/<costs>/<penalty>")
    def ddos(costs, penalty):
        p = Path(costs + "-" + penalty + ".result")
        try:
            if p.exists():
                with open(p, "r") as f:
                    return f.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}

            with open(p, "w") as f:
                res = []
                for i in range(9001):
                    r = fen_calc(str(i), costs, penalty)
                    log.debug(f"Fencalc {i} {res}")
                    if i == 0 or r != res[-1][1]:
                        res.append([(str(i) + "   ")[:4] + " : ", r])
                r = "\n".join(x[0] + x[1] for x in res)
                f.write(r)
                return r, 200, {"Content-Type": "text/plain; charset=utf-8"}
        except:
            with open(p, "w") as f:
                f.write("an error has previously occured and this request is blocked")
                return (
                    "error, this request is blocked",
                    200,
                    {"Content-Type": "text/plain; charset=utf-8"},
                )

    @app.route("/costcalc/<inputstring>/<costs>/<penalty>")
    @app.route("/costcalc/<inputstring>")
    def fen_calc(inputstring: str, costs=None, penalty=None):

        if costs is not None:
            costs = [int(x) for x in costs.split(",")]
        else:
            costs = [0, 15, 35, 60, 100]
        if penalty is not None:
            penalty = [int(x) for x in penalty.split(",")]
        else:
            penalty = [0, 0, 0, 50, 100]
        xp = [int(x) for x in inputstring.split(",")]
        if len(xp) == 1:
            xp = xp[0]
            allconf = {
                (a, b, c) for a in range(5) for b in range(a + 1) for c in range(b + 1)
            }
            correct = [
                [x[0] + 1, x[1] + 1, x[2] + 1]
                for x in allconf
                if FenCharacter.cost(x, costs, penalty) <= xp
            ]
            i = 0
            j = len(correct)
            maximal = correct[:]
            while i < j:
                for u in range(len(maximal[i])):
                    upg = list(maximal[i])
                    upg[u] = upg[u] + 1
                    # upg = tuple(upg)
                    if upg in correct:
                        del maximal[i]
                        i -= 1
                        j -= 1
                        break
                i += 1
            return (
                "\t".join(str(c) for c in maximal),
                200,
                {"Content-Type": "text/plain; charset=utf-8"},
            )
        return (
            str(FenCharacter.cost(tuple(x - 1 for x in xp), costs, penalty)),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    @app.route("/weapon/<w>")
    @app.route("/weapon/<w>/<mods>")
    @app.route("/weapon/<w>/json")
    @app.route("/weapon/<w>/<mods>/json")
    @app.route("/weapon/<w>/<mods>/txt")
    @app.route("/weapon/<w>/txt")
    def show_weapontable(w, mods=""):
        format_json = request.url.endswith("/json")
        format_txt = request.url.endswith("/txt")
        w = w.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
        weapon = weapontable(w, mods, format_json or format_txt)
        if format_txt:
            return format_weapon(weapon)
        return weapon

    def format_weapon(weapon_tab):
        result = f"{'Wert': <11}" + "".join(f"{x: <4}" for x in range(1, 11)) + "\n"
        for key, weapon in weapon_tab.items():
            weapon = [
                x if (len(x) > 1 and x[1] > 0) else ([x[0]] if x[0] else "")
                for x in weapon
            ]
            result += (
                f"{key: <10} "
                + "".join(f"{';'.join(str(y) for y in x): <4}" for x in weapon[1:-1])
                + "\n"
            )
        return result

    @app.route("/specific/<a>")
    @app.route("/specific/<a>/raw")
    def specific(a: str):
        parse_md = not request.url.endswith("/raw")
        a = a.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
        a = a.split(":")
        if a[-1] == "-":
            a = a[:-1]
            hide_headline = 1
        else:
            hide_headline = 0

        article: str = wikiload(a[0])[-1]
        for seek in a[1:]:
            article = traverse_md(article, seek)
        if not article:
            article = "not found"
        else:
            article = article[article.find("\n") * hide_headline :]
        if parse_md:
            return Markup(
                markdown.markdown(article, extensions=["tables", "toc", "nl2br"])
            )
        return article

    @app.route("/bytag/<tag>")
    def tagsearch(tag):
        r = wikindex()
        heads = []
        a = r[1]
        tags = {t: v for t, v in a.items() if tag in v}
        entries = [e for e in r[0] if e in tags.keys()]
        return render_template("wikindex.html", entries=entries, tags=tags, heads=heads)

    @app.route("/char_access/<path:x>")
    def char_access(x):
        selection_path = x.split(".")
        discord = request.cookies.get("discord", "")
        ul = Userlist()
        u = ul.loaduserbyname(selection_path[0])
        if u:
            u = ul.loaduserbyname(session.get("user"))
            if discord.strip() and u.config("discord") != discord:
                abort(403)
            char = u.getsheet()
        else:
            c = wikiload(selection_path[0] + "_character")
            char = FenCharacter()
            char.load_from_md(*c)
        d = char.getdictrepr()
        for x_part in selection_path[1:]:
            if x_part in d.keys():
                d = d[x_part]  # accesses parts of character, dict of dicts
            else:
                d = {
                    "error": "could not find d in current selection",
                    "current selection": d,
                }
                break
        return app.response_class(
            json.dumps(d, indent=2, ensure_ascii=False) + "\n",
            mimetype=app.config["JSONIFY_MIMETYPE"],
        )

    @app.route("/magicalweapon/<w>")
    @app.route("/magicalweapon/<w>/<par>")
    @app.route("/magicalweapon/<w>/json")
    @app.route("/magicalweapon/<w>/<par>/json")
    @app.route("/magicalweapon/<w>/<par>/txt")
    @app.route("/magicalweapon/<w>/txt")
    def magicweapons(w, par=None):
        format_json = request.url.endswith("/json")
        format_txt = request.url.endswith("/txt")
        w = w.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
        code = wikiload("magicalweapons")[-1].upper()
        if w.upper() in code:
            code = code[code.find(w.upper()) :]  # find the right headline
            code = code[code.find("\n") + 1 :]  # skip over the newline
            code = code[: code.find("\n")]  # code should be on the next line
        else:
            raise DescriptiveError(w.upper() + "not found in " + code)
        weapon = magicalweapontable(code, par, format_json or format_txt)
        if format_txt:
            return format_weapon(weapon)
        return weapon
