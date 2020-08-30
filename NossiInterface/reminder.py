import re
import time
from datetime import datetime, timedelta
from typing import Union

import discord
from discord import abc
from pytz import reference

import Data

remindfile = "reminders.txt"
Data.append(remindfile, "")
last = {}
delete = []


async def reminders(getchannel):
    rembuf = []
    nexttime = 10
    now = time.time()
    for line in Data.get(remindfile).splitlines():
        if not line.strip():
            continue
        channelid, date, message = [p.strip() for p in line.split(";")]
        channel: Union[discord.TextChannel, abc.PrivateChannel] = getchannel(
            int(channelid)
        )
        if channel is None:
            print("NoneChannel message:", message)
        if line in delete:
            delete.remove(line)
            await channel.send(message + " has been deleted")
            continue
        date = float(date)
        if date < now:
            await channel.send("Reminder: " + message)
        else:
            rembuf.append(line)
        nexttime = max(0, min(nexttime, date - now))
    while delete:
        d = delete.pop()
        await getchannel(int(d[0])).send(
            f"could not delete {d} from "
            f"{list(tuple(p.strip() for p in line.split(';')) for line in Data.get(remindfile).splitlines())}"
        )
    Data.set(remindfile, "\n".join(rembuf) + "\n")
    return nexttime


def time_eat(inp: str):
    inp = inp.strip()
    m = re.match(r"^[ A-Za-z]*", inp)
    inp = inp[len(m.group(0)) :]
    if m.group(0).strip() == "in":
        if inp[:8].count(":") == 2:
            inp = inp.replace(":", "h", 1).replace(":", "m", 1)
        elif inp[:5].count(":") == 1:
            inp = inp.replace(":", "m", 1)
    rel = re.match(
        r"^(?P<complete>(((?P<hours>\d+) ?[h] ?)?(?P<minutes>\d+) ?[m] ?)?(?P<seconds>\d+) ?[s]? )",
        inp + " ",
    )
    if rel:
        msg = inp[len(rel.group("complete")) :]
        h = int(rel.group("hours") or 0)
        m = int(rel.group("minutes") or 0)
        s = int(rel.group("seconds") or 0)
        return h * 60 * 60 + m * 60 + s, msg
    date = re.match(r"^(?P<complete>[0-9.: -]*)", inp)
    msg = inp[len(date.group("complete")) :]

    for fmt in [
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
    ]:
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
        except:
            continue
    raise ValueError("unrecognizeable format:" + date.group("complete"))


def newreminder(message: discord.Message, msg: str):
    msg = msg.strip()
    if msg.startswith("me "):
        msg = msg[3:]
        mention = message.author.mention + " "
    else:
        mention = ""
    relatime, msg = time_eat(msg)
    date = time.time() + relatime
    newline = (
        ";".join((str(message.channel.id), str(round(date)), mention + msg)) + "\n"
    )
    Data.append(remindfile, newline)
    return datetime.fromtimestamp(int(date), reference.LocalTimezone())


async def delreminder(message):
    if last.get(str(message.channel.id), None) is None:
        await message.add_reaction("😕")
    else:
        delete.append(last.get(str(message.channel.id)))
        await message.add_reaction("👍")


async def listreminder(message: discord.Message, mentionreplace):
    toshow = ""
    for line in Data.get(remindfile).splitlines():
        if line.startswith(str(message.channel.id)):
            channelid, date, msg = [p.strip() for p in line.split(";")]
            toshow += f"{datetime.fromtimestamp(int(date), reference.LocalTimezone())}: {msg}\n"
    toshow = re.sub("<@!(.*?)>", mentionreplace, toshow)
    await message.channel.send("Reminders:\n" + toshow)
