import datetime
from flask_socketio import emit
from flask import session
from NossiSite.helpers import connect_db
import re
import time


def echo(message):
    try:
        emit('Message', {'data': session['user'] + message})
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
        self.presentusers = {}
        self.loadchatlog()

    def loadchatlog(self):  # converts the SQL table into a list for easier access
        db = connect_db("loadchatlog")
        touched = False
        # db.set_trace_callback(echo)
        rows = db.execute("SELECT linenr, line, time  FROM chatlogs WHERE room = ? ORDER BY linenr ASC",
                          [self.name]).fetchall()
        db.close()

        self.chatlog = [[int(row[0]), row[1], row[2]] for row in rows[-1000:]]
        for row in self.chatlog:  # only the last 1000 lines will be loaded
            if self.newestlineindb < int(row[0]):
                self.newestlineindb = int(row[0])
        if not self.chatlog:
            touched = True
            self.chatlog = [[0, "start of " + self.name, time.time()]]
            if self.mailbox:
                self.userjoin(session['user'])
        if touched:
            self.savechatlog()

    def savechatlog(self):
        self.cleanup()
        db = connect_db("save chatlog")
        try:
            if self.chatlog and self.chatlog[-1] and self.chatlog[-1][0] - self.newestlineindb > 0:
                for i in reversed(range(len(self.chatlog))):
                    if self.chatlog[i][0] <= self.newestlineindb:
                        break
                    d = dict(linenr=str(self.chatlog[i][0]), line=self.chatlog[i][1],
                             time=self.chatlog[i][2], room=self.name)
                    try:
                        db.execute("INSERT INTO chatlogs (linenr, line, time, room)"
                                   "VALUES (:linenr,:line, :time ,:room)", d)
                    except Exception as inst:
                        print("writing", d, "to database failed", inst.args)
                self.newestlineindb = self.chatlog[-1][0]
                db.commit()
        except Exception:
            print("Chatlog not initialized")

        db.close()

    def addline(self, line, supresssave=False):
        if not session["user"] in self.presentusers.keys():
            raise Exception("You left this room or were inactive. (Testphase)")
        try:
            if len(self.chatlog) < 1:
                self.chatlog.append([0, line, time.time()])  # initial line
            self.chatlog.append([self.chatlog[-1][0] + 1, line, time.time()])
        except Exception as inst:  # # DEBUG! DUMP SHOULDNT BE NECESSARY
            print("self.chatlog:", self.chatlog, "\n\nline:", line, inst.args)
            emit("Message", {'data': "a fun little error occured, please inform maric"}, room=self.name)
        try:
            emit("Message", {'data': time.strftime("%H:%M") + " " + line}, room=self.name)
        except:
            pass  # probably initializing
        if not supresssave:
            self.savechatlog()

    def cleanup(self):
        def join_spam_remover(seq):
            iterable = iter(seq)
            try:
                prev = next(iterable)
                yield prev
            except Exception as e:
                print("exception during cleanup:", e, e.args)
                return []
            for element in iterable:
                if ":" not in element:
                    if ("joined the room!" in element[1] or "left the room!" in element[1]) and \
                            "joined the room!" in prev[1] or "connection established" in element[1]:
                        pass
                    else:
                        yield element
                else:
                    yield element
                prev = element
            self.chatlog = [x for x in join_spam_remover(self.chatlog)]

    def userjoin(self, user):
        if self.mailbox and not (re.match(r'(.*)_.*', self.name).group(1) == session.get('user')):
            return False
        if user in self.presentusers.keys():
            return False
        self.presentusers[user] = time.time()
        self.addline(user + ' joined the room!')
        return True

    def userleave(self, user):
        if user in self.presentusers.keys():
            self.presentusers.pop(user)
            self.addline(user + ' left the room!')
            return True
        else:
            return False

    def getlog(self, user):
        present = False
        result = ''
        if self.mailbox and not (re.match(r'(.*)_.*', self.name).group(1) == session.get('user')):
            return "####UNAUTHORIZED####"

        if self.mailbox:
            result += "mailbox"
        result += "\n" + self.name + "\n"

        for l, t in [(x[1], x[2]) for x in self.chatlog]:
            if l == user + ' joined the room!':
                present = True
            if present:
                result = result + time.strftime("%Y/%m/%d-%H:%M:%S ", time.gmtime(t)) + l + '\n'
            if l == user + ' left the room!':
                present = False
        return result

    def getuserlist_text(self):
        result = ''
        for u in sorted([x[0] for x in sorted(self.users) if len(x) > 0]):
            result = result + u + '\n'
        return result
