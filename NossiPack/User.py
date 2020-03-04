import os
import pickle
import sqlite3
import sys
from typing import Union, List, Dict

from werkzeug.security import generate_password_hash, check_password_hash

from NossiPack.VampireCharacter import VampireCharacter

__author__ = "maric"

DATABASE = "./NN.db"


def connect_db():
    return sqlite3.connect(DATABASE)


class User(object):
    sheet: VampireCharacter

    def __init__(
        self,
        username,
        password="",
        passwordhash=None,
        funds=0,
        sheet=VampireCharacter().serialize(),
        oldsheets=b"",
        admin="",
        defines="",
    ):
        self.username = username.strip()
        if passwordhash is not None:
            self.pw_hash = passwordhash
        else:
            self.pw_hash = generate_password_hash(password)
        self.funds = funds
        from NossiSite import log

        try:
            self.sheet = VampireCharacter.deserialize(sheet)
        except:
            log.debug("could not load sheet " + str(sheet[:100]))
            self.sheet = VampireCharacter()
        self.oldsheets = self.deserialize_old_sheets(oldsheets)
        self.admin = admin
        self.defines = {}
        if defines:
            self.defines = pickle.loads(defines)
        self.defines = {**self.defines, **self.sheet.unify()}

    def set_password(self, newpassword):
        self.pw_hash = generate_password_hash(newpassword)
        return True

    def serialize_old_sheets(self):
        oldsheetserialized = []
        for s in self.oldsheets:
            if s is None:
                continue
            oldsheetserialized.append(s)
        return pickle.dumps(oldsheetserialized)

    def configs(
        self,
    ) -> Dict[str, str]:  # central place to store default values for users
        res = {
            "discord": "not set",
            "fensheet_dots": "1",
            "fensheet_dot_max": "5",
            "character_sheet": "",  # anything but a valid charactersheet defaults to vampire sheet
        }

        res.update(Config.loadall(self.username))
        return res

    def config(self, option, default=None):
        val = Config.load(self.username, option)
        return val if val is not None else default

    @staticmethod
    def deserialize_old_sheets(inp):
        if inp == b"":
            return []
        oldsheets = pickle.loads(inp)
        for o in oldsheets:
            o.legacy_convert()
        oldsheets.sort(key=lambda x: x.timestamp)
        return oldsheets

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def update_sheet(self, form):
        if "newsheet" in form.keys():
            self.oldsheets.append(VampireCharacter())
            self.oldsheets[-1].setfromform(form)
        self.sheet.setfromform(form)

    @property
    def sheetpublic(self):
        return "public" in self.sheet.meta["Notes"][:22]


class Config(object):
    @staticmethod
    def load(user, option, db=None):
        db = db or connect_db()
        res = db.execute(
            "SELECT value FROM configs WHERE user LIKE :user AND option LIKE :option;",
            dict(user=user, option=option),
        ).fetchone()
        return res[0] if res else None

    @staticmethod
    def loadall(user: str, db=None) -> Dict[str, str]:
        db = db or connect_db()
        res = db.execute(
            "SELECT option, value FROM configs WHERE user LIKE :user;", dict(user=user)
        ).fetchall()
        return {r[0]: r[1] for r in res} if res else {}

    @staticmethod
    def save(user, option, value, db=None):
        db = db or connect_db()
        if Config.load(user, option, db) is not None:
            db.execute(
                "UPDATE configs SET value = :value WHERE user LIKE :user AND option LIKE :option;",
                dict(user=user, option=option, value=value),
            )
        else:
            db.execute(
                "INSERT INTO configs(user,option,value) VALUES (:user, :option, :value);",
                dict(user=user, option=option, value=value),
            )
        db.commit()

    @staticmethod
    def delete(user, option, db=None):
        db = db or connect_db()
        if Config.load(user, option, db) is not None:
            db.execute(
                "DELETE FROM configs WHERE user LIKE :user AND option LIKE :option;",
                dict(user=user, option=option),
            )
        db.commit()
        # else it does not exist


