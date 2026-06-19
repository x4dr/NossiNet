"""Blueprint for main site views including authentication, user profiles, theming, and blog-style entries."""

import json
import string
import subprocess
import time
from random import SystemRandom
from typing import TYPE_CHECKING, Any

import bleach
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from gamepack.Dice import DescriptiveError
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from werkzeug.security import gen_salt

from Data import connect_db
from NossiPack.User import Config, User, Userlist
from NossiPack.VampireCharacter import VampireCharacter
from NossiSite import ALLOWED_TAGS
from NossiSite.base import app, log
from NossiSite.helpers import checklogin

if TYPE_CHECKING:
    from werkzeug.wrappers.response import Response as WerkzeugResponse

views = Blueprint("views", __name__)


@views.route("/version")
def getversion() -> tuple[str, int, dict[str, str]]:
    """Return the latest git commit log entry as plain text."""
    # skipcq: BAN-B607, BAN-B603
    res = subprocess.run(
        ["git", "log", "-n 1"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    result = res.stdout
    return result, 200, {"Content-Type": "text/plain; charset=utf-8"}


@views.route("/entries/")
@views.route("/entries/<x>")
def get_entry(x: str | None = None) -> dict[str, Any]:
    """Retrieve a blog entry by ID with sanitised HTML."""
    if not x:
        return {}
    db = connect_db("entrybyid")
    e = next(
        dict(author=row[0], title=row[1], text=row[2], tags=row[3])
        for row in [
            db.execute(
                "SELECT author, title, text, tags FROM entries WHERE id = ?",
                [x],
            ).fetchone(),
        ]
    )
    e["text"] = bleach.clean(e["text"], tags=ALLOWED_TAGS)
    return e


@views.route("/entry_text/<x>")
def entry_text(x: str) -> str | dict[str, Any]:
    """Retrieve the sanitised text body of a blog entry by ID."""
    if not x:
        return {}
    db = connect_db("entrybyid")
    e = db.execute("SELECT text FROM entries WHERE id = ?", [x]).fetchone()
    if e is None:
        return ""
    return bleach.clean(e[0], tags=ALLOWED_TAGS)


@views.route("/")
def show_entries() -> str:
    """Render the main index page listing all blog entries the user has access to."""
    db = connect_db("main")
    cur = db.execute("SELECT author, title, id, tags FROM entries ORDER BY id DESC")
    entries = [dict(author=row[0], title=row[1], id=row[2], tags=row[3]) for row in cur.fetchall()]
    entries = [
        e
        for e in entries
        if any(t in (e.get("tags", "") or "default").split(" ") for t in session.get("tags", "default").split(" "))
    ]
    for e in entries:
        e["own"] = (session.get("logged_in")) and (session.get("user") == e["author"])
    entries = [
        e for e in entries if e.get("author", "none")[0].isupper()
    ]  # don't send out lowercase authors ("deleted")
    return render_template("base/show_entries.html", entries=entries)


@views.route("/themeeditor")
def theme_editor() -> str:
    """Render the theme editor page."""
    return render_template("base/themeeditor.html")


@views.route("/savetheme", methods=["POST"])
def save_theme() -> tuple[WerkzeugResponse, int]:
    """Save the user's custom theme CSS variables."""
    username = session.get("user", "")
    app.jinja_env.globals["restart_id"] = "".join(SystemRandom().choice(string.hexdigits) for _ in range(4))
    if not username:
        flash("not logged in", "error")
        return (
            jsonify({"success": False, "redirect_url": url_for("views.show_entries")}),
            200,
        )
    usertheme = ""
    for k in request.form:
        v = request.form.get(k)
        if not v or not v.strip():
            continue
        usertheme += f"{k}:{v};"
    Config.save(username, "theme", usertheme)
    flash("theme updated succesfully")
    return (
        jsonify({"success": True, "redirect_url": url_for("views.show_entries")}),
        200,
    )


@views.route("/theme.css")
def theme() -> WerkzeugResponse:
    """Generate the user's custom theme CSS file, falling back to light theme."""
    username = session.get("user", "")
    usertheme = User(username).configs().get("theme", "")
    if not usertheme and session.get("light"):
        with open((current_app.static_folder or "") + "/light-theme.conf") as f:
            usertheme = f.read()
    t = {}
    if username:
        for entry in usertheme.split(";"):
            if not entry.strip():
                continue
            k, v = entry.split(":")
            t[k.strip()] = v.strip()
    with open((current_app.static_folder or "") + "/base-theme.css") as f:
        basetheme = f.read()
    output = ""
    for line in basetheme.splitlines(keepends=True):
        if "-" not in line:
            output += line
            continue
        colorname = line.lstrip(" -")
        splitpos = colorname.find("-color:")
        colorname = colorname[:splitpos]
        if colorname in t:
            output += f"    --{colorname}-color: {t[colorname]};\n"
        else:
            output += line
    response = make_response(output)
    response.headers["Content-Type"] = "text/css"
    return response


@views.route("/edit/post/<x>", methods=["GET", "POST"])
@views.route("/edit/all", methods=["GET", "POST"])
def editentries(x: str | None = None) -> str | WerkzeugResponse:
    """Edit a blog entry by ID or list all entries by the current user."""
    checklogin()
    db = connect_db("editentries")
    if request.method == "GET":
        if x is None:
            cur = db.execute(
                "SELECT author, title, text, id, tags " "FROM entries WHERE UPPER(author) LIKE UPPER(?)",
                [session.get("user")],
            )
            entries = [dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in cur.fetchall()]
            return render_template("base/show_entries.html", entries=entries, edit=True)
        try:
            x_int = int(x)
            cur = db.execute(
                "SELECT author, title, text, id, tags FROM entries WHERE id == ?",
                [x_int],
            )
            entry = next(
                dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in cur.fetchall()
            )
            if ((session.get("user") or "").upper() == entry["author"].upper()) or session.get(
                "admin",
            ):
                return render_template("base/edit_entry.html", mode="blog", entry=entry)
            raise ValueError
        except (ValueError, IndexError):
            flash("not authorized to edit post " + str(x))
            return redirect(url_for("views.editentries"))
    if request.method == "POST":
        if request.form["id"] == "new":
            return add_entry()
        cur = db.execute(
            "SELECT author, title, text, id, tags FROM entries WHERE id == ?",
            [int(request.form["id"])],
        )
        entry = next(dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4]) for row in cur.fetchall())
        if ((session.get("user") or "").upper() == entry["author"].upper()) or session.get(
            "admin",
        ):
            db.execute(
                "UPDATE entries SET title=?, text=?, tags=? WHERE id == ?",
                [
                    request.form["title"],
                    request.form["text"],
                    request.form["tags"],
                    request.form["id"],
                ],
            )
            session["retrieve"] = None
            db.commit()
            flash("entry was successfully edited")
        else:
            flash(
                "not authorized: " + (session.get("user") or "").upper() + "!=" + entry["author"].upper(),
            )

        return redirect(url_for("views.show_entries"))
    return abort(405)


