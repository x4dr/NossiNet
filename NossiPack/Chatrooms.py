"""Chatroom management for real-time communication."""

import contextlib
import re
import time
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from flask import session

# from flask_socketio import emit
from gamepack.Dice import DescriptiveError

from Data import connect_db


def dummy(*args: Any, **kwargs: Any) -> None:
    """No-op placeholder for optional callbacks."""
    pass


emit = dummy


@lru_cache(maxsize=50)
def _resolve_discord_id(discord_id: str) -> str | None:
    with connect_db("resolving mentions") as db:
        # Try exact match or the snowflake(username) format
        res = db.execute(
            "SELECT user FROM configs WHERE option = 'discord' AND (value = :id OR value LIKE :pattern);",
            dict(id=discord_id, pattern=f"{discord_id}(%"),
        ).fetchone()
        return res[0] if res else None


class Chatroom:
    """Represents a chat room with message logging and user presence tracking."""

    def __init__(self, name: str, *, mailbox: bool = False):
        """Initialize a Chatroom.

        Args:
            name: The room name.
            mailbox: If True, treat as a private mailbox room.
        """
        self.name = re.sub(r"_+", "", name)
        self.mailbox = mailbox
        if self.mailbox:
            self.name += "_mailbox"
        self.users: list[str] = []
        self.password = ""
        self.presentusers: dict[str, Any] = {}

    def chatlog(self, limit: int = 1000) -> list[tuple[str, float]]:
        """Last [limit] entries in the chatlog."""
        with connect_db("loadchatlog") as db:
            rows = db.execute(
                "SELECT line, time FROM chatlogs WHERE room = ? " "ORDER BY linenr DESC LIMIT ?",
                [self.name, limit],
            ).fetchall()
        chatlog = [(row[0], float(row[1])) for row in rows[-1000:]]
        if not chatlog:
            self.addline("start of " + self.name)
            return self.chatlog(limit)
        return chatlog

    def resolve_mentions(self, line: str) -> str:
        """Replace Discord-style mentions with resolved usernames.

        Args:
            line: The message text to process.

        Returns:
            The line with <@!id> mentions replaced by usernames.
        """

        def replace_mention(match: re.Match[str]) -> str:
            discord_id = match.group(1)
            resolved = _resolve_discord_id(discord_id)
            return resolved or match.group(0)

        return re.sub(r"<@!?(\d+)>", replace_mention, line)

    def addlinetolog(self, line: str, time_: float) -> None:
        """Persist a message to the chat log database.

        Args:
            line: The message text.
            time_: Unix timestamp of the message.
        """
        line = self.resolve_mentions(line)
        with connect_db("adding line") as db:
            db.execute(
                "INSERT INTO chatlogs (line, time, room) VALUES (:line, :time, :room)",
                dict(line=line, time=time_, room=self.name),
            )
            db.commit()

    def addline(self, line: str, *, supresssave: bool = False) -> None:
        """Add a message line to the room, optionally saving to log.

        Args:
            line: The message text.
            supresssave: If True, skip persisting to the database.
        """
        if session["user"] not in self.presentusers:
            raise DescriptiveError(
                "You got disconnected, because you left this room or were inactive.",
            )
        with contextlib.suppress(Exception):
            emit(
                "Message",
                {"data": time.strftime("%H:%M") + " " + line},
                room=self.name,
            )

        if not supresssave:
            self.addlinetolog(line, time.time())

    def userjoin(self, user: str) -> bool:
        """Add a user to the room's presence list.

        Args:
            user: The username to join.

        Returns:
            True if the user joined, False if already present or unauthorized.
        """
        if (
            self.mailbox
            and (m := re.match(r"(.*)_.*", self.name))
            and m.group(1)
            != session.get(
                "user",
            )
        ):
            return False
        if user in self.presentusers:
            return False
        self.presentusers[user] = time.time()
        self.addline(user + " joined the room!")
        return True

    def userleave(self, user: str) -> bool:
        """Remove a user from the room's presence list.

        Args:
            user: The username to leave.

        Returns:
            True if the user left, False if they were not present.
        """
        if user in self.presentusers:
            self.presentusers.pop(user)
            self.addline(user + " left the room!")
            return True
        return False

    def getlog(self, user: str, length: int = 100) -> str:
        """Retrieve the chat log for a user since they last joined.

        Args:
            user: The username requesting the log.
            length: Maximum number of recent log entries to scan.

        Returns:
            The formatted chat log text, or 'UNAUTHORIZED' for mailbox
            rooms the user does not own.
        """
        present = False
        result = ""
        if (
            self.mailbox
            and (m := re.match(r"(.*)_.*", self.name))
            and m.group(1)
            != session.get(
                "user",
            )
        ):
            return "####UNAUTHORIZED####"

        if self.mailbox:
            result += "mailbox"
        result += "\n" + self.name + "\n"

        for line, t in reversed(self.chatlog(length)):
            if line == user + " joined the room!":
                present = True
            if present:
                result = result + datetime.fromtimestamp(t, UTC).strftime("%Y/%m/%d-%H:%M:%S ") + line + "\n"
            if line == user + " left the room!":
                present = False
        return result

    def getuserlist_text(self) -> str:
        """Return a plain-text listing of users in the room.

        Returns:
            A string with one username per line.
        """
        result = ""
        for u in sorted([x[0] for x in sorted(self.users) if len(x) > 0]):
            result = result + u + "\n"
        return result
