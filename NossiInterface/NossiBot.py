import asyncio
import datetime
import os
import pathlib
import random
import re
import shelve
import string
import time
import traceback
from asyncio import sleep
from typing import Callable
from urllib.parse import quote

import discord
import requests
from dateparser import parse as dateparse

from Data import getnossihelp
from NossiInterface.RollInterface import rollhandle
from NossiInterface.Tools import discordname
from NossiPack.fengraph import chances
from NossiPack.krypta import DescriptiveError, read_nonblocking

bufferfile = "NossiBotBuffer"
shutdownflag = pathlib.Path("shutdown_nossibot")
if shutdownflag.exists():
    shutdownflag.unlink()  # ignore previously set shutdown
remindfile = os.path.expanduser("~/reminders.txt")
remindnext = os.path.expanduser("~/reminders_next.txt")


class MutationLoggingDict(dict):
    def __setitem__(self, key, value):
        dict.__setitem__(self, "mutated", True)
        dict.__setitem__(self, key, value)


storagefile = "~/NossiBot.storage"
persist = MutationLoggingDict()
with shelve.open(os.path.expanduser(storagefile)) as shelvefile:
    for shelvekey in shelvefile.keys():
        persist[shelvekey] = shelvefile[shelvekey]  # copy everything out
    persist["mutated"] = False
now = datetime.datetime.now

with open(os.path.expanduser("~/token.discord"), "r") as tokenfile:
    TOKEN = tokenfile.read().strip()

description = """NossiBot in Python"""
try:
    client = discord.Client()
except RuntimeError:
    client = discord.Client

    def event(coro: Callable):
        """mocking the event decorator for the case that we do static checking"""
        print(
            f"currently not in async mode, just for static checking "
            + getattr(coro, "__name__", "Unknown")
        )

    client.event = event
repeats = {}
active_channels = []


async def reminders(clearjob=None):
    jobs = []
    nextevent = 600
    with open(remindfile, "r") as f:
        for line in f.readlines():
            print(line)
            channelid, jobid, date, message, repeat, interval = [
                p.strip() for p in line.split(";")
            ]
            date = int(date)
            if date < time.time():
                print(jobid, "relevant now")
                if repeats.get(jobid, None) is None:
                    repeats[jobid] = 0
                if repeats[jobid] < int(repeat.split(" ")[1]):
                    print("reminding,")
                    delay = int(repeat.split(" ")[0])
                    reminddate = date + repeats[jobid] * delay
                    if time.time() > date + repeats[jobid] * delay:
                        repeats[jobid] += 1
                        status = (
                            ""
                            if int(repeat.split(" ")[1]) < 2
                            else str(repeats[jobid]) + "/" + repeat.split(" ")[1]
                        )
                        await client.get_channel(int(channelid)).send(
                            message + " " + status + jobid
                        )
                        nextevent = reminddate + delay - time.time()
                else:
                    print("resetting")
                    repeats[jobid] = 0
                    if interval and int(interval):
                        date += int(interval)
                    else:
                        repeat = ""
            else:
                nextevent = min(nextevent, date - time.time())
                print(nextevent, "until next event")
            if repeat and (jobid != clearjob):
                jobs.append(
                    ";".join(
                        [
                            channelid,
                            jobid,
                            str(round(date)),
                            message,
                            repeat,
                            str(interval),
                        ]
                    )
                )
            else:
                print("job", jobid, "deleted")
    with open(remindnext, "w") as f:
        f.write("\n".join(jobs))
    os.replace(remindnext, remindfile)


def newreminder(channelid, message):
    jobid = "".join(random.choice(string.ascii_letters).lower() for _ in range(4))
    print(message)
    date, message, repeat, interval = [
        x.strip() for x in (message.split(";") + ["", ""])[:4]
    ]
    date = datetime.datetime.timestamp(dateparse(date))
    repeat = (
        str(
            round(
                abs(
                    dateparse(repeat.split(" ")[0]) - datetime.datetime.now()
                ).total_seconds()
            )
        )
        + " "
        + repeat.split(" ")[1]
    )
    interval = str(
        round(abs(dateparse(interval) - datetime.datetime.now()).total_seconds())
    )
    newline = (
        ";".join((channelid, jobid, str(round(date)), message, repeat, interval)) + "\n"
    )
    print("new line:", newline)
    with open(remindfile, "a") as f:
        f.write(newline)


