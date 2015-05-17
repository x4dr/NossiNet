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

    def addKudos(self, kudos):
        self.Kudos += kudos


class Userlist(object):
    def __init__(self, key):
        self.key = key
        self.userlist = None
        self.loaduserlist()
        f = open('users', 'w')
        f.close()

    def loaduserlist(self):
        f = open('users', 'rb')
        try:
            self.userlist = pickle.load(f)
            f.close()
        except:
            self.userlist = []

    def saveuserlist(self):
        f = open('users', 'wb')
        pickle.dump(self.userlist, f, protocol=pickle.HIGHEST_PROTOCOL)
        f.close()

    def adduser(self, user):
        self.userlist.append(user)
        self.saveuserlist()
