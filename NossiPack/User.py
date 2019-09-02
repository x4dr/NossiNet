import os
import sys
import pickle
from typing import Union

from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

from NossiPack.FenCharacter import FenCharacter
from NossiPack.VampireCharacter import VampireCharacter

__author__ = 'maric'

DATABASE = './NN.db'


def connect_db():
    return sqlite3.connect(DATABASE)


class User(object):
    def __init__(self, username, password="", passwordhash=None, funds=0,
                 sheet=VampireCharacter().serialize(), oldsheets=b'', admin="", defines=''):
        self.username = username.strip()
        self.pw_hash = generate_password_hash(password)
        if passwordhash is not None:
            self.pw_hash = passwordhash
        self.funds = funds
        try:
            self.sheet = VampireCharacter.deserialize(sheet)
        except:
            self.sheet = FenCharacter.deserialize(sheet)

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

    @staticmethod
    def deserialize_old_sheets(inp):
        if inp == b'':
            return []
        oldsheets = pickle.loads(inp)
        for o in oldsheets:
            o.legacy_convert()
        oldsheets.sort(key=lambda x: x.timestamp)
        return oldsheets

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def update_sheet(self, form):
        print("logging character change\n", form)
        if "newsheet" in form.keys():
            self.oldsheets.append(VampireCharacter())
            self.oldsheets[-1].setfromform(form)
        self.sheet.setfromform(form)

    @property
    def sheetpublic(self):
        return "public" in self.sheet.meta["Notes"][:22]


class Userlist(object):
    def __init__(self, key="", preload=False, sheets=True):
        self.key = key
        self.userlist = []
        self.file = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        if preload:
            self.loaduserlist(sheets)

    def loaduserlist(self, sheets=True):  # converts the SQL table into a list for easier access
        db = connect_db()
        print("loading userlist")
        if sheets:
            cur = db.execute('SELECT username, passwordhash, funds, '
                             'sheet, oldsheets, defines, admin FROM users')
            self.userlist = [User(username=row[0], passwordhash=row[1], funds=row[2],
                                  sheet=row[3], oldsheets=row[4], defines=row[5], admin=row[6]) for row in
                             cur.fetchall()]
        else:
            cur = db.execute('SELECT username, passwordhash, funds,'
                             'defines, admin FROM users')
            self.userlist = [User(username=row[0], passwordhash=row[1], funds=row[2],
                                  defines=row[3], admin=row[4]) for row in
                             cur.fetchall()]
        db.close()
        print("loaded userlist")

    def saveuserlist(self):
        # writes/overwrites the SQL table with the maybe changed list. this is not performant at all
        db = connect_db()

        for u in self.userlist:
            if u.sheet.checksum() != 0:
                d = dict(username=u.username, pwhash=u.pw_hash, funds=u.funds,
                         sheet=u.sheet.serialize(), oldsheets=u.serialize_old_sheets(), defines=pickle.dumps(u.defines),
                         admin=u.admin)
                db.execute(
                    "INSERT OR REPLACE INTO users (username, passwordhash, funds, "
                    "sheet, oldsheets, defines, admin) "
                    "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :defines, :admin)", d)
            else:
                d = dict(username=u.username, pwhash=u.pw_hash, funds=u.funds,
                         defines=pickle.dumps(u.defines), admin=u.admin, emptysheet=VampireCharacter().serialize())
                db.execute(
                    "INSERT OR REPLACE INTO users (username, passwordhash, funds,  "
                    "sheet, oldsheets, defines, admin) "
                    "VALUES (:username,:pwhash, :funds,"
                    "COALESCE((SELECT sheet FROM users WHERE username = :username), :emptysheet),"
                    "COALESCE((SELECT oldsheets FROM users WHERE username = :username), ''),"
                    " :defines, :admin)", d)

        db.commit()
        db.close()

    def adduser(self, user, password):
        if self.contains(user):
            return 'Name is taken!'
        u = User(username=user, password=password)
        d = dict(username=u.username, pwhash=u.pw_hash, funds=u.funds,
                 sheet=u.sheet.serialize(), oldsheets=u.serialize_old_sheets(), defines=pickle.dumps(u.defines),
                 admin=u.admin)
        db = connect_db()
        db.execute(
            "INSERT OR REPLACE INTO users (username, passwordhash, funds, "
            "sheet, oldsheets, defines, admin) "
            "VALUES (:username,:pwhash, :funds, :sheet, :oldsheets, :defines, :admin)", d)
        db.commit()
        db.close()
        return None

    def contains(self, user):
        for u in self.userlist:
            if u.username == user:
                return True
        return False

    def getuserbyname(self, username) -> Union[User, None]:
        for u in self.userlist:
            if u.username == username:
                return u
        return None

    def loaduserbyname(self, username)-> Union[User, None]:
        db = connect_db()
        cur = db.execute('SELECT username, passwordhash, funds, '
                         'sheet, oldsheets, defines, admin FROM users WHERE username = (?)', (username,))
        self.userlist = [User(username=row[0], passwordhash=row[1], funds=row[2],
                              sheet=row[3], oldsheets=row[4], defines=row[5], admin=row[6]) for row in
                         cur.fetchall()]
        db.close()
        return self.getuserbyname(username)

    def getfunds(self, user=None, username=None):
        if user is None:
            if username is not None:
                user = self.getuserbyname(username)
        if user is not None:
            return user.funds
        return None

    def valid(self, user, password) -> bool:
        for u in self.userlist:
            if u.username == user:
                if u.check_password(password):
                    return True
        return False
