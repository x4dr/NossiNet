from flask_socketio import emit


class Chatroom(object):
    def __init__(self, name):
        self.name = name
        self.mailbox = False
        self.users = []
        self.chatlog = []
        self.password = ''
        self.flag = False

    def loaduserlist(self):  # converts the SQL table into a list for easier access
        db = connect_db()
        cur = db.execute('SELECT username, passwordhash, kudos, funds, kudosdebt FROM users')
        self.userlist = [User(username=row[0], passwordhash=row[1],
                              kudos=row[2], funds=row[3], kudosdebt=row[4]) for row in cur.fetchall()]
        db.close()

    def saveuserlist(self):  # writes/overwrites the SQL table with the maybe changed list. this is not performant at all
        db = connect_db()

        for u in self.userlist:
            test = u.kudos
            test = u.kudosdebt
            d = dict(username=u.username, pwhash=u.pw_hash, kudos=u.kudos, funds=u.funds, kudosdebt=u.kudosdebt)
            db.execute("INSERT OR REPLACE INTO users (username, passwordhash, kudos, funds, kudosdebt) "
                       "VALUES (:username,:pwhash,:kudos, :funds, :kudosdebt)", d)
        db.commit()
        db.close()

    def addline(self, line):
        self.flag = True
        self.chatlog.append(line)
        emit("Message", {'data': line}, room=self.name)

    def userjoin(self, user):
        for u in self.users:
            if u == user:
                self.addline(user + " tried to join twice.")
                return
        self.users.append(user)
        self.addline(user + ' joined the room!')

    def userleave(self, user):
        for u in self.users:
            if u == user:
                self.addline(user + ' left the room!')

        self.users = [x for x in self.users if x != user]

    def getlog(self, user):
        present = False
        result = ''
        for l in self.chatlog:
            if l == user + ' joined the room!':
                present = True
            if l == user + ' left the room!':
                present = False
            if present:
                result = result + l + '\n'
        return result

    def getuserlist_text(self):
        result = ''
        for u in sorted(self.users):
            result = result + u + '\n'
        return result

