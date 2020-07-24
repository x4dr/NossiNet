import re
import time
from datetime import datetime
from typing import Union

import discord
from dateparser import parse
from discord import abc

import Data
from NossiPack.krypta import DescriptiveError

remindfile = "reminders.txt"
Data.append(remindfile, "")
last = {}
delete = []


async def reminders(getchannel):
    rembuf = []
    nexttime = 10
    now = time.time()
    for line in Data.get(remindfile).splitlines():

        if not line:
            continue
        channelid, date, message, instructions = [p.strip() for p in line.split(";")]
        channel: Union[discord.TextChannel, abc.PrivateChannel] = getchannel(
            int(channelid)
        )
        if channel is None:
            continue
        if line in delete:
            delete.remove(line)
            await channel.send(message + " " + instructions + " has been deleted")
            continue
        date = float(date)
        if date < now:
            await channel.send("Reminder: " + message + " " + instructions)
            repacked = (channelid, *instruct(date, message, instructions, now))
            if repacked[1] is not None:
                rembuf.append(";".join(str(x) for x in repacked))
                last[channelid] = rembuf[-1]
            date = repacked[1]
            if not date:
                continue
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


def instruct(date, message, instructions: str, now):
    newinstr = []
    times = 0
    for i in instructions.split(","):
        i = i.strip()
        if i.startswith("repeat after "):
            after = now - parse(i[13:]).timestamp()
            if not after:
                raise DescriptiveError(i[13:] + " is not a valid time measure")
            date = date + after
        elif i.endswith("times"):
            times = int(i[:-5])
            continue
        newinstr.append(i)
    if times > 1:
        newinstr.append(str(times - 1) + " times")
    else:
        return None, "", ""
    return date, message, ", ".join(newinstr)


def newreminder(channelid, message):
    date, message, instructions = [
        x.strip() for x in (message.split(";") + ["", ""])[:3]
    ]
    date = datetime.timestamp(parse(date))
    while date < time.time():
        date += 86400  # 1day
    newline = ";".join((channelid, str(round(date)), message, instructions)) + "\n"
    Data.append(remindfile, newline)


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
            channelid, date, msg, instructions = [p.strip() for p in line.split(";")]
            toshow += f"{datetime.fromtimestamp(int(date))}: {msg}; {instructions}\n"
    toshow = re.sub("<@!(.*?)>", mentionreplace, toshow)
    print(toshow)
    await message.channel.send("Reminders:\n" + toshow)
