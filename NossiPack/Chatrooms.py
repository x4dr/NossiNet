from flask_socketio import emit
from flask import session
from NossiSite.helpers import connect_db
import re


def echo(message):
    try:
        emit('Message', {'data': session['user']  + message})
    except:
        pass


class Chatroom(object):
    def __init__(self, name, mailbox=False):
        self.name = re.sub(r'_+', '', name)
        self.mailbox = mailbox
        if self.mailbox:
            self.name += "_mailbox"
        self.users = []
        self.chatlog = []
        self.password = ''  # unimplemented
        self.newestlineindb = -1
        self.loadchatlog()

    def loadchatlog(self):  # converts the SQL table into a list for easier access
        db = connect_db()
        db.set_trace_callback(echo)
        rows = db.execute("SELECT linenr, line  FROM chatlogs WHERE room = ? ORDER BY linenr ASC",
                            [self.name]).fetchall()
        db.close()

        self.chatlog = [[int(row[0]), row[1]] for row in rows[-1000:]]
        for row in self.chatlog:  # only the last 1000 lines will be loaded
            if self.newestlineindb < int(row[0]):
                self.newestlineindb = int(row[0])
        if not self.chatlog:
            self.chatlog = [[0, "start of " + self.name]]
            if self.mailbox:
                self.userjoin(session['user'])
        self.savechatlog()

    def savechatlog(self):
        self.terminate_trailing_users()
        db = connect_db()
        if len(self.chatlog) - self.newestlineindb > 0:
            for i in reversed(range(len(self.chatlog))):
                if self.chatlog[i][0] <= self.newestlineindb:
                    break
                d = dict(linenr=str(self.chatlog[i][0]), line=self.chatlog[i][1], room=self.name)
                try:
                    db.execute("INSERT INTO chatlogs (linenr, line, room)"
                               "VALUES (:linenr,:line,:room)", d)
                except Exception as inst:
                    print("writing", d, "to database failed", inst.args)
            self.newestlineindb = self.chatlog[-1][0]
            db.commit()
        db.close()

    def addline(self, line):
        self.chatlog.append([self.chatlog[-1][0] + 1, line])
        try:
            emit("Message", {'data': line}, room=self.name)
        except:
            pass  # probably initializing
        self.savechatlog()

    def terminate_trailing_users(self):
        presentusers = {}
        for l in [x[1] for x in self.chatlog]:
            t = re.match(r'(.*) joined the room!', l)
            if t:
                presentusers[t.group(1)] = True
            t = re.match(r'(.*) left the room!', l)
            if t:
                presentusers[t.group(1)] = False
        for u in presentusers.keys():
            if presentusers[u] and (u not in self.users):
                self.addline(u + ' left the room!')

    def userjoin(self, user):
        if self.mailbox and not (re.match(r'(.*)_.*', self.name).group(1) == session.get('user')):
            return False
        for u in self.users:
            if u == user:
                return False
        self.users.append(user)
        self.addline(user + ' joined the room!')
        return True

    def userleave(self, user):
        actuallyleft = False
        for u in self.users:
                if u == user:
                    self.addline(user + ' left the room!')
                    actuallyleft = True
        self.users = [x for x in self.users if x != user]
        return actuallyleft

    def getlog(self, user):
        present = False
        result = ''
        if self.mailbox and not (re.match(r'(.*)_.*', self.name).group(1) == session.get('user')):
            return "####UNAUTHORIZED####"

        ###debug
        if self.mailbox:
            result+= "mailbox"
        result+="\n"+self.name+"\n"
        ###debug

        for l in [x[1] for x in self.chatlog]:
            if l == user + ' joined the room!':
                present = True
            if present:
                result = result + l + '\n'
            if l == user + ' left the room!':
                present = False
        return result

    def getuserlist_text(self):
        result = ''
        for u in sorted(self.users):
            result = result + u + '\n'
        return result
