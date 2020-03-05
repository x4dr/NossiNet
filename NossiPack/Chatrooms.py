import re
import time
from typing import List, Tuple, Union

from flask import session
from flask_socketio import emit
from datetime import datetime

from NossiPack.krypta import DescriptiveError
from NossiSite.helpers import connect_db


def echo(message):
    try:
        emit("Message", {"data": session["user"] + message})
    except:
        pass


class Chatroom:
    def __init__(self, name, mailbox=False):
        self.name = re.sub(r"_+", "", name)
        self.mailbox = mailbox
        if self.mailbox:
            self.name += "_mailbox"
        self.users = []
        self.password = ""  # unimplemented
        self.presentusers = {}

    def chatlog(self, limit=1000) -> List[Tuple[str, Union[int, float]]]:
        """last [limit] entries in the chatlog"""
        with connect_db("loadchatlog") as db:
            rows = db.execute(
                "SELECT line, time FROM chatlogs WHERE room = ? ORDER BY linenr DESC LIMIT ?",
                [self.name, limit],
            ).fetchall()
        chatlog = [(row[0], float(row[1])) for row in rows[-1000:]]
        if not chatlog:
            self.addline("start of " + self.name)
            return self.chatlog(limit)  # another round to get the correct time
        return chatlog

    def addlinetolog(self, line, time_):
        db = connect_db("adding line")
        db.execute(
            "INSERT INTO chatlogs (line, time, room)" "VALUES (:line, :time ,:room)",
            dict(line=line, time=time_, room=self.name),
        )

    def addline(self, line):
        if not session["user"] in self.presentusers.keys():
            raise DescriptiveError(
                "You got disconnected, because you left this room or were inactive."
            )
        try:
            emit(
                "Message", {"data": time.strftime("%H:%M") + " " + line}, room=self.name
            )
        except:
            print(
                "Message",
                {"data": time.strftime("%H:%M") + " " + line},
                self.name,
                "could not be emitted",
            )
        self.addlinetolog(line, time.time())

    def userjoin(self, user):
        if self.mailbox and not (
            re.match(r"(.*)_.*", self.name).group(1) == session.get("user")
        ):
            return False
        if user in self.presentusers.keys():
            return False
        self.presentusers[user] = time.time()
        self.addline(user + " joined the room!")
        return True

    def userleave(self, user):
        if user in self.presentusers.keys():
            self.presentusers.pop(user)
            self.addline(user + " left the room!")
            return True
        return False

    def getlog(self, user):
        present = False
        result = ""
        if self.mailbox and not (
            re.match(r"(.*)_.*", self.name).group(1) == session.get("user")
        ):
            return "####UNAUTHORIZED####"

        if self.mailbox:
            result += "mailbox"
        result += "\n" + self.name + "\n"

        for line, t in self.chatlog(10 ** 10):
            if line == user + " joined the room!":
                present = True
            if present:
                result = (
                    result
                    + datetime.utcfromtimestamp(t).strftime("%Y/%m/%d-%H:%M:%S ")
                    + line
                    + "\n"
                )
            if line == user + " left the room!":
                present = False
        return result

    def getuserlist_text(self):
        result = ""
        for u in sorted([x[0] for x in sorted(self.users) if len(x) > 0]):
            result = result + u + "\n"
        return result
