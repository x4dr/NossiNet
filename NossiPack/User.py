import os
import sys

__author__ = 'maric'

from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE = '/home/maric/workspace/PycharmProjects/NossiNet/NN.db'


def connect_db():
    return sqlite3.connect(DATABASE)


class User(object):
    def __init__(self, username, password="", passwordhash=None, kudos=0):
        self.username = username
        self.pw_hash = generate_password_hash(password)
        if passwordhash is not None:
            self.pw_hash = passwordhash
        self.kudos = kudos

    def set_password(self, oldpassword, newpassword):
        if check_password_hash(oldpassword):
            self.pw_hash = generate_password_hash(newpassword)
            return True
        else:
            return False

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def addkudos(self, kudos):
        self.kudos += kudos


class Userlist(object):
    def __init__(self, key=""):
        self.key = key
        self.userlist = []
        self.file = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        self.loaduserlist()

    def loaduserlist(self):  # converts the SQL table into a list for easier access
        db = connect_db()
        cur = db.execute('SELECT username, passwordhash, kudos FROM users')
        self.userlist = [User(username=row[0], passwordhash=row[1], kudos=row[2]) for row in cur.fetchall()]
        db.close()

    def saveuserlist(
            self):  # writes/overwrites the SQL table with the maybe changed list. this is not performant at all
        db = connect_db()
        for u in self.userlist:
            d = dict(username=u.username, pwhash=u.pw_hash, kudos=u.kudos)
            db.execute("INSERT OR REPLACE INTO users (username, passwordhash, kudos) "
                       "VALUES (:username,:pwhash,:kudos)", d)
        db.commit()
        db.close()

    def adduser(self, user):
        if self.contains(user.username):
            return 'Name is taken!'
        self.userlist.append(user)
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

    def valid(self, user, password):
        for u in self.userlist:
            if u.username == user:
                if u.check_password(password):
                    return True
        return False
