import logging
import os
import re
import sqlite3
import time
import traceback
from contextlib import closing

import markdown
import numexpr
from flask import request, session, g, redirect, url_for, \
    render_template, flash

from NossiSite import app
from fengraph import weapondata

log = logging.Logger("helperlogger")
wikipath = "~/wiki/"


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


wikitags = {}
wikistamp = [0.0]


def wikindex():
    global wikitags
    mds = []
    for p in os.listdir(os.path.expanduser(wikipath)):
        if p.endswith(".md"):
            mds.append(p[:-3])
    return sorted(mds), wikitags


def stream_string(s):
    for l in s:
        yield l


def wikisave(page, author, title, tags, body):
    print("saving ...")
    with open(os.path.expanduser(wikipath + page + ".md"), 'w+') as f:
        f.write("title: " + title + "  \n")
        f.write("tags: " + " ".join(tags) + "  \n")
        f.write(body.replace("\n", ""))
    with open(os.path.expanduser(wikipath) + "control", "a+") as h:
        h.write(page + " edited by " + author + "\n")
    with open(os.path.expanduser(wikipath) + "control", "r") as f:
        print(os.path.expanduser(wikipath) + "control", ":", f.read())
    os.system(os.path.expanduser("~/") + "bin/wikiupdate & ")


def wikiload(page):
    with open(os.path.expanduser(wikipath + page + ".md")) as f:
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


def stream_file(f):
    o = open(f, 'rb')
    try:
        streambytes = o.read(500)
        while streambytes != b'':
            yield streambytes
            streambytes = o.read(500)
        yield streambytes
    finally:
        o.close()


def generate_token():
    if not session['logged_in']:
        raise Exception("Not Logged in.")
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
        if exception.args[0] == "REDIR":
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
        raise Exception("REDIR", redirect(url_for('login', r=request.url)))


@app.errorhandler(Exception)
def internal_error(error: Exception):
    if error.args[0] == "REDIR":
        return error.args[1]
    else:
        logging.exception("Unhandled internal error")
    flash("internal error. sorry", category="error")
    return render_template('show_entries.html'), 500


def weaponadd(weapon_damage_array, b, ind=0):
    if len(weapon_damage_array) != len(b):
        raise Exception("Length mismatch!", weapon_damage_array, b)
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
        raise Exception("Dont know what do do with " + code)


def calculate(calc, par):
    loose_par = [None]
    if par is None:
        par = {}

    else:
        print(par)
        loose_par += [x for x in par.split(",") if ":" not in x]
        par = {x.upper(): y for x, y in [pair.split(":") for pair in par.split(",") if ":" in pair]}
    for k, v in par.items():
        calc = calc.replace(k, v)
    missing = None
    while len(loose_par) > 0:
        try:
            print("PAR:", par,loose_par)
            res = numexpr.evaluate(calc, local_dict=par).item()
            missing = None  # success
            break
        except KeyError as e:
            missing = e
            print("LOOSE:",loose_par)
            par[e.args[0]] = int(loose_par.pop())  # try autofilling
    if missing:
        raise Exception("Parameter " + missing.args[0] + " is missing!")
    print("calcing", calc, res)
    return round(res)


def weapontable(w, mods="", json=False):
    try:
        data = weapondata()
        data = {k.lower(): v for k, v in data.items()}
        weapon = data.get(w.lower(), None)
        if weapon is None:
            raise Exception(w.lower() + " does not exist in " + " ".join(data.keys()))
        for mod in mods.split(","):
            mod = mod.strip()
            if not mod:
                continue
            modregex = re.compile(r"^(?P<direction>[LR])(?P<sharp>X?)(?P<amount>-?\d+)(?P<apply>[HSCB]+)$")
            match = modregex.match(mod)
            if not match:
                raise Exception("Modifier Code " + mod + " does not match the format!")
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
        raise
        return '<div style="color: red"> WeaponCode Invalid: ' + " ".join(e.args) + ' </div>'


def fillweapontables(body):
    def gettable(match):
        return weapontable(match.group(1), match.group(2))

    regex = re.compile(r"\[\[Weapon:(.*?):(.*?)\]\]", re.IGNORECASE)
    return regex.sub(gettable, body)


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