class Userlist(object):
    userlist: List[User]

    def __init__(self, key="", preload=False, sheets=True):
        self.key = key
        self.userlist = []
        self.file = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        if preload:
            self.loaduserlist(sheets)

    def loaduserlist(
        self, sheets=True
    ):  # converts the SQL table into a list for easier access
        db = connect_db()
        if sheets:
            cur = db.execute(
                "SELECT username, passwordhash, funds, "
                "sheet, oldsheets, defines, admin FROM users"
            )
            f_all = cur.fetchall()
            for row in f_all:
                try:
                    self.userlist.append(
                        User(
                            username=row[0],
                            passwordhash=row[1],
                            funds=row[2],
                            sheet=row[3],
                            oldsheets=row[4],
                            defines=row[5],
                            admin=row[6],
                        )
                    )
                except Exception as e:
                    print(
                        f"unknown db exception of type {type(e)}: {e} start of row: {str(row[:100])}\n___\n{e.args}"
                    )
        else:
            cur = db.execute(
                "SELECT username, passwordhash, funds," "defines, admin FROM users"
            )
            self.userlist = [
                User(
                    username=row[0],
                    passwordhash=row[1],
                    funds=row[2],
                    defines=row[3],
                    admin=row[4],
                )
                for row in cur.fetchall()
            ]
        db.close()

    def saveuserlist(self):
        # writes/overwrites the SQL table with the maybe changed list. this is not performant at all
        db = connect_db()
        for u in self.userlist:
            if u.sheet.checksum() != 0:
                d = dict(
                    username=u.username,
                    pwhash=u.pw_hash,
                    funds=u.funds,
                    sheet=u.sheet.serialize(),
                    oldsheets=u.serialize_old_sheets(),
                    defines=pickle.dumps(u.defines),
                    admin=u.admin,
                )
                db.execute(
                    "INSERT OR REPLACE INTO users (username, passwordhash, funds, "
                    "sheet, oldsheets, defines, admin) "
                    "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :defines, :admin)",
                    d,
                )
            else:
                d = dict(
                    username=u.username,
                    pwhash=u.pw_hash,
                    funds=u.funds,
                    defines=pickle.dumps(u.defines),
                    admin=u.admin,
                    emptysheet=VampireCharacter().serialize(),
                )
                db.execute(
                    "INSERT OR REPLACE INTO users (username, passwordhash, funds,  "
                    "sheet, oldsheets, defines, admin) "
                    "VALUES (:username,:pwhash, :funds,"
                    "COALESCE((SELECT sheet FROM users WHERE username = :username), :emptysheet),"
                    "COALESCE((SELECT oldsheets FROM users WHERE username = :username), ''),"
                    " :defines, :admin)",
                    d,
                )

        db.commit()
        db.close()

    def adduser(self, user, password):
        if self.contains(user):
            return "Name is taken!"
        u = User(username=user, password=password)
        d = dict(
            username=u.username,
            pwhash=u.pw_hash,
            funds=u.funds,
            sheet=u.sheet.serialize(),
            oldsheets=u.serialize_old_sheets(),
            defines=pickle.dumps(u.defines),
            admin=u.admin,
        )
        db = connect_db()
        db.execute(
            "INSERT OR REPLACE INTO users (username, passwordhash, funds, "
            "sheet, oldsheets, defines, admin) "
            "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :defines, :admin)",
            d,
        )
        db.commit()
        db.close()
        return None

    def contains(self, user: str):
        for u in self.userlist:
            if u.username.upper() == user.upper():
                return True
        return False

    def getuserbyname(self, username) -> Union[User, None]:
        for u in self.userlist:
            if u.username == username:
                return u
        return None

    def loaduserbyname(self, username) -> Union[User, None]:
        db = connect_db()
        cur = db.execute(
            "SELECT username, passwordhash, funds, "
            "sheet, oldsheets, defines, admin FROM users WHERE username = (?)",
            (username,),
        )
        try:
            row = cur.fetchone()
            if row is None:
                return None
            newuser = User(
                username=row[0],
                passwordhash=row[1],
                funds=row[2],
                sheet=row[3],
                oldsheets=row[4],
                defines=row[5],
                admin=row[6],
            )

            if newuser.username not in self.userlist:
                self.userlist.append(newuser)
        except Exception as e:
            from NossiSite import log

            log.exception("loading user by name, error :", e, e.args)
            raise
        return newuser

    def getfunds(self, user=None, username=None):
        if user is None:
            if username is not None:
                user = self.getuserbyname(username)
        if user is not None:
            return user.funds
        return None

    def valid(self, user, password) -> bool:
        try:
            return self.loaduserbyname(user).check_password(password)
        except Exception:
            from NossiSite import log

            log.exception("exception while checking user credentials for ", user)
            raise
