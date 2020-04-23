import decimal
import html
import json
import os
import re
import time
from pathlib import Path
from typing import Tuple, List, Union

import bleach
import markdown
import numexpr
from flask import render_template, request, redirect, url_for, session, flash, abort
from markupsafe import Markup

from NossiPack.FenCharacter import FenCharacter
from NossiPack.User import User, Userlist
from NossiPack.fengraph import weapondata
from NossiPack.krypta import DescriptiveError
from NossiSite.base import app as defaultapp, log
from NossiSite.helpers import checktoken, checklogin

wikipath = Path.home() / "wiki"
wikistamp = [0.0]
wikitags = {}
bleach.ALLOWED_TAGS += [
    "br",
    "u",
    "p",
    "pre",
    "table",
    "th",
    "tr",
    "td",
    "tbody",
    "thead",
    "tfoot",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "div",
    "hr",
]


def register(app=None):
    if app is None:
        app = defaultapp

    @app.route("/index/")
    def wiki_index():
        r = wikindex()
        return render_template(
            "wikindex.html",
            entries=[x.with_suffix("").as_posix() for x in r],
            tags=gettags(),
        )

    @app.route("/wiki", methods=["GET", "POST"])
    @app.route("/wiki/", methods=["GET", "POST"])
    @app.route("/wiki/<path:page>", methods=["GET", "POST"])
    def wikipage(page=None):
        raw = request.url.endswith("/raw")
        if raw:
            page = page[:-4]
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

            body = markdown.markdown(body, extensions=["tables", "toc", "nl2br"])
            body = bleach.clean(body)
            body = fill_infolets(
                body, page[:-10] if page.endswith("_character") else page
            )
            return render_template(
                "wikipage.html", title=title, tags=tags, body=body, wiki=page
            )
        return body, 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.route("/edit/<path:x>", methods=["GET", "POST"])
    def editwiki(x=None):
        checklogin()
        if request.method == "GET":
            try:
                author = ""
                ident = (x,)
                retrieve = session.get("retrieve", None)
                if retrieve:
                    title = retrieve["title"]
                    text = retrieve["text"]
                    tags = retrieve["tags"].split(" ")
                else:
                    title, tags, text = wikiload(x)
                entry = dict(
                    author=author,
                    id=ident,
                    title=title,
                    tags=" ".join(tags),
                    text=text,
                )
                return render_template(
                    "edit_entry.html", mode="wiki", wiki=x, entry=entry
                )
            except FileNotFoundError:
                flash("entry " + str(x) + " not found.")
        if request.method == "POST":
            if checktoken():
                if request.form.get("wiki", None) is not None:
                    log.info(f"saving wiki file {request.form['wiki']}")
                    wikisave(
                        x,
                        session.get("user"),
                        request.form["title"],
                        request.form["tags"].split(" "),
                        request.form["text"],
                    )
                    session["retrieve"] = None
            return redirect(url_for("wikipage", page=request.form.get("wiki", None)))
        return abort(405)

    @app.route("/fenweapongraph")
    def graphtest():
        from NossiPack import fengraph

        fengraph.supply_graphdata()
        return render_template("graphs.html")

    @app.route("/fensheet/<c>")
    def fensheet(c):
        try:
            char = FenCharacter()
            title, tags, body = wikiload(c + "_character")
            body = bleach.clean(body)
            char.load_from_md(title, tags, body)
            body = render_template(
                "fensheet.html",
                character=char,
                userconf=User(session.get("user", "")).configs(),
            )
            return fill_infolets(body.replace("&amp;", "&"), char)
        except DescriptiveError as e:
            flash("Error with character sheet:\n" + e.args[0])
            return redirect(url_for("showsheet", name=c))

    @app.route("/ewsheet/<c>")
    def ewsheet(c):
        try:
            from NossiPack.EWCharacter import EWCharacter

            char = EWCharacter()
            char.load_from_md(*wikiload(c + "_character"))
            body = render_template(
                "endworldsheet.html",
                character=char.Data,
                userconf=User(session.get("user", "")).configs(),
            )
            return fill_infolets(body, c)
        except DescriptiveError as e:
            flash("Error with your configuration value character_sheet: " + e.args[0])
            return redirect(url_for("showsheet", name=c))

    @app.route("/costcalc/all/<costs>/<penalty>")
    @app.route("/costcalc/all/<costs>/<penalty>/<width>")
    def ddos(costs, penalty, width=3):
        p = Path(costs + "-" + penalty + ".result")
        try:
            if p.exists():
                with open(p, "r") as f:
                    return f.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}
            start = time.time()
            if (
                int(costs.split(",")[-1]) * 3
                + sum(int(x) for x in penalty.split(",")) * 3
                > 10000
            ):
                raise AttributeError("just too large of a space")
            with open(p, "w") as f:
                res = [["[0]", "[0]"]]
                i = 0
                while not all(
                    all(int(x) >= 5 for x in y.strip("[]").split(",") if x)
                    for y in res[-1][1]
                ):
                    r = FenCharacter.cost_calc(str(i), costs, penalty, width)
                    log.debug(f"Fencalc {i} {res}")
                    if i == 0 or r != res[-1][1]:
                        res.append([(str(i) + "   ")[:4] + " : ", r])
                    if time.time() - start > 30:
                        raise TimeoutError()
                    i += 1
                    print(res[-1][1])
                r = "\n".join(x[0] + "\t".join(x[1]) for x in res[1:])
                f.write(r)
                return r, 200, {"Content-Type": "text/plain; charset=utf-8"}
        except:
            with open(p, "w") as f:
                f.write("an error has previously occured and this request is blocked")
                return (
                    "error, this request is now blocked",
                    200,
                    {"Content-Type": "text/plain; charset=utf-8"},
                )

    @app.route("/costcalc/<inputstring>/<costs>/<penalty>/<width>")
    @app.route("/costcalc/<inputstring>/<costs>/<penalty>")
    @app.route("/costcalc/<inputstring>")
    def fen_calc(inputstring: str, costs=None, penalty=None, width=3):
        return (
            "\t".join(FenCharacter.cost_calc(inputstring, costs, penalty, width)),
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
        a = gettags()
        tags = {t: v for t, v in a.items() if tag in v}
        entries = [e for e in r if e in tags.keys()]
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
        try:
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
        except Exception as e:
            if format_txt:
                return " ".join(e.args)
            if format_json:
                return {"error": e}
            raise

        return weapon


def weaponadd(weapon_damage_array, b, ind=0):
    if len(weapon_damage_array) != len(b):
        raise DescriptiveError("Length mismatch!", weapon_damage_array, b)
    c = []
    for i, w in enumerate(weapon_damage_array):
        c.append((w + [0, 0])[:2])
        c[-1][ind] = max(c[-1][ind] + b[i], 0)
    return c


def magicalweapontable(code: str, par=None, as_json=False, context=None):
    calc = re.compile(r"<(?P<x>.*?)>")
    code = code.strip()
    for match in calc.findall(code):
        code = code.replace(f"<{match}>", str(calculate(match, par)))
    code = re.sub(r"^CODE\s+", "", code)
    step = code.split(":")
    if step[0].strip() == "WEAPON":
        return weapontable(step[1], step[2], as_json, context)
    raise DescriptiveError("Dont know what do do with \n" + code)


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
    missing = None
    res = 0
    while len(loose_par) > 0:
        try:
            res = numexpr.evaluate(calc, local_dict=par, truediv=True).item()
            missing = None  # success
            break
        except KeyError as e:
            missing = e
            par[e.args[0]] = int(loose_par.pop())  # try autofilling
    if missing:
        if missing.args[0] == "em":
            raise DescriptiveError("Parameter " + missing.args[0] + " is missing!")
        raise DescriptiveError("Parameter " + missing.args[0] + " is missing!")
    return decimal.Decimal(res).quantize(1, decimal.ROUND_HALF_UP)


def weapontable(w, mods="", as_json=False, context: FenCharacter = None):
    try:
        mods = html.unescape(mods)
        if context:
            for k, v in context.stat_definitions().items():
                mods = mods.replace(k, v)
        calc = re.compile(r"<(?P<x>.*?)>")
        mods = mods.strip()

        for match in calc.findall(mods):
            try:
                mods = mods.replace(f"<{match}>", str(calculate(match)))
            except SyntaxError:
                raise DescriptiveError(f"{mods} is not correct!")
        data = weapondata()
        data = {k.lower(): v for k, v in data.items()}
        weapon = data.get(w.lower(), None)
        if weapon is None:
            raise DescriptiveError(
                w.lower() + " does not exist in " + " ".join(data.keys())
            )
        for mod in mods.split(","):
            mod = mod.strip()
            if not mod:
                continue
            modregex = re.compile(
                r"^(?P<direction>[LR])\s*(?P<sharp>X?)\s*(?P<amount>-?\d+)\s*(?P<apply>[HSCB]+)$"
            )
            match = modregex.match(mod)
            if not match:
                raise DescriptiveError(
                    "Modifier Code " + mod + " does not match the format!"
                )
            match = match.groupdict()
            if match["direction"] == "L":
                direction = -1
                pos = 10
            elif match["direction"] == "R":
                direction = 1
                pos = 1
            else:
                continue
            sharp = 1 if match.get("sharp", None) else 0
            amount = int(match["amount"])
            apply = match["apply"]
            addition = [0] * 12
            inc = 1 if amount > 0 else -1
            while amount != 0:
                amount -= inc
                addition[pos] += inc
                pos += direction
                pos = 10 if pos == 0 else (1 if pos == 11 else pos)

            for a in apply:
                if a == "H":
                    weapon["Hacken"] = weaponadd(weapon["Hacken"], addition, sharp)
                if a == "S":
                    weapon["Stechen"] = weaponadd(weapon["Stechen"], addition, sharp)
                if a == "C":
                    weapon["Schneiden"] = weaponadd(
                        weapon["Schneiden"], addition, sharp
                    )
                if a == "B":
                    weapon["Schlagen"] = weaponadd(weapon["Schlagen"], addition, sharp)

        for k in list(weapon.keys()):
            if sum(sum(x for x in dmg) for dmg in weapon[k]) == 0:
                weapon.pop(k)
        if as_json:
            return weapon
        return markdown.markdown(
            render_template("weapontable.html", data=weapon), extensions=["tables"]
        )
    except Exception as e:
        return (
            '<div style="color: red"> WeaponCode Invalid: '
            + " ".join(str(html.escape(x)) for x in e.args)
            + " </div>"
        )


def fill_infolets(body, context=None):
    def gettable(match):
        return weapontable(match.group("ref"), match.group("mod"), context=context)

    def getinfo(match):
        a = match.group("ref").split(":")
        if a[-1] == "-":
            a = a[:-1]
            hide_headline = 1
        else:
            hide_headline = 0
        try:
            article: str = wikiload(a[0])[-1]
        except DescriptiveError as e:
            flash(e.args[0])
            article = ""
        for seek in a[1:]:
            article = traverse_md(article, seek)
        if not article:
            article = "[[not found]]"
        elif hide_headline:
            article = article[article.find("\n") * hide_headline :]
        return markdown.markdown(
            bleach.clean(article), extensions=["tables", "toc", "nl2br"],
        )

    def hide(func):
        def hidden(text):
            header = text.group("name") or text.group(0).strip("[]")
            try:
                return (
                    "<div class=hideable><b> " + header + "</b></div>"
                    "<div>" + func(text) + "</div>"
                )
            except Exception as e:
                return f"Error with {header}:\n  {e.args} !"

        return hidden

    hiddenweapons = re.compile(
        r"\[(?P<name>.*?)\[\[weapon:(?P<ref>.+?):(?P<mod>.*?)\]\]\]", re.IGNORECASE
    )
    weapons = re.compile(r"\[\[weapon:(?P<ref>.+?):(?P<mod>.*?)\]\]", re.IGNORECASE)
    hiddeninfos = re.compile(
        r"\[(?P<name>.*?)\[\[specific:(?P<ref>.+?)\]\]\]", re.IGNORECASE
    )
    infos = re.compile(r"\[\[specific:(?P<ref>.+?)\]\]", re.IGNORECASE)
    links = re.compile(r"\[(.+?)\]\((?P<ref>.+?)\)")

    body = links.sub(r'<a href="/wiki/\g<2>"> \g<1> </a>', body)

    body = infos.sub(getinfo, hiddeninfos.sub(hide(getinfo), body))
    return weapons.sub(gettable, hiddenweapons.sub(hide(gettable), body))


def traverse_md(md: str, seek: str) -> str:
    result = ""
    level = 0
    for line in md.split("\n"):
        line = line.strip()
        if line.startswith("#") or level:
            current_level = len(line) - len(line.lstrip("#"))
            if current_level and level >= current_level:
                level = 0
                continue
            if level or line.lstrip("#").strip().upper() == seek.upper():
                if not level:
                    level = current_level
                result += line + "\n"
    return result


def wikiload(page: Union[str, Path]) -> Tuple[str, List[str], str]:
    try:
        if isinstance(page, str):
            p = wikipath / (page + ".md")
        else:
            p = wikipath / page.with_suffix(".md")
        with p.open() as f:
            mode = "meta"
            title = ""
            tags = []
            body = ""
            for line in f.readlines():
                if mode and line.startswith("tags:"):
                    tags += [t for t in line.strip("tags:").strip().split(" ") if t]
                    continue
                if mode and line.startswith("title:"):
                    title = line.strip("title:").strip()
                    continue
                if mode and not line.strip():
                    mode = ""
                body += line
            return title, tags, body
    except FileNotFoundError:
        raise DescriptiveError(page + " not found in wiki.")


def wikisave(page, author, title, tags, body):
    print(f"saving {page} ...")
    with (wikipath / (page + ".md")).open("w+") as f:
        f.write("title: " + title + "  \n")
        f.write("tags: " + " ".join(tags) + "  \n")
        f.write(body.replace("\r", ""))
    with (wikipath / "control").open("a+") as h:
        h.write(page + " edited by " + author + "\n")
    with (wikipath / "control").open("r") as f:
        print((wikipath / "control").as_posix() + "control", ":", f.read())
    os.system(os.path.expanduser("~/") + "bin/wikiupdate & ")
    updatewikitags()


def wikindex() -> List[Path]:
    mds = []
    for p in wikipath.glob("**/*.md"):
        mds.append(p.relative_to(wikipath))
    return sorted(mds)


def gettags():
    if not wikitags:
        updatewikitags()
    return wikitags


def updatewikitags():
    print(
        "it has been "
        + str(time.time() - wikistamp[0])
        + " seconds since the last wiki indexing"
    )
    wikistamp[0] = time.time()
    for k in list(wikitags.keys()):
        del wikitags[k]  # reset everything
    for m in wikindex():
        wikitags[m.stem] = wikiload(m)[1]
    print("index took: " + str(1000 * (time.time() - wikistamp[0])) + " milliseconds")


def load_fen_char(c):
    char = FenCharacter()
    char.load_from_md(*wikiload(c + "_character"))
    return char.stat_definitions()


def load_user_char(user):
    u = User(user)
    d = u.config("discord", "not set")
    c = u.config("character_sheet", "")
    if re.match(r".*#\d{4}$", d):
        return load_fen_char(c)