@views.route("/update_filter/", methods=["POST"])
def update_filter() -> WerkzeugResponse:
    """Update the tag filter for the current session and redirect to the index."""
    if session.get("logged_in"):
        session["tags"] = request.form["tags"]
    return redirect(url_for("views.show_entries"))


@views.route("/config/", methods=["POST"])
@views.route("/config/<path:x>", methods=["GET", "POST"])
def config(x: str | None = None) -> str | WerkzeugResponse:
    """View or update a user configuration option."""
    checklogin()
    if request.method == "GET":
        c = Config.load(session["user"], x or "") or ""
        heading = x
        return render_template("base/config.html", heading=heading, config=x, curval=c)
    if request.method == "POST":
        if not x:
            return redirect(url_for("views.config", x=request.form["configuration"]))
        if request.form.get("delete", None):
            log.info(f"Deleting {x} of user {session['user']}.")
            Config.delete(session["user"], x.lower())
            flash(f"Deleted {x}!")
        elif s := request.form.get("confirm", None):
            if x != "unconfirmed_discord_link":
                abort(400)
            log.info(f"confirming discord account {s} for user {session['user']}.")
            Config.save(session["user"], "discord", s)
            Config.delete(session["user"], x.lower())
            flash(f"Confirmed {s} as your discord account!")
        else:
            try:
                Config.save(session["user"], x.lower(), request.form["configuration"])
                flash(f"Saved {x}!")
            except DescriptiveError as e:
                flash(f"Error: {e}", category="error")
        return redirect(url_for("views.show_user_profile", username=session["user"]))
    return abort(405)


