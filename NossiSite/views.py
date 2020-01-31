import json
import random
import time
from pathlib import Path
from typing import List, Tuple

import bleach
import markdown
from flask import Response, abort
from markupsafe import Markup
from werkzeug.security import gen_salt, generate_password_hash

from NossiPack.FenCharacter import FenCharacter
from NossiPack.User import Userlist, User
from NossiPack.VampireCharacter import VampireCharacter
from NossiPack.krypta import DescriptiveError
from NossiSite import app, helpers
from NossiSite.helpers import g, session, checktoken, request, redirect, url_for, \
    render_template, flash, init_db, wikiload, wikindex, wikisave, checklogin, fill_infolets, traverse_md, log

bleach.ALLOWED_TAGS += ["br", "u", "p", "table", "th", "tr", "td", "tbody", "thead", "tfoot"]

init_db()


@app.route('/setfromsource/')
def setfromsource():
    checklogin()
    source = request.args.get('source')
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    try:
        new = VampireCharacter()
        if new.setfromdalines(source[-7:]):
            u.sheet = new
            ul.saveuserlist()
            flash("character has been overwritten with provided Dalines sheet!")
        else:
            new = FenCharacter()
            char = wikiload(source + "_character")
            if char:
                new.load_from_md(char[0], char[1], char[2])
                u.sheet = new
                ul.saveuserlist()
            else:
                flash("Problem with provided sheet source!")
    except Exception:
        log.exception("setfromsource:")
        flash("Sorry " + session.get('user').capitalize() + ", I can not let you do that.")

    return redirect(url_for('charsheet'))


@app.route('/')
def show_entries():
    cur = g.db.execute('SELECT author, title, text, id, tags FROM entries ORDER BY id DESC')
    entries = [dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in
               cur.fetchall()]
    for e in entries:
        skip = True
        if session.get("logged_in") and session.get("tags"):
            for t in session.get("tags").split(" "):
                if t in e.get("tags", "").split(" "):
                    skip = False
        else:
            if "default" in (e.get("tags") if e.get("tags") else "").split(" "):
                skip = False
        if skip:
            e["author"] = e.get("author").lower()  # "delete" nonmatching tags
        e['text'] = bleach.clean(e['text'].replace("\n", "<br>"))
        e['own'] = (session.get('logged_in')) and (session.get('user') == e['author'])
    entries = [e for e in entries if e.get('author', "none")[0].isupper()]  # dont send out lowercase authors (deleted)

    return render_template('show_entries.html', entries=entries)


@app.route('/index/')
def wiki_index():
    r = wikindex()
    heads = []
    return render_template("wikindex.html", entries=r[0], tags=r[1], heads=heads)


@app.route('/wiki', methods=["GET", "POST"])
@app.route('/wiki/<page>', methods=["GET", "POST"])
@app.route('/wiki/<page>/<raw>', methods=["GET"])
def wikipage(page=None, raw=None):
    if page is None:
        page = request.form.get('n', None)
        if page is None:
            return wiki_index()
        return redirect(url_for("wikipage", page=page))
    try:
        page = page.lower()
        title, tags, body = wikiload(page)
    except DescriptiveError as e:
        if str(e.args[0]) != page + " not found in wiki.":
            raise
        if session.get('logged_in'):
            entry = dict(id=0, text="", tags="", author=session.get('user'))
            return render_template("edit_entry.html", mode="wiki", wiki=page, entry=entry
                                   )
        else:
            flash("That page doesn't exist. Log in to create it!")

            return redirect(url_for("wiki_index"))
    if raw != "raw":
        body = bleach.clean(body)
        body = Markup(markdown.markdown(body, extensions=["tables", "toc", "nl2br"]))
        body = fill_infolets(body)
        return render_template("wikipage.html", title=title, tags=tags, body=body, wiki=page)
    else:
        return body


