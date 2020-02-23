import decimal
import errno
import logging
import os
import re
import sqlite3
import time
import traceback
from contextlib import closing
from typing import Tuple, List, Union, Dict
from pathlib import Path

import bleach
import markdown
import numexpr
from flask import request, session, g, redirect, url_for, \
    render_template, flash
from markupsafe import Markup

from NossiPack import User
from NossiPack.FenCharacter import FenCharacter
from NossiPack.krypta import DescriptiveError, write_nonblocking, is_int
from NossiSite import app
from fengraph import weapondata

log = logging.getLogger("frontend")
fh = logging.FileHandler("nossilog.log", mode="w")
fh.setLevel(logging.DEBUG)
log.addHandler(fh)
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')
log.setLevel(logging.DEBUG)
wikipath = Path.home() / "wiki"


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


wikitags = {}
wikistamp = [0.0]


def wikindex() -> Tuple[List[Path], Dict]:
    global wikitags
    mds = []
    for p in wikipath.glob("**/*.md"):
        mds.append(p.relative_to(wikipath))
    return sorted(mds), wikitags


def wikisave(page, author, title, tags, body):
    print("saving ...")
    with (wikipath / (page + ".md")).open('w+') as f:
        f.write("title: " + title + "  \n")
        f.write("tags: " + " ".join(tags) + "  \n")
        f.write(body.replace("\n", ""))
    with (wikipath / "control").open("a+") as h:
        h.write(page + " edited by " + author + "\n")
    with (wikipath / "control").open("r") as f:
        print((wikipath / "control").as_posix() + "control", ":", f.read())
    os.system(os.path.expanduser("~/") + "bin/wikiupdate & ")


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


def update_discord_bindings(user, page):
    u = User(user)
    d = u.config("discord", "not set")
    c = u.config("character_sheet", "")
    if c + "_character" == page and re.match(r".*#\d{4}$", d):
        fifo_name = 'NossiBotBuffer'
        try:
            os.mkfifo(fifo_name)
        except OSError as oe:
            if oe.errno != errno.EEXIST:
                raise
        char = FenCharacter()
        char.load_from_md(*wikiload(page))
        definitions = {}
        for catname, cat in char.Categories.items():
            for secname, sec in cat.items():
                for statname, stat in sec.items():
                    if statname.strip() and is_int(stat):
                        if definitions.get(statname, None) is None:
                            definitions[statname.strip()] = ".".join([catname.strip(), secname.strip(), statname.strip()])
                            definitions[statname.strip().lower()] = statname.strip()
                        definitions[".".join([catname.strip(), secname.strip(), statname.strip()])] = stat.strip()
        data = "\n".join([f"undef {catname}.*" for catname in char.Categories.keys()]+[f"{d} def {k} = {v}" for k, v in definitions.items()])
        write_nonblocking(fifo_name, data)


def generate_token():
    if not session['logged_in']:
        raise DescriptiveError("Not Logged in.")
    return session['print']  # only one token per session for now.


