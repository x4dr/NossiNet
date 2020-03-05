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
from urllib.parse import quote

import discord
import requests
from dateparser import parse as dateparse

from NossiPack import WoDParser, fengraph
from NossiPack.krypta import DescriptiveError, read_nonblocking

bufferfile = "NossiBotBuffer"
shutdownflag = pathlib.Path("shutdown_nossibot")
if shutdownflag.exists():
    shutdownflag.unlink()  # ignore previously set shutdown
remindfile = os.path.expanduser("~/reminders.txt")
remindnext = os.path.expanduser("~/reminders_next.txt")
numemoji = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
numemoji_2 = ("❗", "‼️", "\U0001F386")


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
client = discord.Client()
repeats = {}
lastroll = {}
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
            it = fengraph.chances(parameters[:-2], parameters[-2], parameters[-1])
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
            it = fengraph.chances(parameters[:-1], parameters[-1])
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


async def rollhandle(msg, comment, send, author):
    errreport = msg.startswith("?")
    if errreport:
        msg = msg[1:]
    msg = msg.strip()

    if msg == "+":
        msg = lastroll.get(author, "")
    p = WoDParser(persist.get(discordname(author), {"defines": {}}))
    try:
        r = p.do_roll(msg)
    except Exception as e:
        if errreport:  # query for error
            await author.send(" ".join(e.args))
        return
    lastroll[author] = msg
    reply = ""
    if isinstance(p.rolllogs, list) and len(p.rolllogs) > 1:
        reply += (
            "\n".join(x.name + ": " + x.roll_v() for x in p.rolllogs if x.roll_v())
            + "\n"
        )

    if len(reply) > 1950:
        last = ""
        reply = ""
        for x in p.rolllogs:
            if not x.roll_v():
                continue  # skip empty rolls
            if x.name != last:
                last = x.name
                reply += "\n" + x.name + ": " + x.roll_v()
            else:
                reply += ", " + str(x.result)
        reply = reply.strip("\n") + "\n"
    if p.triggers.get("verbose", None):
        if r is None:
            print(msg, "lead to noneroll!")
        await send(
            author.mention
            + comment
            + " "
            + msg
            + ":\n"
            + r.name
            + ": "
            + r.roll_vv(p.triggers.get("verbose"))
        )
    else:
        tosend = "uninitialized"
        try:
            tosend = (
                author.mention
                + comment
                + " "
                + msg
                + ":\n"
                + reply
                + (r.roll_v() if not reply.endswith(r.roll_v() + "\n") else "")
            )
            if len(tosend) > 2000:
                tosend = (
                    f"{author.mention}"
                    f"{comment} "
                    f"{msg}:\n"
                    f"{reply[: max(4000 - len(tosend), 0)]} [...]"
                    f"{r.roll_v()}"
                )
            if len(tosend) > 2000:
                tosend = (
                    author.mention + comment + " " + msg + ":\n" + r.name + ": [...]"
                )
                tosend += r.roll_v()[-(2000 - len(tosend)) :]
            sent = await send(tosend)
            if r.selectors and r.result >= r.max * len(r.selectors):
                await sent.add_reaction("\U0001f4a5")
            if r.max == 10 and (r.selectors or r.amount == 5):
                for frequency in range(1, 11):
                    amplitude = r.resonance(frequency)
                    if amplitude > 0:
                        await sent.add_reaction(numemoji[frequency - 1])
                    if amplitude > 1 and len(r.r) == 5:
                        await sent.add_reaction(numemoji_2[amplitude - 2])

        except Exception as e:
            problem = str(e)
            ermsg = (
                f"big oof during rolling {problem}\n"
                f"length:{len(tosend)} \n "
                f"first 100 {tosend[:100]}"
            )
            if errreport:  # query for error
                await author.send(ermsg[:2000])
            print(ermsg)


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
            pass

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
    if msg.startswith("def") and "=" in msg:
        msg = msg[3:].strip()
        q = re.compile(r"^=\s*?")
        if q.match(msg):
            msg = q.sub(msg, "").strip()
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
    elif msg.startswith("undef "):
        msg = msg[6:]
        change = False
        for k in list(defines.keys()):
            if re.match(msg + r"$", k):
                change = True
                del defines[k]
        if change:
            persist[author][defines] = defines
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


def discordname(user):
    return user.name + "#" + user.discriminator


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
            await client.close()
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
            with open("nossibot_help.txt") as f:
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
        await rollhandle(msg, comment, send, message.author)


client.run(TOKEN)
print("Done.")