@app.route('/edit/<x>', methods=["GET", "POST"])
def editentries(x=None):
    checklogin()
    if request.method == "GET":
        if x == "all":
            cur = g.db.execute('SELECT author, title, text, id, tags '
                               'FROM entries WHERE UPPER(author) LIKE UPPER(?)', [session.get('user')])
            entries = [dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row
                       in
                       cur.fetchall()]

            return render_template('show_entries.html', entries=entries, edit=True)
        try:
            x = int(x)
            cur = g.db.execute('SELECT author, title, text, id, tags '
                               'FROM entries WHERE id == ?', [x])
            entry = [dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in
                     cur.fetchall()][0]
            if (session.get("user").upper() == entry['author'].upper()) or session.get('admin'):

                return render_template('edit_entry.html', mode="blog", entry=entry)
            else:
                flash("not authorized to edit id" + str(x))
        except ValueError:
            try:
                author = ""
                ident = x,
                retrieve = session.get("retrieve", None)
                if retrieve:
                    title = retrieve['title']
                    text = retrieve['text']
                    tags = retrieve['tags'].split(" ")
                else:
                    title, tags, text = wikiload(x)
                entry = dict(author=author, id=ident, title=title, tags=" ".join(tags), text=text)
                return render_template('edit_entry.html', mode="wiki", wiki=x, entry=entry)
            except FileNotFoundError:
                flash("entry " + str(x) + " not found.")
        return redirect(url_for('editentries', x="all"))
    if request.method == "POST":
        log.info(f"{session.get('user', '?')} editing id  {request.form['id']} {request.form}")
        if request.form["id"] == "new":
            add_entry()
        if checktoken():
            if request.form.get("wiki", None) is not None:
                log.info(f"saving wiki file {request.form['wiki']}")
                wikisave(request.form['wiki'].lower(), session.get('user'), request.form['title'],
                         request.form['tags'].split(" "), request.form['text'])
                session["retrieve"] = None
                return redirect(url_for("wikipage", page=request.form['wiki']))

            cur = g.db.execute('SELECT author, title, text, id, tags '
                               'FROM entries WHERE id == ?', [int(request.form['id'])])
            entry = [dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in
                     cur.fetchall()][0]
            if (session.get('user').upper() == entry['author'].upper()) or session.get('admin'):
                log.info(f"{session.get('user', '?')} editing id {request.form['id']} {request.form}")
                g.db.execute('UPDATE entries SET title=?, text=?, tags=? WHERE id == ?',
                             [request.form['title'], request.form['text'], request.form['tags'], request.form['id']])
                session["retrieve"] = None
                g.db.commit()
                flash('entry was successfully edited')
            else:
                flash("not authorized: " + session.get('user').upper() + "!=" + entry['author'].upper())
        else:
            flash("go back and try again")
        return redirect(url_for('show_entries'))


@app.route('/update_filter/', methods=["POST"])
def update_filter():
    if checktoken() and session.get('logged_in'):
        session['tags'] = request.form['tags']
    return redirect(url_for("show_entries"))


@app.route('/fensheet/<c>')
def fensheet(c):
    char = FenCharacter()
    char.load_from_md(*wikiload(c + "_character"))
    body = render_template("fensheet.html", character=char)
    return fill_infolets(body)


@app.route('/weapon/<w>')
@app.route('/weapon/<w>/<mods>')
@app.route('/weapon/<w>/json')
@app.route('/weapon/<w>/<mods>/json')
@app.route('/weapon/<w>/<mods>/txt')
@app.route('/weapon/<w>/txt')
def weapontable(w, mods=""):
    format_json = request.url.endswith("/json")
    format_txt = request.url.endswith("/txt")
    w = w.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
    weapon = helpers.weapontable(w, mods, format_json or format_txt)
    if format_txt:
        return format_weapon(weapon)
    return weapon


def format_weapon(weapon):
    result = f"{'Wert': <11}" + "".join(f"{x: <4}" for x in range(1, 11)) + "\n"
    for key in weapon.keys():
        weapon[key] = [x if (len(x) > 1 and x[1] > 0) else ([x[0]] if x[0] else "") for x in
                       weapon[key]]
        result += f"{key: <10} " + "".join(f"{';'.join(str(y) for y in x): <4}" for x in weapon[key][1:-1]) + "\n"
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
        article = article[article.find("\n") * hide_headline:]
    if parse_md:
        return Markup(markdown.markdown(article, extensions=["tables", "toc", "nl2br"]))
    else:
        return article