def init_db():
    print("initializing DB")
    with closing(connect_db("initialization")) as db:
        with app.open_resource('../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.template_filter('quoted')
def quoted(s):
    quotedstring = re.findall('\'([^\']*)\'', str(s))
    if quotedstring:
        return quotedstring[0]
    return None


@app.template_filter('remove_leading_underscore')
def underscore_remove(s):
    while s and s[0] == "_":
        s = s[1:]
    return s


@app.template_filter('markdown')
def markdownfilter(s):
    if s is None:
        return ""
    if isinstance(s, str):
        return Markup(markdown.markdown(s, extensions=["tables", "toc", "nl2br"]))
    elif isinstance(s, list):
        next_try = "\n".join(s)
        n = Markup(markdown.markdown(next_try, extensions=["tables", "toc", "nl2br"]))
        return n.split("\n")
    else:
        DescriptiveError("Templating error:" + str(s) + "does not belong")


def connect_db(source):
    try:
        db = getattr(g, 'db', None)
        if db:
            return db
    except:
        pass  # just connect normally
    print("connecting to", app.config['DATABASE'], "from", source)
    return sqlite3.connect(app.config['DATABASE'])


@app.before_request
def before_request():
    g.db = connect_db("before request")
    if len(wikitags.keys()) == 0:
        updatewikitags()


#    try:
#        print(request.remote_addr, " => ", request.path,
#              ">", session.get('user', '?'), "<")
#    except:
#        print("exception while printing before request")

"""
@app.after_request
def after_request(x):
    return x
    try:
        print(request.remote_addr, " done ", request.path,
              ">", session.get('user', '?'), "<")
    except:
        print("exception while printing after request")
    return x"""


@app.teardown_request
def teardown_request(exception: Exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
    if exception:
        if exception.args and exception.args[0] == "REDIR":
            return exception.args[1]
        print("exception caught by teardown:", exception, exception.args)
        traceback.print_exc()


def updatewikitags():
    print("it has been " + str(time.time() - wikistamp[0]) + " seconds since the last wiki indexing")
    wikistamp[0] = time.time()
    for m in wikindex()[0]:
        wikitags[m] = wikiload(m)[1]
    print("index took: " + str(1000 * (time.time() - wikistamp[0])) + " milliseconds")


@app.context_processor
def gettoken():
    gentoken()
    return dict(token=session.get("print", None))


def gentoken():
    return session.get('print', None)


def checklogin():
    if not session.get('logged_in'):
        flash('You are not logged in!')
        raise Exception("REDIR", redirect(url_for('login', r=request.path[1:])))


@app.errorhandler(Exception)
def internal_error(error: Exception):
    if error.args and error.args[0] == "REDIR":
        return error.args[1]
    else:
        if type(error) == DescriptiveError:
            flash(error.args[0])
            logging.exception("Handled Descriptive Error")
            if request.url.endswith("/raw"):
                return error.args[0]
        else:
            flash("internal error. sorry", category="error")
            logging.exception("Unhandled internal error")
    return render_template("show_entries.html")


def weaponadd(weapon_damage_array, b, ind=0):
    if len(weapon_damage_array) != len(b):
        raise DescriptiveError("Length mismatch!", weapon_damage_array, b)
    c = []
    for i in range(len(weapon_damage_array)):
        c.append((weapon_damage_array[i] + [0, 0])[:2])
        c[-1][ind] = max(c[-1][ind] + b[i], 0)
    return c


def magicalweapontable(code: str, par=None, json=False):
    calc = re.compile(r"<(?P<x>.*?)>")
    code = code.strip()
    for match in calc.findall(code):
        code = code.replace(f"<{match}>", str(calculate(match, par)))
    code = re.sub(r"^CODE\s+", "", code)
    step = code.split(":")
    if step[0].strip() == "WEAPON":
        return weapontable(step[1], step[2], json)
    else:
        raise DescriptiveError("Dont know what do do with " + code)


def calculate(calc, par):
    loose_par = [0]  # last pop ends the loop
    if par is None:
        par = {}

    else:
        print(par)
        loose_par += [x for x in par.split(",") if ":" not in x]
        par = {x.upper(): y for x, y in [pair.split(":") for pair in par.split(",") if ":" in pair]}
    for k, v in par.items():
        calc = calc.replace(k, v)
    missing = None
    res = 0
    while len(loose_par) > 0:
        try:
            print("PAR:", par, loose_par)
            res = numexpr.evaluate(calc, local_dict=par, truediv=True).item()
            missing = None  # success
            break
        except KeyError as e:

            missing = e
            print("LOOSE:", loose_par)
            par[e.args[0]] = int(loose_par.pop())  # try autofilling
    if missing:
        raise DescriptiveError("Parameter " + missing.args[0] + " is missing!")
    return decimal.Decimal(res).quantize(1, decimal.ROUND_HALF_UP)


def weapontable(w, mods="", json=False):
    try:
        data = weapondata()
        data = {k.lower(): v for k, v in data.items()}
        weapon = data.get(w.lower(), None)
        if weapon is None:
            raise DescriptiveError(w.lower() + " does not exist in " + " ".join(data.keys()))
        for mod in mods.split(","):
            mod = mod.strip()
            if not mod:
                continue
            modregex = re.compile(r"^(?P<direction>[LR])(?P<sharp>X?)(?P<amount>-?\d+)(?P<apply>[HSCB]+)$")
            match = modregex.match(mod)
            if not match:
                raise DescriptiveError("Modifier Code " + mod + " does not match the format!")
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
                    weapon["Schneiden"] = weaponadd(weapon["Schneiden"], addition, sharp)
                if a == "B":
                    weapon["Schlagen"] = weaponadd(weapon["Schlagen"], addition, sharp)

        for k in list(weapon.keys()):
            if sum(sum(x for x in dmg) for dmg in weapon[k]) == 0:
                weapon.pop(k)
        if json:
            return weapon
        else:
            return markdown.markdown(render_template("weapontable.html",
                                                     data=weapon), extensions=["tables"])
    except Exception as e:
        return '<div style="color: red"> WeaponCode Invalid: ' + " ".join(e.args) + ' </div>'


def fill_infolets(body):
    bleach_ok_list = ["br", "u", "p", "table", "th", "tr", "td",
                      "tbody", "thead", "tfoot", "h2", "h3", "h4", "h5", "h6",
                      "div", "hr"]

    def gettable(match):
        return weapontable(match.group("ref"), match.group("mod"))

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
            article = article[article.find("\n") * hide_headline:]
        return markdown.markdown(bleach.clean(article, tags=bleach_ok_list), extensions=["tables", "toc", "nl2br"])

    def hide(func):
        def hidden(text):
            header = text.group("name") or text.group(0).strip("[]")
            return "<div class=hideable><b> " + header + "</b></div>""<div>" + func(text) + "</div>"

        return hidden

    hiddenweapons = re.compile(r"\[(?P<name>.*?)\[\[weapon:(?P<ref>.+?):(?P<mod>.*?)\]\]\]", re.IGNORECASE)
    weapons = re.compile(r"\[\[weapon:(?P<ref>.+?):(?P<mod>.*?)\]\]", re.IGNORECASE)
    hiddeninfos = re.compile(r"\[(?P<name>.*?)\[\[specific:(?P<ref>.+?)\]\]\]", re.IGNORECASE)
    infos = re.compile(r"\[\[specific:(?P<ref>.+?)\]\]", re.IGNORECASE)
    links = re.compile(r"\[(.+?)\]\((?P<ref>.+?)\)")

    body = links.sub(r'<a href="/wiki/\g<2>"> \g<1> </a>', body)

    body = infos.sub(getinfo, hiddeninfos.sub(hide(getinfo), body))
    return weapons.sub(gettable, hiddenweapons.sub(hide(gettable), body))


def checktoken():
    if request.form.get('token', "None") != session.get("print", None):
        flash("invalid token!")
        session['retrieve'] = request.form
        return False
    else:
        return True


@app.errorhandler(404)
def page_not_found(e):
    if e:
        print(e)
    return render_template('404.html'), 404


def openupdb():
    db = connect_db("opening_DB_UP")
    if db is not None:
        db.close()