@views.route("/charactersheet/")
def charsheet() -> str | WerkzeugResponse:
    """Redirect the logged-in user to their configured character sheet."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    configchar = u.config("character_sheet", None)
    if configchar:
        char: WikiCharacterSheet[Any] | None = WikiCharacterSheet.load_locate(configchar)
        if char and hasattr(char, "render"):
            res = char.render()
            if res:
                return res  # type: ignore[no-any-return]
        return redirect(url_for("sheets.sheet", c=configchar))
    return redirect(url_for("sheets.chargen"))


@views.route("/showsheet/<name>")
def showsheet(name: str = "None") -> str | WerkzeugResponse:
    """Display another user's vampire character sheet if permitted."""
    checklogin()
    if name == "None":
        return "error"
    name = name.upper()
    ul = Userlist()
    u = ul.loaduserbyname(name)
    if u is None:
        abort(404)
    if (u and u.sheetpublic) or session.get("admin", False):
        return render_template(
            "sheets/vampsheet.html",
            character=u.getsheet().getdictrepr(),
            own=False,
        )
    flash("you do not have permission to see this")
    return render_template(
        "sheets/vampsheet.html",
        character=VampireCharacter().getdictrepr(),
        own=False,
    )


@views.route("/deletesheet/", methods=["POST"])
def del_sheet() -> WerkzeugResponse:
    """Delete (free) a character sheet by its number."""
    checklogin()
    x = int(request.form["sheetnum"])
    User.freesheet(str(x))
    return redirect(url_for("views.menu_oldsheets"))


@views.route("/claimsheet/", methods=["POST"])
def claim_sheet() -> WerkzeugResponse:
    """Assign unassigned/'deleted' charactersheet to user."""
    checklogin()
    x = int(request.form["sheetnum"])
    u = Userlist().loaduserbyname(str(session["user"] or ""))
    assert u is not None
    u.claimsheet(str(x))
    return redirect(url_for("views.menu_oldsheets"))


@views.route("/restoresheet/", methods=["POST"])
def res_sheet() -> WerkzeugResponse:
    """Restore an old character sheet from the user's history."""
    checklogin()
    x = int(request.form["sheetnum"])
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    if u.loadoldsheets().get(x, None):
        u.sheetid = x
        ul.saveuserlist()
        flash("Sheet selected from history!")
    return redirect(url_for("views.menu_oldsheets"))


@views.route("/berlinmap")
def berlinmap() -> str:
    """Render the Berlin interactive map page."""
    return render_template("misc/map.html")


@views.route("/berlinmap/data.dat")
def mapdata() -> str:
    """Generate JSON data for Berlin map property and actor overlays."""
    db = connect_db("mapdata")
    log.debug("generating mapdata")
    time0 = time.time()
    cur = db.execute("SELECT name, owner,tags,data FROM property")
    plzs = {}
    for row in cur.fetchall():
        plzs[row[0]] = {
            "owner": row[1] or "",
            "tags": row[2] or "",
            "data": row[3] or "",
        }
    cur = db.execute("SELECT name, faction, allegiance, clan, tags FROM actors")
    for row in cur.fetchall():
        for plzdat in plzs.values():
            if plzdat["owner"].upper() == row[0]:
                plzdat["tags"] += " ".join(x for x in row[1:] if x)
                if row[1]:
                    plzdat["faction"] = row[1]
    log.debug(f"took: {time.time() - time0} seconds.")
    return json.dumps(plzs)