@app.route('/magicalweapon/<w>')
@app.route('/magicalweapon/<w>/<par>')
@app.route('/magicalweapon/<w>/json')
@app.route('/magicalweapon/<w>/<par>/json')
@app.route('/magicalweapon/<w>/<par>/txt')
@app.route('/magicalweapon/<w>/txt')
def magicweapons(w, par=None):
    format_json = request.url.endswith("/json")
    format_txt = request.url.endswith("/txt")
    w = w.replace("Ã¤", "ä").replace("ã¶", "ö").replace("ã¼", "ü")
    code = wikiload("magicalweapons")[-1].upper()
    if w.upper() in code:
        code = code[code.find(w.upper()):]  # find the right headline
        code = code[code.find("\n") + 1:]  # skip over the newline
        code = code[:code.find("\n")]  # code should be on the next line
    else:
        raise DescriptiveError(w.upper(), "not foundin ", code)
    weapon = helpers.magicalweapontable(code, par, format_json or format_txt)
    if format_txt:
        return format_weapon(weapon)
    return weapon


@app.route('/bytag/<tag>')
def tagsearch(tag):
    r = wikindex()
    heads = []
    a = r[1]
    tags = {t: v for t, v in a.items() if tag in v}
    entries = [e for e in r[0] if e in tags.keys()]
    return render_template("wikindex.html", entries=entries, tags=tags, heads=heads)


@app.route("/change_discord", methods=["GET", "POST"])
def change_discord():
    checklogin()
    if request.method == "GET":
        return render_template("change_discord.html")
    else:
        ul = Userlist()
        u = ul.loaduserbyname(session.get('user'))
        u.discord = request.form["discord"]
        ul.saveuserlist()
        return redirect(url_for('show_user_profile', username=u.username))


@app.route('/charactersheet/')
def charsheet():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    sheet = u.sheet.getdictrepr()
    if sheet["Type"] == "OWOD":
        return render_template('vampsheet.html', character=sheet, own=True)
    elif sheet["Type"] == "FEN":
        return render_template('fensheet.html', character=u.sheet, own=True)
    else:
        error = "unrecognized sheet format"
        return render_template('vampsheet.html', character=sheet, error=error, own=True)


@app.route('/showsheet/<name>')
def showsheet(name="None"):
    checklogin()
    if name == "None":
        return "error"
    name = name.upper()
    ul = Userlist()
    u = ul.loaduserbyname(name)
    if u:
        if u.sheetpublic or session.get('admin', False):
            return render_template('vampsheet.html', character=u.sheet.getdictrepr(), own=False)
        else:
            return render_template('vampsheet.html', character=VampireCharacter().getdictrepr(), own=False)
    else:
        abort(404)


@app.route('/deletesheet/', methods=["POST"])
def del_sheet():
    checklogin()
    x = int(request.form["sheetnum"])
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    u.oldsheets.pop(x)
    ul.saveuserlist()
    flash("Sheet deleted from history!")
    return redirect(url_for('menu_oldsheets'))


@app.route('/restoresheet/', methods=["POST"])
def res_sheet():
    checklogin()
    x = int(request.form["sheetnum"])
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    newactive = u.oldsheets.pop(x)
    u.oldsheets.append(u.sheet)
    u.sheet = newactive
    ul.saveuserlist()
    flash("Sheet deleted from history!")
    return redirect(url_for('menu_oldsheets'))


@app.route('/berlinmap')
def berlinmap():
    return render_template('map.html')
    # return redirect("https://www.google.com/maps/d/viewer?mid=1TH6vryHyVxv_xFjFJDXgXQegZO4")


@app.route('/berlinmap/data.dat')
def mapdata():
    log.debug("generating mapdata")
    time0 = time.time()
    cur = g.db.execute('SELECT name, owner,tags,data FROM property')
    plzs = {}
    for row in cur.fetchall():
        plzs[row[0]] = {'owner': row[1] or "", 'tags': row[2] or "", 'data': row[3] or ""}
    cur = g.db.execute('SELECT name, faction, allegiance, clan, tags FROM actors')
    for row in cur.fetchall():
        for plz in plzs.keys():
            if plzs[plz]['owner'].upper() == row[0]:
                plzs[plz]['tags'] += " ".join([x for x in row[1:] if x])
                if row[1]:
                    plzs[plz]['faction'] = row[1]
    log.debug(f"took: {time.time() - time0} seconds.")
    return json.dumps(plzs)