async def oraclehandle(msg, comment, send, author):
    msg = msg[6:].strip()
    errreport = msg.startswith("?")
    if errreport:
        msg = msg[1:].strip()
    sentmessage = None
    if msg.startswith("show"):
        try:
            parameters = msg[5:].split(" ")
            it = chances(parameters[:-2], parameters[-2], parameters[-1])
            sentmessage = await send(author.mention + comment + " " + next(it))
            for n in it:
                if isinstance(n, str):
                    await sentmessage.edit(content=author.mention + comment + " " + n)
                else:
                    await sentmessage.delete(delay=0.1)
                    await send(
                        author.mention + comment, file=discord.File(n, "graph.png")
                    )
        except Exception as e:
            print("exception during oracle show", e)
            if errreport:
                await author.send("oracle show error:" + " ".join(e.args))
            if sentmessage:
                await sentmessage.edit(content=author.mention + " ERROR")
                await sentmessage.delete(delay=3)
            await send(author.mention + " <selectors> <modifier> <number of quantiles>")
    else:
        try:
            parameters = msg.split(" ")
            it = chances(parameters[:-1], parameters[-1])
            sentmessage = await send(author.mention + comment + " " + next(it))
            n = ""
            p = (
                ", ".join(str(x) for x in parameters[:-1])
                + "@5"
                + (("R" + str(parameters[-1])) if parameters[-1] else "")
            )
            for n in it:
                if isinstance(n, str):
                    await sentmessage.edit(content=author.mention + comment + " " + n)
            if n:
                n, avg, dev = n
                await sentmessage.edit(
                    content=(
                        author.mention
                        + comment
                        + "```"
                        + p
                        + " avg:"
                        + str(avg)
                        + " dev: "
                        + str(dev)
                        + "\n"
                        + n
                        + "```"
                    )
                )
            else:
                raise DescriptiveError("no data!")
        except Exception as e:
            print("exception during oracle", e)
            if sentmessage:
                await sentmessage.edit(content=author.mention + " ERROR")
                await sentmessage.delete(delay=3)
            if errreport:
                await author.send("Oracle error: " + " ".join(str(x) for x in e.args))
            await send(author.mention + " <selectors> <modifier>")


async def weaponhandle(msg, comment, send, author):
    n = requests.get(
        "http://127.0.0.1/"
        + "/".join(quote(x.strip()) for x in msg.split(":", 2))
        + "/txt"
    )
    if n.status_code == 200:
        n = n.content.decode("utf-8")
        await send(author.mention + comment + "```" + msg + "\n" + n + "```")
    else:
        print("failed request:", n.status_code, n.url)
        return


async def specifichandle(msg, comment, send, author):
    msg = msg[len("specific:") :].strip()
    n = requests.get("http://127.0.0.1/specific/" + quote(msg.strip()) + "/raw")
    if n.status_code == 200:
        n = n.content.decode("utf-8")
        await send(author.mention + comment + "```" + msg + "\n" + n[:1950] + "```")
        for replypart in [n[i : i + 1950] for i in range(1950, len(n), 1950)]:
            await send("```" + replypart + "```")
        return True
    print("failed request:", n.status_code, n.url)
    return False


async def handle_defines(msg, send, message):
    msg = msg.strip("`")
    if isinstance(message, str):  # message is name already

        async def error(a):
            raise Exception(a)

        async def nop(a):
            print(a)

        class Fake:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        author = message
        message = Fake(author=Fake(send=error), add_reaction=nop)
        send = send or nop
    else:
        author = discordname(message.author)
    try:
        defines = persist[author]["defines"]
    except KeyError:
        persist[author] = {"defines": {}}
        defines = {}
    if msg.startswith("def"):
        msg = msg[3:].strip()
        if "=" in msg:
            question = re.compile(r"^=\s*?")
            if question.match(msg):
                msg = question.sub(msg, "").strip()
                if not msg:
                    defstring = "defines are:\n"
                    for k, v in defines.items():
                        defstring += "def " + k + " = " + v + "\n"
                    for replypart in [
                        defstring[i : i + 1950] for i in range(0, len(defstring), 1950)
                    ]:
                        await message.author.send(replypart)
                    return None
            define, value = [x.strip() for x in msg.split("=", 1)]
            defines[define] = value
            persist[author]["defines"] = defines
            persist["mutated"] = True
            await message.add_reaction("\N{THUMBS UP SIGN}")
            msg = None
        else:
            await message.author.send(defines[msg])
            msg = None
    elif msg.startswith("undef "):
        msg = msg[6:]
        change = False
        for k in list(defines.keys()):
            if re.match(msg + r"$", k):
                change = True
                del defines[k]
        if change:
            persist[author]["defines"] = defines
            await message.add_reaction("\N{THUMBS UP SIGN}")
        else:
            await message.add_reaction("\N{BLACK QUESTION MARK ORNAMENT}")
        msg = None
    else:
        oldmsg = ""
        counter = 0
        while oldmsg != msg:
            oldmsg = msg
            counter += 1
            if counter > 1000:
                await send(
                    "... i think i have some issues with the defines.\n" + msg[:1000]
                )
            for k, v in defines.items():
                pat = r"\b" + re.escape(k) + r"\b"
                msg = re.sub(pat, v, msg)
    return msg


async def handle_inp(inp):
    for line in inp:
        if line.find("#") != -1:
            name = line[: line.find("#") + 5]
            line = line[len(name) :].strip()
            acc = line[: line.find("message: ")].strip()
            line = line[line.find(":") + 1 :].strip()
            if persist[name].get("NossiAccount", None) == acc:
                print(f"saving: {line, name}")
                await handle_defines(line, None, name)
            else:
                print(
                    "access error:", persist[name].get("NossiAccount", None), "!=", acc
                )
        else:
            print("received message without discord name:", line)


