import pathlib
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Tuple

import discord
from pytz import reference

last = {}
delete = []

date_formats = [
    "%d.%m.%y %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y",
    "%d.%m %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m %H:%M",
    "%d.%m",
    "%H:%M:%S",
    "%H:%M",
    "%y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M",
]
days = r"(?P<days>\d+)\s*([d:]|days?)"
hours = r"(?P<hours>\d+)\s*([h:]|hours?)"
mins = r"(?P<minutes>\d+)\s*([m:]|min(utes?)?)"
seconds = r"(?P<seconds>\d+)\s*(s(ec(onds?))?)"


def setup_db():
    path = pathlib.Path(__file__).parent / "remind.db"
    preexisting = path.exists()
    con = sqlite3.connect(path)
    if not preexisting:
        con.execute(
            "CREATE TABLE IF NOT EXISTS reminders ("
            "id integer PRIMARY KEY,"
            "channel int NOT NULL,"
            "executiondate DATE,"
            "message TEXT);"
        )
    return con


reminddb = setup_db()


def next_reminders():
    cur = reminddb.cursor()
    return cur.execute(
        "SELECT * FROM reminders ORDER BY executiondate LIMIT 3"
    ).fetchall()


def save_reminder(date, channel, message):
    cur = reminddb.cursor()
    cur.execute(
        "INSERT INTO reminders(executiondate,channel,message) VALUES (?,?,?)",
        (date, channel, message),
    )
    reminddb.commit()


def extract_time_delta(inp: str):
    inp = inp.strip()
    if inp.startswith("in") or any(x in inp[:8] for x in "dhms"):
        inp = inp[2:].strip() if inp.startswith("in") else inp

        rel = (
            re.match(r"\s*".join((days, hours, mins, seconds)) + r"?\s*", inp)
            or re.match(r"\s*".join((hours, mins, seconds)) + r"?\s*", inp)
            or re.match(r"\s*".join((hours, mins)) + r"?\s*", inp)
            or re.match(seconds + r"\s*", inp)  # seconds without optional ending
            or re.match(
                r"(?=\d)((?P<days>\d+)\s*d\s*)?"
                r"((?P<hours>\d+)\s*h\s*)?"
                r"((?P<minutes>\d+)\s*m?\s*)?"
                r"((?P<seconds>\d+)\s*s?)?\s*",
                inp,
            )
        )
        if rel:
            msg = inp[rel.end() :]
            d = int(rel.groupdict().get("days") or 0)
            h = int(rel.groupdict().get("hours") or 0)
            m = int(rel.groupdict().get("minutes") or 0)
            s = int(rel.groupdict().get("seconds") or 0)
            return d * 24 * 3600 + h * 3600 + m * 60 + s, msg
    else:
        inp = inp.removeprefix("at").removeprefix("on")
    date = re.match(r"^(?P<complete>[0-9.: -]*)", inp)
    msg = inp[len(date.group("complete")) :]
    for fmt in date_formats:
        try:
            d = datetime.strptime(date.group("complete").strip(), fmt)
            if d.year == 1900:
                d = d.combine(datetime.now().date(), d.time())
                if d < datetime.now():
                    d += timedelta(days=1)
            return (
                d.timestamp() - time.time(),
                msg,
            )
        except Exception:
            continue
    try:
        return int(date.group("complete")) * 60, msg  # minutes by default
    except ValueError:
        raise ValueError("unrecognizeable format:" + inp)


def newreminder(message: discord.Message, msg: str):
    msg = msg.strip()
    if msg.startswith("me "):
        msg = msg[3:]
        mention = message.author.mention + " "
    else:
        mention = ""
    relatime, msg = extract_time_delta(msg)
    msg = msg.removeprefix("that").strip()
    if msg.lower().startswith("i "):
        msg = "You" + msg[1:]
    date = time.time() + relatime
    save_reminder(date, message.channel.id, mention + msg)
    return datetime.fromtimestamp(int(date), reference.LocalTimezone())


def delreminder(reminder_id):
    cur = reminddb.cursor()
    cur.execute(
        "DELETE FROM reminders WHERE id=?",
        (reminder_id,),
    )
    reminddb.commit()


def listreminder(message: discord.Message) -> List[Tuple[int, int, float, str]]:
    cur = reminddb.cursor()
    return cur.execute(
        "SELECT id, channel, executiondate, message FROM reminders WHERE channel=?",
        (message.channel.id,),
    ).fetchall()