@app.route('/oldsheets/')
def menu_oldsheets():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    oldsheets = []
    xpdiffs = []
    for i in range(len(u.oldsheets)):
        oldsheets.append(u.oldsheets[i].timestamp)
        if i > 0:
            xpdiffs.append(u.oldsheets[i].get_diff(u.oldsheets[i - 1]))
        else:
            xpdiffs.append(u.oldsheets[i].get_diff(None))
    return render_template('oldsheets.html', oldsheets=oldsheets, xpdiffs=xpdiffs)


@app.route('/showoldsheets/<x>')
def showoldsheets(x):
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    try:
        sheetnum = int(x)
    except:
        return redirect(url_for('/oldsheets/'))
    return render_template('vampsheet.html', character=u.oldsheets[sheetnum].getdictrepr(), oldsheet=x)


@app.route('/new_fen_sheet/', methods=['GET'])
def new_fen_sheet():
    checklogin()
    return render_template('fensheet_editor_new.html', character=FenCharacter())


@app.route('/new_vamp_sheet/', methods=['GET'])
def new_vamp_sheet():
    checklogin()
    return render_template('vampsheet_editor.html', character=VampireCharacter())


@app.route("/fencalc/all/<costs>/<penalty>")
def ddos(costs, penalty):
    p = Path(costs + "-" + penalty + ".result")
    try:
        if p.exists():
            with open(p, "r") as f:
                return f.read()
        else:
            with open(p, "w") as f:
                res = []
                for i in range(605):
                    r = fen_calc(str(i), costs, penalty)
                    log.debug(f"Fencalc {i} {res}")
                    if i == 0 or r != res[-1][1]:
                        res.append([(str(i) + "   ")[:4] + " : ", r])
                r = "\n".join([x[0] + x[1] for x in res])
                f.write(r)
                return r
    except:
        with open(p, "w") as f:
            f.write("an error has previously occured and this request is blocked")
            return "error"


@app.route('/fencalc/<inputstring>/<costs>/<penalty>')
@app.route('/fencalc/<inputstring>')
def fen_calc(inputstring: str, costs=None, penalty=None):  # move into fen sheet static method
    def cost(att: Tuple[int, ...], internal_costs: List[int], internal_penalty: List[int]) -> int:
        pen = 0
        for ip, p in enumerate(internal_penalty):
            pen += (max(sum([1 for a in att if a >= ip]), 1) - 1) * p
        return sum([internal_costs[a] for a in att]) + pen

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
        allconf = set([(a, b, c) for a in range(5) for b in range(a + 1) for c in range(b + 1)])
        correct = [[x[0] + 1, x[1] + 1, x[2] + 1] for x in allconf if cost(x, costs, penalty) <= xp]
        i = 0
        j = len(correct)
        maximal = correct[:]
        while i < j:
            for u in range(len(maximal[i])):
                upg = list(maximal[i])
                upg[u] = upg[u] + 1
                # upg = tuple(upg)
                if upg in correct:
                    del (maximal[i])
                    i -= 1
                    j -= 1
                    break
            i += 1
        return "\t".join(str(c) for c in maximal)
    else:
        return str(cost(tuple([x - 1 for x in xp]), costs, penalty))


@app.route('/modify_sheet/', methods=['GET', 'POST'])
@app.route('/modify_sheet/<t>', methods=['GET', 'POST'])
def modify_sheet(t=None):
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    if t is not None:
        if t == "FEN":
            u.sheet = FenCharacter()
        if t == "OWOD":
            u.sheet = VampireCharacter()
    if request.method == 'POST':
        log.info(f"incoming modify: {request.form}")
        u.update_sheet(request.form)
        ul.saveuserlist()

        return redirect('/charactersheet/')
    a = "NOPE"
    sheet = u.sheet.getdictrepr()
    if sheet["Type"] == "OWOD":
        a = render_template('vampsheet_editor.html', character=sheet, Clans=u.sheet.get_clans(),
                            Backgrounds=u.sheet.get_backgrounds())
    elif sheet["Type"] == "FEN":
        a = render_template('fensheet_editor.html', character=u.sheet)
    return a


