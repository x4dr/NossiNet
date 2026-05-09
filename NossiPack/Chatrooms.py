import re
import time
from datetime import datetime, UTC
from typing import List, Tuple, Optional
from functools import lru_cache

from flask import session

# from flask_socketio import emit
from gamepack.Dice import DescriptiveError

from Data import connect_db


def dummy(*args, **kwargs):
    pass


emit = dummy


@lru_cache(maxsize=50)
def _resolve_discord_id(discord_id: str) -> Optional[str]:
    with connect_db("resolving mentions") as db:
        # Try exact match or the snowflake(username) format
        res = db.execute(
            "SELECT user FROM configs WHERE option = 'discord' AND (value = :id OR value LIKE :pattern);",
            dict(id=discord_id, pattern=f"{discord_id}(%"),
        ).fetchone()
        return res[0] if res else None


class Chatroom:
    def __init__(self, name: str, mailbox: bool = False):
        self.name = re.sub(r"_+", "", name)
        self.mailbox = mailbox
        if self.mailbox:
            self.name += "_mailbox"
        self.users: List[str] = []
        self.password = ""
        self.presentusers: dict = {}

    def chatlog(self, limit: int = 1000) -> List[Tuple[str, float]]:
        """last [limit] entries in the chatlog"""
        with connect_db("loadchatlog") as db:
            rows = db.execute(
                "SELECT line, time FROM chatlogs WHERE room = ? "
                "ORDER BY linenr DESC LIMIT ?",
                [self.name, limit],
            ).fetchall()
        chatlog = [(row[0], float(row[1])) for row in rows[-1000:]]
        if not chatlog:
            self.addline("start of " + self.name)
            return self.chatlog(limit)
        return chatlog

    def resolve_mentions(self, line: str) -> str:
        def replace_mention(match: re.Match) -> str:
            discord_id = match.group(1)
            resolved = _resolve_discord_id(discord_id)
            return resolved if resolved else match.group(0)

        return re.sub(r"<@!?(\d+)>", replace_mention, line)

    def addlinetolog(self, line: str, time_: float) -> None:
        line = self.resolve_mentions(line)
        with connect_db("adding line") as db:
            db.execute(
                "INSERT INTO chatlogs (line, time, room) VALUES (:line, :time, :room)",
                dict(line=line, time=time_, room=self.name),
            )
            db.commit()

    def addline(self, line: str, supresssave: bool = False) -> None:
        if not session["user"] in self.presentusers:
            raise DescriptiveError(
                "You got disconnected, because you left this room or were inactive."
            )
        try:
            emit(
                "Message", {"data": time.strftime("%H:%M") + " " + line}, room=self.name
            )
        except Exception:
            pass

        if not supresssave:
            self.addlinetolog(line, time.time())

    def userjoin(self, user):
        if self.mailbox and not (
            re.match(r"(.*)_.*", self.name).group(1) == session.get("user")
        ):
            return False
        if user in self.presentusers:
            return False
        self.presentusers[user] = time.time()
        self.addline(user + " joined the room!")
        return True

    def userleave(self, user):
        if user in self.presentusers:
            self.presentusers.pop(user)
            self.addline(user + " left the room!")
            return True
        return False

    def getlog(self, user, length=100):
        present = False
        result = ""
        if self.mailbox and not (
            re.match(r"(.*)_.*", self.name).group(1) == session.get("user")
        ):
            return "####UNAUTHORIZED####"

        if self.mailbox:
            result += "mailbox"
        result += "\n" + self.name + "\n"

        for line, t in reversed(self.chatlog(length)):
            if line == user + " joined the room!":
                present = True
            if present:
                result = (
                    result
                    + datetime.fromtimestamp(t, UTC).strftime("%Y/%m/%d-%H:%M:%S ")
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
