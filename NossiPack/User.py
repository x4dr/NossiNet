import pickle
import sqlite3
from typing import Union, List, Dict

from flask import flash
from werkzeug.security import generate_password_hash, check_password_hash

from NossiPack.Character import Character
from NossiPack.VampireCharacter import VampireCharacter

__author__ = "maric"

from NossiPack.krypta import connect_db as condb


def connect_db():
    return condb("User")


class User:
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
    ):
        self.username = username.strip().upper()
        if passwordhash is not None:
            self.pw_hash = passwordhash
        else:
            self.pw_hash = generate_password_hash(password)
        self.funds = funds
        from NossiSite import log

        try:
            self.sheet = VampireCharacter.deserialize(sheet)
        except:
            log.debug(f"could not load sheet {str(sheet[:100])}")
            self.sheet = VampireCharacter()
        self.oldsheets = self.deserialize_old_sheets(oldsheets)
        self.admin = admin

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

    def savetodb(self):
        db = connect_db()
        self.transition_oldsheets()
        if self.sheet.checksum() != 0:
            d = dict(
                username=self.username,
                pwhash=self.pw_hash,
                funds=self.funds,
                sheet=self.sheet.serialize(),
                oldsheets=self.serialize_old_sheets(),
                admin=self.admin,
            )
            db.execute(
                "INSERT OR REPLACE INTO users "
                "(username, passwordhash, funds, sheet, oldsheets, admin) "
                "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :admin)",
                d,
            )
        else:
            d = dict(
                username=self.username,
                pwhash=self.pw_hash,
                funds=self.funds,
                admin=self.admin,
                emptysheet=VampireCharacter().serialize(),
            )
            db.execute(
                "REPLACE INTO users (username, passwordhash, funds,  "
                "sheet, oldsheets, admin) "
                "VALUES (:username,:pwhash, :funds,"
                "COALESCE((SELECT sheet FROM users WHERE username = :username), "
                ":emptysheet),"
                "COALESCE((SELECT oldsheets FROM users WHERE username = "
                ":username), ''),"
                ":admin)",
                d,
            )
        db.commit()

    def configs(
        self,
    ) -> Dict[str, str]:  # central place to store default values for users
        res = {
            "discord": "not set",
            "fensheet_dots": "1",
            "fensheet_dot_max": "5",
            "character_sheet": "",
            # anything but a valid charactersheet defaults to vampire sheet
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

    def transition_oldsheets(self):
        db = connect_db()
        o: Union[VampireCharacter, Character]
        for o in self.oldsheets:
            if not isinstance(o, VampireCharacter):
                print("LEGACY CHARACTER!", o.getdictrepr())
                flash(f"LEGACY CHAR FROM {self.username}@{o.timestamp}")
                o = VampireCharacter.from_character(o)
                o.legacy_convert()
            db.execute(
                "INSERT INTO sheets (owner, sheetdata)"
                "VALUES (:username,:sheetdata);",
                {"username": self.username, "sheetdata": pickle.dumps(o)},
            )
        self.oldsheets = []

    @classmethod
    def load(cls, username):
        db = connect_db()
        cur = db.execute(
            "SELECT username, passwordhash, funds, "
            "sheet, oldsheets, admin FROM users WHERE username = (?)",
            [username],
        )
        row = cur.fetchone()
        if row is None:
            return None
        return User(
            username=row[0],
            passwordhash=row[1],
            funds=row[2],
            sheet=row[3],
            oldsheets=row[4],
            admin=row[5],
        )


class Config:
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
                "UPDATE configs SET value = :value "
                "WHERE user LIKE :user AND option LIKE :option;",
                dict(user=user, option=option, value=value),
            )
        else:
            db.execute(
                "INSERT INTO configs(user,option,value) "
                "VALUES (:user, :option, :value);",
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


class Userlist:
    userlist: List[User]

    def __init__(self):
        self.userlist = []

    def saveuserlist(self):
        for u in self.userlist:
            u.savetodb()

    @classmethod
    def adduser(cls, user, password):
        u = User(username=user, password=password)
        d = dict(
            username=u.username,
            pwhash=u.pw_hash,
            funds=u.funds,
            sheet=u.sheet.serialize(),
            oldsheets=u.serialize_old_sheets(),
            admin=u.admin,
        )
        try:
            with connect_db() as db:
                db.execute(
                    "INSERT INTO users (username, passwordhash, funds, "
                    "sheet, oldsheets, admin) "
                    "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :admin)",
                    d,
                )
                db.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: users.username" in e.args[0]:
                return f"Username {user} is taken!"

        return None

    def loaduserbyname(self, username) -> Union[User, None]:
        username = username.upper()
        t = [x for x in self.userlist if x.username.upper() == username]
        if t:
            return t[0]
        newuser = User.load(username)
        if newuser:
            self.userlist.append(newuser)
        return newuser

    def valid(self, user, password) -> bool:
        try:
            u = self.loaduserbyname(user)
            if u is None:
                return False
            return u.check_password(password)
        except Exception:
            from NossiSite import log

            log.exception("exception while checking user credentials for {user}")
            raise