@views.route("/oldsheets/")
def menu_oldsheets() -> str:
    """Show the user's old character sheets with XP diffs."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    oldsheets = []
    xpdiffs = []
    for i, sheet in u.loadoldsheets().items():
        oldsheets.append([i, sheet.timestamp, sheet.meta])
        if len(oldsheets) > 1:
            xpdiffs.append(sheet.get_diff(u.getsheet(int(str(oldsheets[-2][0])))))
        else:
            xpdiffs.append(sheet.get_diff(None))
    return render_template(
        "sheets/oldsheets.html",
        oldsheets=oldsheets,
        xpdiffs=xpdiffs,
    )


@views.route("/showoldsheets/<x>")
def showoldsheets(x: str) -> str | WerkzeugResponse:
    """View a specific old character sheet by its number."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    try:
        sheetnum = int(x)
    except Exception:
        flash(f"LOL NOPE {x} is not a sheet number")
        return redirect(url_for("views.menu_oldsheets"))
    sheet = u.loadsheet(sheetnum)
    if sheet:
        return render_template(
            "sheets/vampsheet.html",
            character=u.getsheet(sheetnum).getdictrepr(),
            oldsheet=x,
        )
    flash(
        "I am not allowed to tell you if that character even exists. " "Maybe you can summon them?",
    )
    return render_template("sheets/oldsheets.html", summon=x)


@views.route("/new_vamp_sheet/", methods=["GET"])
def new_vamp_sheet() -> str:
    """Render the vampire character sheet editor for a blank sheet."""
    checklogin()
    return render_template("sheets/vampsheet_editor.html", character=VampireCharacter())


@views.route("/modify_sheet/", methods=["GET", "POST"])
def modify_sheet() -> str | WerkzeugResponse:
    """View or process modifications to the user's vampire character sheet."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    if request.method == "POST":
        log.info(f"incoming modify: {request.form}")
        u.update_sheet(request.form)
        ul.saveuserlist()
        return redirect("/charactersheet/")

    sheet = u.getsheet().getdictrepr()
    print("sheet", sheet)
    if sheet["Type"] == "OWOD":
        return render_template(
            "sheets/vampsheet_editor.html",
            character=sheet,
            Clans=u.getsheet().get_clans(),
            Backgrounds=u.getsheet().get_backgrounds(),
        )
    msg = f"unsupported sheettpe:{sheet['Type']}"
    raise DescriptiveError(msg)


@views.route("/delete_entry/<ident>", methods=["POST"])
def delete_entry(ident: str) -> WerkzeugResponse:
    """Toggle a blog entry's deleted state by lowercasing/uppercasing its author."""
    checklogin()
    db = connect_db("deleteentry")
    entry = {}
    cur = db.execute(
        "SELECT author, title, text, id FROM entries WHERE id = ?",
        [ident],
    )
    for row in cur.fetchall():  # SHOULD only run once
        entry = dict(author=row[0], title=row[1], text=row[2], id=row[3])
    if (not session.get("admin")) and (entry.get("author", "").upper() != session.get("user")):
        flash("This is not your Post!")
    else:
        if entry.get("author", "A")[0].islower():
            db.execute(
                "UPDATE entries SET author = ? WHERE id = ?",
                [entry.get("author", "").upper(), entry.get("id")],
            )
            flash('Entry: "' + (entry.get("title") or "") + '" has been restored.')

        else:
            db.execute(
                "UPDATE entries SET author = ? WHERE id = ?",
                [entry.get("author", "").upper(), entry.get("id")],
            )
            flash('Entry: "' + (entry.get("title") or "") + '" has been deleted.')
        db.commit()
    return redirect(url_for("views.show_entries"))


@views.route("/add", methods=["POST"])
def add_entry() -> WerkzeugResponse:
    """Insert a new blog entry into the database."""
    checklogin()
    log.info(f"{session.get('user', '?')} adding {request.form}")

    db = connect_db("addentry")
    db.execute(
        "INSERT INTO entries (author, title, text, tags) VALUES (?, ?, ?, ?)",
        [
            session.get("user"),
            request.form["title"],
            request.form["text"],
            request.form["tags"],
        ],
    )
    db.commit()
    flash("New entry was successfully posted")
    return redirect(url_for("views.show_entries"))


