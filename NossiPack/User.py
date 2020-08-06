import pickle
import sqlite3
from typing import Union, List, Dict

from flask import flash
from werkzeug.security import generate_password_hash, check_password_hash

from NossiPack.VampireCharacter import VampireCharacter

__author__ = "maric"

from NossiPack.krypta import connect_db as condb
from NossiSite.base import log


class User:
    oldsheets: Dict[int, VampireCharacter]
    db = None

    def __init__(
        self, username, password="", passwordhash=None, funds=0, sheet=None, admin="",
    ):
        self.username = username.strip().upper()
        if passwordhash is not None:
            self.pw_hash = passwordhash
        else:
            self.pw_hash = generate_password_hash(password)
        self.funds = funds
        self.sheet = "unused"
        self.sheetid = sheet
        self._loadedsheet = None
        self.oldsheets = {}
        self.admin = admin

    @classmethod
    def connect_db(cls) -> sqlite3.Connection:
        cls.db = condb("User")
        return cls.db

    def set_password(self, newpassword):
        self.pw_hash = generate_password_hash(newpassword)
        return True

    def loadsheet(self, num=None):
        if self._loadedsheet and num is None:
            return self._loadedsheet
        db = self.connect_db()
        res = db.execute(
            "SELECT sheet_id, sheetdata FROM sheets WHERE owner LIKE :user "
            "AND sheet_id = :id;",
            dict(user=self.username, id=self.sheetid if num is None else num),
        ).fetchone()
        if not res:
            return None
        return VampireCharacter.deserialize(res[1])

    def getsheet(self, num=None) -> VampireCharacter:
        sheet = self.loadsheet(num) or VampireCharacter()
        if num is None:
            self._loadedsheet = sheet
        return sheet

    def serialize_old_sheets(self):
        self.transition_oldsheets()
        return "LEGACY"

    def loadoldsheets(self) -> Dict[int, VampireCharacter]:
        db = self.connect_db()
        res = db.execute(
            "SELECT sheet_id, sheetdata FROM sheets WHERE owner LIKE :user;",
            dict(user=self.username),
        ).fetchall()
        self.oldsheets = (
            {r[0]: VampireCharacter.deserialize(r[1]) for r in res} if res else {}
        )
        return (
            {int(r[0]): VampireCharacter.deserialize(r[1]) for r in res} if res else {}
        )

    def savetodb(self):
        db = self.connect_db()
        self.transition_oldsheets()
        if self._loadedsheet:
            self.sheetid = self.savesheet(self._loadedsheet, self.sheetid)
            self._loadedsheet = None  # clear to load from db next time
        d = dict(
            username=self.username,
            pwhash=self.pw_hash,
            funds=self.funds,
            sheet=self.sheetid or 0,
            admin=self.admin,
        )
        db.execute(
            "INSERT OR REPLACE INTO users "
            "(username, passwordhash, funds, sheet, admin) "
            "VALUES (:username,:pwhash, :funds, :sheet, :admin)",
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
            self.sheetid = self.savesheet(VampireCharacter().setfromform(form))
        else:
            self.savesheet(self.getsheet().setfromform(form), self.sheetid)

    def savesheet(self, sheet, num: int = None):
        if not isinstance(sheet, VampireCharacter):
            flash(f"UPDATING LEGACY CHAR FROM {self.username}@{sheet.timestamp}")
            sheet = VampireCharacter.from_character(sheet)
            sheet.legacy_convert()
        db = self.connect_db()
        if num:
            dbc = db.cursor()  # need cursor to get affected rowcount
            dbc.execute(
                "UPDATE sheets SET sheetdata=(:sheetdata) "
                "WHERE owner=(:username) AND sheet_id=(:id);",
                {
                    "username": self.username,
                    "sheetdata": pickle.dumps(sheet),
                    "id": num,
                },
            )
            if dbc.rowcount:
                db.commit()
                return num
            raise Exception("NO UPDATE HAPPENED!", self.username, num)
        db.execute(
            "INSERT INTO sheets (owner, sheetdata) VALUES (:username,:sheetdata);",
            {"username": self.username, "sheetdata": pickle.dumps(sheet)},
        )
        res = db.execute("SELECT last_insert_rowid();").fetchone()
        return res[0]

    @property
    def sheetpublic(self):
        return "public" in self.getsheet().meta["Notes"][:22]

    def transition_oldsheets(self):
        o: VampireCharacter
        for i, o in self.oldsheets.items():
            if i < 0:
                self.savesheet(o)
        self.oldsheets = {}
        if isinstance(self.sheetid, int):
            return  # reference instead

        if self.sheetid:
            sheet = self.getsheet()
            if not isinstance(sheet, VampireCharacter):
                print("LEGACY CHARACTER!", sheet.getdictrepr())
                flash(f"LEGACY CHAR FROM {self.username}@{sheet.timestamp}")
                sheet = VampireCharacter.from_character(sheet)
                sheet.legacy_convert()
            self.sheetid = self.savesheet(sheet)

    @classmethod
    def load(cls, username):
        db = cls.connect_db()
        cur = db.execute(
            "SELECT username, passwordhash, funds, "
            "sheet, admin FROM users WHERE username = (?)",
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
            admin=row[4],
        )

    def claimsheet(self, x):
        db = self.connect_db()
        c = db.cursor()
        res = c.execute(
            "UPDATE sheets SET owner = :user WHERE owner IS NULL AND sheet_id = :id;",
            dict(user=self.username, id=int(x)),
        )
        if res.rowcount:
            flash("success")
        else:
            flash("You cannot claim sheet " + str(x))
        db.commit()

    @classmethod
    def freesheet(cls, x):
        x = int(x)
        flash(
            "If you ever want to restore this sheet, write this number down:" + str(x)
        )
        db = cls.connect_db()
        db.execute("UPDATE sheets SET owner=NULL WHERE sheet_id=?", [x])
        db.commit()


class Config:
    @staticmethod
    def load(user, option, db=None):
        db = db or User.connect_db()
        res = db.execute(
            "SELECT value FROM configs WHERE user LIKE :user AND option LIKE :option;",
            dict(user=user, option=option),
        ).fetchone()
        return res[0] if res else None

    @staticmethod
    def loadall(user: str, db=None) -> Dict[str, str]:
        db = db or User.connect_db()
        res = db.execute(
            "SELECT option, value FROM configs WHERE user LIKE :user;", dict(user=user)
        ).fetchall()
        return {r[0]: r[1] for r in res} if res else {}

    @staticmethod
    def check(db):
        res = db.execute(
            "SELECT value FROM configs WHERE option LIKE 'character_sheet';"
        ).fetchall()
        res = [x[0] for x in res if x[0].strip()]
        if len(res) != len(set(res)):
            raise Exception("Violated Unique character sheet constraint!")

    @staticmethod
    def save(user, option, value, db=None):
        db = db or User.connect_db()
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
        Config.check(db)
        db.commit()

    @staticmethod
    def delete(user, option, db=None):
        db = db or User.connect_db()
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
    def adduser(cls, user, password) -> Union[str, None]:
        """
        Adds a User to the Database
        :param user: username
        :param password: password (cleartext, will be hashed)
        :return: None if success, str with errormessage on failure
        """
        if cls().loaduserbyname(user) is None:
            u = User(username=user, password=password)
            u.savetodb()
            return None
        return f"Username {user} is taken!"

    def loaduserbyname(self, username) -> Union[User, None]:
        username = username.upper()
        t = [x for x in self.userlist if x.username.upper() == username]
        if t:
            return t[0]
        newuser = User.load(username)
        if newuser:
            self.userlist.append(newuser)
        return newuser

    def valid(self, user: str, password: str) -> bool:
        """
        checks if credentials are valid
        :param user: username
        :param password: userpassword (cleartext)
        :return: True if user with these credentials exists, False otherwise
        """
        try:
            u = self.loaduserbyname(user)
            if u is None:  # technically vulnerable to timing attacks
                return False
            return u.check_password(password)
        except Exception:
            log.exception("exception while checking user credentials for {user}")
            raise