@app.route('/delete_entry/<ident>', methods=['POST'])
def delete_entry(ident):
    if checktoken():
        checklogin()
        entry = {}
        cur = g.db.execute('SELECT author, title, text, id FROM entries WHERE id = ?', [ident])
        for row in cur.fetchall():  # SHOULD only run once
            entry = dict(author=row[0], title=row[1], text=row[2], id=row[3])
        if (not session.get('admin')) and (entry.get('author').upper() != session.get('user')):
            flash('This is not your Post!')
        else:
            if entry.get('author')[0].islower():
                g.db.execute('UPDATE entries SET author = ? WHERE id = ?',
                             [entry.get('author').upper(), entry.get('id')])
                flash('Entry: "' + entry.get('title') + '" has been restored.')

            else:
                g.db.execute('UPDATE entries SET author = ? WHERE id = ?',
                             [entry.get('author').lower(), entry.get('id')])
                flash('Entry: "' + entry.get('title') + '" has been deleted.')
            g.db.commit()
        return redirect(url_for('show_entries'))
    else:
        abort(404)


@app.route('/add', methods=['POST'])
def add_entry():
    checklogin()
    log.info(f"{session.get('user', '?')} adding {request.form}")
    if checktoken():
        g.db.execute('INSERT INTO entries (author, title, text, tags) VALUES (?, ?, ?, ?)',
                     [session.get('user'), request.form['title'], request.form['text'], request.form['tags']])
        g.db.commit()
        flash('New entry was successfully posted')

    return redirect(url_for('show_entries'))


@app.route('/buy_funds/', methods=['GET', 'POST'])
def add_funds():
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    error = None
    keyprovided = session.get('amount') is not None
    if not keyprovided:
        keyprovided = None
    if request.method == 'POST':
        if checktoken():
            try:
                amount = int(request.form['amount'])
                if amount > 0:
                    key = int(time.time())
                    key = generate_password_hash(str(key))
                    log.info(f"REQUEST BY {u.username} FOR {amount} CREDITS. KEY: {key}.")
                    session['key'] = key[-10:]
                    session['amount'] = amount
                    keyprovided = True
                else:
                    error = 'need positive amount'
            except Exception:
                try:
                    key = request.form['key'][-10:]
                    if key == session.pop('key'):
                        flash('Transfer of ' + str(session.get('amount')) + ' Credits was successfull!')
                        u.funds += int(session.pop('amount'))
                    else:
                        error = 'wrong key, transaction invalidated.'
                        session.pop('amount')
                        session.pop('key')
                except Exception:
                    error = 'invalid transaction'

    ul.saveuserlist()

    return render_template('funds.html', user=u, error=error, keyprovided=keyprovided)


@app.route('/register', methods=['GET', 'POST'])
def register():  # this is not clrs secure because it does not need to be
    error = None
    u = Userlist(None)
    if request.method == 'POST':
        username = request.form['username'].strip()
        if len(username) > 2:
            username = username.upper()
            if request.form['password'] == request.form['passwordcheck']:
                password = request.form['password']
                if len(password) > 0:
                    log.info(f"creating user {username}")
                    error = u.adduser(username, password)
                    if error is None:
                        flash('User successfully created.')
                        return redirect(url_for('start'))
                else:
                    error = 'Password has to be not empty!'
            else:
                error = 'Passwords do not match!'
        else:
            error = 'Username is too short!'
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
@app.route('/login/<path:r>', methods=['GET', 'POST'])
def login(r=None):
    error = None
    returnto = r
    if request.method == 'POST':
        ul = Userlist(preload=False, sheets=False)
        user = request.form['username']
        user = user.upper()
        if not ul.valid(user, request.form.get('password', None)):
            error = 'invalid username/password combination'
        else:
            session['logged_in'] = True
            session['print'] = gen_salt(32)
            session['user'] = user
            session['admin'] = (ul.loaduserbyname(session.get('user')).admin == "Administrator")
            flash('You were logged in')
            log.info(f"logged in as {user}")
            returnto = request.form.get('returnto', None)
            if returnto is None:
                return redirect(url_for('show_entries'))
            else:
                return redirect(returnto)
    log.debug(f"returnto during login: {returnto}")
    return render_template('login.html', returnto=returnto, error=error)