@views.route("/buy_funds/", methods=["GET", "POST"])
def add_funds() -> str:
    """Render the funds purchase page and process credit transfers."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    error = None
    keyprovided: bool | None = session.get("amount") is not None
    if not keyprovided:
        keyprovided = None
    if request.method == "POST":
        try:
            amount = int(request.form["amount"])
            if amount > 0:
                key = int(time.time())
                key_str = str(hash(str(key)))
                log.info(f"REQUEST BY {u.username} FOR {amount} CREDITS. KEY: {key_str}.")
                session["key"] = key_str[-10:]
                session["amount"] = amount
                keyprovided = True
            else:
                error = "need positive amount"
        except Exception:
            try:
                key_input = request.form["key"][-10:]
                if key_input == session.pop("key"):
                    flash(
                        "Transfer of " + str(session.get("amount")) + " Credits was successfull!",
                    )
                    u.funds += int(session.pop("amount"))
                else:
                    error = "wrong key, transaction invalidated."
                    session.pop("amount")
                    session.pop("key")
            except Exception:
                error = "invalid transaction"

    ul.saveuserlist()

    return render_template(
        "base/funds.html",
        user=u,
        error=error,
        keyprovided=keyprovided,
    )


@views.route("/register", methods=["GET", "POST"])
def register_user() -> str | WerkzeugResponse:  # this is not clrs secure because it does not need to be
    """Render the registration form and process new user sign-ups."""
    error = None
    if request.method == "POST":
        username = request.form["username"].strip().upper()
        if len(username) > 2:
            if request.form["password"] == request.form["passwordcheck"]:
                password = request.form["password"]
                if len(password) > 0:
                    log.info(f"creating user {username}")
                    error = Userlist.adduser(username, password)
                    if error is None:
                        flash("User successfully created.")
                        return redirect(url_for("views.start"))
                else:
                    error = "Password has to be not empty!"
            else:
                error = "Passwords do not match!"
        else:
            error = "Username is too short!"
    if error:
        flash(error, category="error")
    return render_template("base/register.html")


@views.route("/login", methods=["GET", "POST"])
def login() -> str | WerkzeugResponse:
    """Render the login form and authenticate users."""
    error = None
    if request.method == "POST":
        ul = Userlist()
        user = request.form["username"]
        user = user.upper()
        if not ul.valid(user, request.form.get("password", "")):
            error = "invalid username/password combination"
        else:
            session["logged_in"] = True
            session["print"] = gen_salt(32)
            session["user"] = user
            u_adm = ul.loaduserbyname(str(session.get("user") or ""))
            assert u_adm is not None
            session["admin"] = u_adm.admin == "Administrator"
            flash("You were logged in")
            log.info(f"logged in as {user}")

            returnto = session.pop("returnto", None) or url_for("views.show_entries")
            return redirect(returnto)
    return render_template("base/login.html", error=error)


@views.route("/logout")
def logout() -> WerkzeugResponse:
    """Clear the session and log the user out."""
    session.clear()
    flash("You were logged out")
    return redirect(url_for("views.show_entries"))


@views.route("/nn")
def start() -> str:
    """Render the Nosferatu Network welcome splash page."""
    return render_template(
        "base/show_entries.html",
        entries=[
            dict(
                author="the NOSFERATU NETWORK",
                title="WeLcOmE tO tHe NoSfErAtU nEtWoRk",
                text="",
            ),
        ],
        heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=/">'],
    )


@views.route("/user/<username>")
def show_user_profile(username: str) -> str:
    """Display a user's profile page with messages and configuration."""
    msgs = []

    if username == session.get("user"):
        db = connect_db("mapdata")
        # get messages for this user if looking at own page
        cur = db.execute(
            "SELECT author, recipient, title, text, value, lock, id FROM messages "
            "WHERE ? IN (recipient, author) ORDER BY id DESC",
            (session.get("user"),),
        )
        for row in cur.fetchall():
            msg = dict(
                author=row[0],
                recipient=row[1],
                title=row[2],
                text=row[3],
                value=row[4],
                lock=row[5],
                id=row[6],
            )
            if msg["lock"]:
                if msg["author"] == username:
                    msg["text"] = "[not yet paid for by " + msg["recipient"] + "]<br><br>" + msg["text"]
                    msg.pop("lock")
                else:
                    msg["text"] = "[locked until you pay]"
            msgs.append(msg)

    ul = Userlist()
    u = ul.loaduserbyname(username)
    if u is None:
        u = User(username, "")
    return render_template("base/userinfo.html", user=u, msgs=msgs, configs=u.configs())


