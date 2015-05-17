import os
import sys

__author__ = 'maric'

from werkzeug.security import generate_password_hash, check_password_hash
import pickle


class User(object):
    def __init__(self, username, password):
        self.username = username
        self.pw_hash = generate_password_hash(password)
        self.Kudos = 0

    def set_password(self, oldpassword, newpassword):
        if check_password_hash(oldpassword):
            self.pw_hash = generate_password_hash(newpassword)
            return True
        else:
            return False

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def addkudos(self, kudos):
        self.Kudos += kudos


class Userlist(object):
    def __init__(self, key=""):
        self.key = key
        self.userlist = []
        self.file = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        self.loaduserlist()

    def loaduserlist(self):
        f = open(self.file + os.sep + 'users', 'rb')
        try:
            self.userlist = pickle.load(f)
            f.close()
        except:
            self.userlist = []

    def saveuserlist(self):
        f = open(self.file + os.sep + 'users', 'wb')
        pickle.dump(self.userlist, f, protocol=pickle.HIGHEST_PROTOCOL)
        f.close()

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

    def valid(self, user, password):
        for u in self.userlist:
            if u.username == user:
                if u.check_password(password):
                    return True
        return False
