import os
import sys
import pickle

from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from NossiPack.Character import Character

__author__ = 'maric'

DATABASE = './NN.db'


def connect_db():
    return sqlite3.connect(DATABASE)


class User(object):
    def __init__(self, username, password="", passwordhash=None, kudos=10, funds=0, kudosdebt="",
                 sheet=Character().serialize(), oldsheets=b'', admin="", defines=''):
        self.kudosdebt = kudosdebt
        self.username = username.strip()
        self.pw_hash = generate_password_hash(password)
        if passwordhash is not None:
            self.pw_hash = passwordhash
        self.kudos = kudos
        self.funds = funds
        self.sheet = Character.deserialize(sheet)
        self.oldsheets = self.deserialize_old_sheets(oldsheets)
        if admin == "Administrator":
            self.admin = "Administrator"
        else:
            self.admin = ""
        self.defines = {}
        if defines:
            self.defines = pickle.loads(defines)
      #  print(defines, "><defines><")

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
        if "newsheet" in form.keys():
            form.pop('newsheet')
            self.oldsheets.append(Character())
            self.oldsheets[-1].setfromform(form)
        self.sheet.setfromform(form)

    def addkudos(self, kudos):
        if kudos == 0:
            return  # so that if two people both owe each other it will not create an endless loop
        l = self.get_kudosdebts()
        u = None
        i = 0
        while i < len(l):
            d = l[i]
            if int(d.get('remaining')) > 0:
                ul = Userlist()
                u = ul.getuserbyname(d.get('loaner'))
                break

        if u is not None:
            tax = int(0.1 * kudos)  # rounds down, so < 10 kudos transactions are not taxed
            kudos += -tax  # yes this means that negative kudos is applied as well
            d['remaining'] = int(d.get('remaining')) - tax  # can go below zero, then its overtaxed ^^ lucky/unlucky
            u.addkudos(tax)  # if the loaner is in debt it will cascade
        self.kudos += kudos
        self.set_kudosdebts(l)

    def get_kudosdebts(self):
        kd = self.kudosdebt
        kd = kd.split("|")
        entries = []
        for s in kd:
            tmp = s.split("#")
            if len(tmp) == 5:
                entries.append(dict(loaner=tmp[0], state=tmp[1], remaining=tmp[2], original=tmp[3], id=tmp[4]))
            else:
                if tmp != ['']:  # sometimes deleted entries persist as empty entries, this is not problematic
                    print("kudos error with: ", tmp)
        return entries

    def set_kudosdebts(self, entries):
        result = ""
        for e in entries:
            result += e.get('loaner') + "#" + e.get('state') + "#" + str(e.get('remaining')) + "#" + str(e.get(
                'original')) + "#" + str(e.get('id')) + "|"
        print(result)
        self.kudosdebt = result

    def add_kudosoffer(self, loaner):
        l = self.get_kudosdebts()
        i = 0
        if len(l) > 0:
            i = int(l[-1].id) + 1
        l.append(dict(loaner=loaner, state="unaccepted", remaining="-1", original="-1", id=str(i)))
        self.set_kudosdebts(l)


class Userlist(object):
    def __init__(self, key=""):
        self.key = key
        self.userlist = []
        self.file = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        self.loaduserlist()

    def loaduserlist(self):  # converts the SQL table into a list for easier access
        db = connect_db()
        cur = db.execute('SELECT username, passwordhash, kudos, funds, kudosdebt, '
                         'sheet, oldsheets, defines, admin FROM users')
        self.userlist = [User(username=row[0], passwordhash=row[1], kudos=row[2], funds=row[3], kudosdebt=row[4],
                              sheet=row[5], oldsheets=row[6], defines=row[7], admin=row[8]) for row in
                         cur.fetchall()]
        db.close()

    def saveuserlist(
            self):  # writes/overwrites the SQL table with the maybe changed list. this is not performant at all
        db = connect_db()

        for u in self.userlist:
            d = dict(username=u.username, pwhash=u.pw_hash, kudos=u.kudos, funds=u.funds, kudosdebt=u.kudosdebt,
                     sheet=u.sheet.serialize(), oldsheets=u.serialize_old_sheets(), defines=pickle.dumps(u.defines),
                     admin=u.admin)
            db.execute(
                "INSERT OR REPLACE INTO users (username, passwordhash, kudos, funds, kudosdebt, "
                "sheet, oldsheets, defines, admin) "
                "VALUES (:username,:pwhash,:kudos, :funds, :kudosdebt, :sheet, :oldsheets, :defines, :admin)", d)
        db.commit()
        db.close()

    def adduser(self, user):
        if self.contains(user.username):
            return 'Name is taken!'
        self.userlist.append(user)
        print("kudosdebt:", user.kudosdebt)
        print(self.userlist[-1].kudosdebt)
        self.saveuserlist()
        return None

    def contains(self, user):
        for u in self.userlist:
            if u.username == user:
                return True
        return False

    def getuserbyname(self, username):
        for u in self.userlist:
            if u.username == username:
                return u
        return None

    def getfunds(self, user=None, username=None):
        if user is None:
            if username is not None:
                user = self.getuserbyname(username)
        if user is not None:
            return user.funds
        return None

    def valid(self, user, password):
        for u in self.userlist:
            if u.username == user:
                if u.check_password(password):
                    return True
        return False