@views.route("/impressum/")
def impressum() -> str:
    """Render the legal impressum / imprint page."""
    return render_template("base/Impressum.html")


@views.route("/sendmsg/<username>", methods=["POST"])
def send_msg(username: str) -> WerkzeugResponse:
    """Send a message to a user."""

    def check0(a: str) -> bool:
        return int(a) == 0

    error = None

    checklogin()
    db = connect_db("mapdata")
    db.execute(
        "INSERT INTO messages (author, recipient, title, text, value, lock)" " VALUES (?, ?, ?, ?, ?, ?)",  # 6
        [
            session.get("user"),  # 1 -author
            username,  # 2 -recipient
            request.form["title"],  # 3 title
            request.form["text"],  # 4 text
            request.form["price"],  # 5 value
            not check0(request.form["price"]),  # 6 lock
        ],
    )
    db.commit()
    flash("Message sent")
    return redirect(url_for("views.show_entries", error=error))


@views.route("/unlock/<ident>")
def unlock(ident: str) -> str:
    """Pay to unlock a locked message and transfer funds to the author."""
    checklogin()
    ul = Userlist()
    error = None
    lock = 0
    author = ""
    value = 0

    db = connect_db("mapdata")
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    cur = db.execute("SELECT author, value, lock FROM messages WHERE id = ?", [ident])
    for row in cur.fetchall():
        author = row[0]
        value = row[1]
        lock = row[2]
    n = ul.loaduserbyname(
        author,
    )  # n because n = u seen from the other side of the table
    if lock == 1:
        if n is None:
            error = "Recipient no longer exists."
        elif u.funds < value:
            error = "Not enough funds."
        else:
            u.funds -= value
            aftertax = int(value * 0.99)  # 1% Tax
            n.funds = int(n.funds + aftertax)
            db.execute("UPDATE messages SET lock = 0 WHERE id = ?", [ident])
            flash("Transfer complete. Check the received message.")
            db.commit()
            ul.saveuserlist()
    return render_template(
        "base/userinfo.html",
        user=u,
        error=error,
        heads=[
            '<META HTTP-EQUIV="refresh" CONTENT="5;url='
            + url_for("views.show_user_profile", username=u.username)
            + '">',
        ],
    )


@views.route("/resetpassword/", methods=["GET", "POST"])
def resetpassword() -> str:
    """Render the password reset form and process password changes."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    if request.method == "POST":
        try:
            username = request.form["username"].strip().upper()
            password = request.form["password"]
            newpassword = request.form["newpassword"]
            if session.get("admin", False):
                u = ul.loaduserbyname(username)
                assert u is not None
            if u.username == username:
                if u.check_password(password) or session.get("admin", False):
                    u.set_password(newpassword)
                    flash("Password change successfull!")
                else:
                    flash("Wrong password!")
            else:
                flash("You are not " + username)
        except Exception:
            flash("You seem to not exist. Huh...")
            return render_template("base/resetpassword.html")
    ul.saveuserlist()

    return render_template("base/resetpassword.html")


@views.route("/payout/", methods=["GET", "POST"])
def payout() -> str:
    """Render the payout page and process fund deductions."""
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(str(session.get("user") or ""))
    assert u is not None
    error = None
    if request.method == "POST":
        try:
            amount = int(request.form["amount"])

            u.funds += -amount
            log.info(f"DEDUCT BY {session.get('user')}: {amount}")
            if u.funds < 0:
                flash("not enough funds")
                raise Exception
            flash("Deduct successfull")
            ul.saveuserlist()
        except Exception:
            error = 'Error deducting "' + request.form.get("amount", "nothing") + '".'

    return render_template("base/payout.html", user=u, error=error)


@views.route("/lightswitch/")
def lightswitch() -> WerkzeugResponse:
    """Toggle the light/dark theme preference in the session."""
    if session.get("light", False):
        session.pop("light")
    else:
        session["light"] = "ON"
    return redirect("/")


@views.route("/sse_test_ui")
def sse_test_ui() -> str:
    """Render the SSE test UI page."""
    return render_template("sse_test.html")