@app.route('/logout')
def logout():
    session.clear()
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/cards')
def cards():
    return render_template('cards.html')


@app.route('/nn')
def start():
    return render_template('show_entries.html',
                           entries=[
                               dict(author='the NOSFERATU NETWORK', title='WeLcOmE tO tHe NoSfErAtU nEtWoRk', text='')],
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=/">'])


@app.route('/user/<username>')
def show_user_profile(username):
    msgs = []
    if username == session.get('user'):  # get messages for this user if looking at own page
        cur = g.db.execute(
            'SELECT author,recipient,title,text,value,lock, id FROM messages '
            'WHERE ? IN (recipient, author) ' + ' ORDER BY id DESC',
            (session.get('user'),))
        for row in cur.fetchall():
            msg = dict(author=row[0], recipient=row[1], title=row[2], text=row[3], value=row[4],
                       lock=row[5], id=row[6])
            if msg['lock']:
                if msg['author'] == username:
                    msg['text'] = '[not yet paid for by ' + msg['recipient'] + ']<br><br>' + msg['text']
                    msg.pop('lock')
                else:
                    msg['text'] = '[locked until you pay]'
            msgs.append(msg)

    ul = Userlist(preload=True)
    if ul.contains(username):
        u = ul.getuserbyname(username)
    else:
        u = User(username, "")
    site = render_template('userinfo.html', user=u, msgs=msgs)
    return site


@app.route('/impressum/')
def impressum():
    return render_template('Impressum.html')


@app.route('/tickerdata/<referrer>')
def tickerdata(referrer):
    result = {"data": "- - - - -"}
    with open("NossiSite/locales/newsEN.json") as f:
        news = json.loads(f.read())
    if referrer == "show_entries.html":
        result["data"] = news["mainpage"]
    else:
        result["data"] = ""

    return json.dumps(result)


@app.route('/boardgame<int:size>_<seed>.json')
@app.route('/boardgame<int:size>_.json')
def boardgamemap(size, seed=""):
    if size > 100:
        size = 100
    rx = random.Random()
    if seed:
        rx.seed(str(size) + str(seed))

    def r(a=4):
        for i in range(a):
            yield rx.randint(1, 10)

    def e(inp, dif):
        for i in inp:
            yield 2 if i == 10 else (1 if i >= dif else 0)

    def fpik(inp, pref="FPIK"):
        vals = list(inp)
        vals = [(v if v != 2 else (2 if sum(vals) < 4 else 1)) for v in vals]
        for i in range(len(pref)):
            yield '"' + pref[i] + '": ' + str(vals[i])

    def cell():  # i, j):
        difficulty = 8
        '''6 + (
            (9 if i == j else
             8)
            if i in [0, size - 1] and j in [0, size - 1] else
            (7 if j in [0, size - 1] else
             (6 if j % 2 == 1 and (i in [0, size - 1] or j in [0, size - 1]) else
              (5 if 0 < i < size - 1 else 8))))'''

        for l in fpik(e(r(), difficulty)):
            yield l

    first = True

    def notfirst():
        nonlocal first
        if first:
            first = False
            return True
        else:
            return False

    def resetfirst():
        nonlocal first
        first = True

    def generate():
        yield "{\"board\": ["
        for x in range(size):
            yield ("," if not first else "") + "["
            resetfirst()
            for y in range(size):
                time.sleep(0.001)
                yield ("" if notfirst() else ",") + "{ \"x\":%d, \"y\":%d, " % (x, y) + ",".join(
                    cell(
                        # x, y
                    )
                ) + "}"
            yield "]"
        yield "]}"

    return Response(generate(), mimetype='text/json')


@app.route('/gameboard/<int:size>/')
@app.route('/gameboard/<int:size>/<seed>')
def gameboard(size, seed=""):
    if size > 20:
        size = 20
    return render_template("gameboard.html", size=size, seed=seed)


@app.route('/sendmsg/<username>', methods=['POST'])
def send_msg(username):
    def check0(a):
        return int(a) == 0

    error = None
    if checktoken():
        checklogin()
        g.db.execute('INSERT INTO messages (author,recipient,title,text,value,lock)'
                     ' VALUES (?, ?, ?, ?, ?, ?)',  # 6
                     [session.get('user'),  # 1 -author
                      username,  # 2 -recipient
                      request.form['title'],  # 3 title
                      request.form['text'],  # 4 text
                      request.form['price'],  # 5 value
                      not check0(request.form['price']),  # 6 lock
                      ])
        g.db.commit()
        flash('Message sent')
    return redirect(url_for('show_entries', error=error))


@app.route('/unlock/<ident>')
def unlock(ident):
    ul = Userlist()
    error = None
    u = None
    lock = 0
    author = ''
    value = 0
    if checktoken():
        u = ul.loaduserbyname(session.get('user'))
        cur = g.db.execute('SELECT author, value, lock FROM messages WHERE id = ?', [ident])
        for row in cur.fetchall():
            author = row[0]
            value = row[1]
            lock = row[2]
        n = ul.loaduserbyname(author)  # n because n = u seen from the other side of the table
        if lock == 1:
            if u.funds < value:
                error = "Not enough funds."
            else:
                u.funds -= value
                aftertax = int(value * 0.99)  # 1% Tax
                n.funds = int((n.funds + aftertax))
                g.db.execute('UPDATE messages SET lock = 0 WHERE id = ?',
                             [ident])
                flash("Transfer complete. Check the received message.")
                g.db.commit()
                ul.saveuserlist()
        else:
            flash('already unlocked!')

    return render_template('userinfo.html', user=u, error=error,
                           heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=' + url_for('show_user_profile',
                                                                                         username=u.username) + '">'])