async def tick():
    next_call = time.time()
    while True:
        k = "remind"
        try:
            await reminders()
        except Exception as e:
            print("Exception reminding:", e, e.args, traceback.format_exc())
        inp = read_nonblocking(bufferfile)
        if inp:
            await handle_inp(inp)
        try:
            if persist["mutated"]:
                with shelve.open(os.path.expanduser(storagefile)) as shelvingfile:
                    for k in persist:
                        if k == "mutated":
                            continue  # mutated will never be saved!
                        shelvingfile[k] = persist[k]
                    persist["mutated"] = False
        except Exception as e:
            print(f"Exception in tick with {k}:", e, e.args, traceback.format_exc())
        next_call += 10
        if client.is_closed():
            break
        if shutdownflag.exists():
            shutdownflag.unlink()
            info = await client.application_info()
            await info.owner.send("I got Killed")
        await asyncio.sleep(next_call - time.time())


@client.event
async def on_ready():
    print("Logged in as")
    print("Name:", client.user.name)
    print("ID:", client.user.id)
    print("------")
    asyncio.create_task(tick())
    p = discord.Permissions(117824)
    print(discord.utils.oauth_url(client.user.id, p))
    info = await client.application_info()
    await info.owner.send("I Live")
    persist["owner"] = discordname(info.owner)


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    message = None
    for ch in active_channels:
        try:
            message = await ch.fetch_message(payload.message_id)
        except:  # not found here
            pass
    if message is not None:
        await on_message(message)


@client.event
async def on_message(message: discord.Message):
    msg: str = message.content
    send = message.channel.send
    if message.author == client.user:
        return
    if msg.startswith("NossiBot") or isinstance(message.channel, discord.DMChannel):
        msg = msg[len("NossiBot") :] if msg.startswith("NossiBot") else msg
        if msg.strip() == "help":
            with getnossihelp() as f:
                helpmsg = f.read()
                replypart = ""
                lines = helpmsg.split("\n")
                i = 0
                while len(replypart) < 1950 and i <= len(lines):
                    if i < len(lines) and len(replypart) + len(lines[i]) < 1950:
                        replypart += lines[i] + "\n"
                        i += 1
                    else:
                        if replypart:
                            await message.author.send("```" + replypart + "```")
                            await sleep(1)
                            replypart = ""
                        else:
                            if i < len(lines):
                                await message.author.send(
                                    "```" + lines[i][:1990] + "```"
                                )
            return
        if "DIE" in msg and discordname(message.author) == persist["owner"]:
            await message.add_reaction("\U0001f480")
            await send("I shall die.")
            await client.close()
            return
        if msg.lower().startswith("i am ") or msg.lower().startswith("who am i"):
            if msg.lower().startswith("i am"):
                msg = msg[len("i am ") :]
                if persist.get(discordname(message.author), None) is None:
                    persist[discordname(message.author)] = {"defines": {}}
                persist[discordname(message.author)][
                    "NossiAccount"
                ] = msg.strip().upper()
                await message.add_reaction("\N{THUMBS UP SIGN}")
            try:
                await send(
                    "You are " + persist[discordname(message.author)]["NossiAccount"]
                )
            except KeyError:
                await send("I have no recollection of you.")
        if not isinstance(message.channel, discord.DMChannel):
            if "BANISH" in msg:
                persist["allowed_rooms"].remove(message.channel.id)
                await send("I will no longer listen here.")
                return
            if "INVOKE" in msg:
                try:
                    persist["allowed_rooms"] = persist["allowed_rooms"] | {
                        message.channel.id
                    }
                except KeyError:
                    persist["allowed_rooms"] = {message.channel.id}
                await send(
                    "I have been invoked and shall do my duties here until BANISHed."
                )
                return

    if message.channel.id not in persist["allowed_rooms"]:
        if isinstance(
            message.channel, discord.TextChannel
        ):  # skip nonallowed textchannels
            return  # all other channels should be ok as long as the bot can read it
    if message.channel not in active_channels:
        active_channels.append(message.channel)
        if isinstance(message.channel, discord.TextChannel):
            print(
                "new channel:", message.channel.name, "on", message.channel.guild.name
            )
    if "\n" in msg:
        for m in msg.split("\n"):
            n = message
            n.content = m
            await on_message(n)
        return

    if msg.startswith("#remind"):
        newreminder(str(message.channel.id), msg[7:])
        await send(str(message))
    msg, comment = msg.rsplit("//", 1) if "//" in msg else (msg, "")
    comment = " " + comment.strip()
    msg = await handle_defines(msg, send, message)
    if not msg:
        return
    if msg.startswith("weapon:") or msg.startswith("magicalweapon:"):
        await weaponhandle(msg, comment, send, message.author)
    elif msg.startswith("specific:"):
        await specifichandle(msg, comment, send, message.author)
    elif msg.startswith("oracle"):
        await oraclehandle(msg, comment, send, message.author)
    else:
        await rollhandle(
            msg,
            comment,
            message,
            persist.get(discordname(message.author), {"defines": {}})["defines"],
        )


if __name__ == "__main__":
    client.run(TOKEN)
    print("Done.")