@app.route('/resetpassword/', methods=['GET', 'POST'])
def resetpassword():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    if request.method == 'POST':
        if checktoken():
            try:
                username = request.form['username']
                password = request.form['password']
                newpassword = request.form['newpassword']
                if session.get('admin', False):
                    u = ul.loaduserbyname(username)
                if u.username == username:
                    if u.check_password(password) or session.get('admin', False):
                        u.set_password(newpassword)
                        flash('Password change successfull!')
                    else:
                        flash('Wrong password!')
                else:
                    flash('You are not ' + username)
            except:
                flash('You seem to not exist. Huh...')
                return render_template('resetpassword.html')
    ul.saveuserlist()

    return render_template('resetpassword.html')


@app.route('/payout/', methods=['GET', 'POST'])
def payout():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get('user'))
    error = None
    if request.method == 'POST':
        if checktoken():
            try:
                amount = int(request.form['amount'])

                u.funds += -amount
                log.info(f"DEDUCT BY {session.get('user')}: {amount}")
                if u.funds < 0:
                    flash("not enough funds")
                    raise Exception()
                flash('Deduct successfull')
                ul.saveuserlist()
            except:
                error = "Error deducting \"" + request.form.get('amount', 'nothing') + "\"."

    return render_template('payout.html', user=u, error=error)


@app.route('/lightswitch/')
def lightswitch():
    if session.get('light', False):
        session.pop('light')
    else:
        session["light"] = "ON"
    return redirect(request.referrer)


@app.route('/fenweapongraph')
def graphtest():
    import fengraph
    fengraph.supply_graphdata()
    return render_template("graphs.html")


@app.route('/chargen/<a>,<b>,<c>,<abia>,<abib>,<abic>,<shuffle>')
def chargen(a, b, c, abia, abib, abic, shuffle):
    try:
        return render_template("vampsheet.html",
                               character=VampireCharacter.makerandom(1, 5, int(a), int(b), int(c),
                                                                     int(abia), int(abib), int(abic), int(shuffle))
                               .getdictrepr())
    except:
        return redirect("/chargen/")


@app.route('/favicon.ico')
def favicon():
    return redirect("/static/favicon.ico")
