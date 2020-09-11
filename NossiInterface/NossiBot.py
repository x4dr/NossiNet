import ast
import asyncio
import datetime
import os
import pathlib
import re
import shelve
import time
import traceback
from typing import List
from urllib.parse import quote

import discord
import requests

import Data
from Data import getnossihelp
from NossiInterface.RollInterface import rollhandle, chunk_reply, timeout
from NossiInterface.Tools import (
    discordname,
    split_send,
    handle_defines,
    cardhandle,
    statehandle,
    get_remembering_send,
    delete_replies,
)
from NossiInterface.reminder import reminders, newreminder, delreminder, listreminder
from NossiPack.fengraph import chances, montecarlo, versus
from NossiPack.krypta import DescriptiveError

client = discord.Client()
bufferfile = "NossiBotBuffer"
shutdownflag = pathlib.Path("shutdown_nossibot")
if shutdownflag.exists():
    shutdownflag.unlink()  # ignore previously set shutdown
ticking = [0]
disconnecting = []
channels = {}
people = {}
print("initializing NossiBot...")


class MutationLoggingDict(dict):
    def __setitem__(self, key, value):
        dict.__setitem__(self, "mutated", True)
        dict.__setitem__(self, key, value)


storagefile = "~/NossiBot.storage"

nossiUrl = "http://127.0.0.1:5000/"

persist = MutationLoggingDict()
with shelve.open(os.path.expanduser(storagefile)) as shelvefile:
    for shelvekey in shelvefile.keys():
        persist[shelvekey] = shelvefile[shelvekey]  # copy everything out
    persist["mutated"] = False
now = datetime.datetime.now

with open(os.path.expanduser("~/token.discord"), "r") as tokenfile:
    TOKEN = tokenfile.read().strip()

active_channels = []


async def oraclehandle(msg, comment, send, author):
    msg = msg[6:].strip()
    errreport = msg.startswith("?")
    if errreport:
        msg = msg[1:].strip()
    sentmessage = None
    mode = None
    if msg.endswith(" under") or msg.endswith(" asc") or msg.endswith(" below"):
        mode = 1
        msg = msg[:-4]
    if msg.endswith(" over") or msg.endswith(" desc") or msg.endswith(" above"):
        mode = -1
        msg = msg[:-5]
    if msg.startswith("show"):
        try:
            parameters = msg[5:].split(" ")
            it = chances(parameters[:-2], parameters[-2], parameters[-1], mode=mode)
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
            await send(
                author.mention
                + " <selectors> <modifier> <number of quantiles> [above|asc|over|below|desc|under]"
            )
    elif msg.startswith("try"):
        sentmessage = await send("Applying the numerical HAMMER for 10 seconds...")
        r = await timeout(montecarlo, msg[3:], 12)
        await sentmessage.edit(content=author.mention + "\n" + str(r)[:1950])

    else:
        try:
            if " v " in msg:
                a, b = msg.split("v", 1)
                a = [x.strip() for x in a.lower().split(" ") if x.strip()]
                b = [x.strip() for x in b.lower().split(" ") if x.strip()]
                if len(a) == len(b) == 3:
                    it = versus(a, b, mode)
                else:
                    await send(
                        author.mention
                        + "versus mode needs exactly 3 numbers on each side"
                    )
                    return
                p = (
                    ",".join(str(x) for x in a[:-1])
                    + "@5"
                    + ("R" + str(a[-1]))
                    + " v "
                    + ",".join(str(x) for x in a[:-1])
                    + "@5"
                    + ("R" + str(a[-1]))
                )

            else:
                parameters = [x.strip() for x in msg.lower().split(" ") if x.strip()]
                it = chances(parameters[:-1], parameters[-1], mode=mode)
                p = (
                    ",".join(str(x) for x in parameters[:-1])
                    + "@5"
                    + (("R" + str(parameters[-1])) if parameters[-1] else "")
                )
            sentmessage = await send("received")
            n = []
            for i in it:
                n.append(i)
                if isinstance(i, str):
                    await sentmessage.edit(content=author.mention + comment + " " + i)
            if n:
                n, avg, dev = n[-1]
                print(n)
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
            await send(author.mention + " <selectors> <modifier> [asc|desc]")
            raise


async def weaponhandle(msg, comment, send, author, react):
    n = requests.get(
        nossiUrl + "/".join(quote(x.strip()) for x in msg.split(":", 2)) + "/txt"
    )
    if n.status_code == 200:
        n = n.content.decode("utf-8")
        if len(n) > 1950:
            await chunk_reply(author.send, n)
        else:
            await chunk_reply(
                send, author.mention + comment + "```" + msg + "\n" + n + "```"
            )
    else:
        await react("😕")
        print("failed request:", n.status_code, n.url)


async def specifichandle(msg, comment, send, author):
    msg = msg[len("specific:") :].strip()
    n = requests.get(nossiUrl + "specific/" + quote(msg.strip()) + "/raw")
    if n.status_code == 200:
        n = n.content.decode("utf-8")
        await send(author.mention + comment + "```" + msg + "\n" + n[:1950] + "```")
        for replypart in [n[i : i + 1950] for i in range(1950, len(n), 1950)]:
            await send("```" + replypart + "```")
        return True
    print("failed request:", n.status_code, n.url)
    return False


def savepersist():
    try:
        if persist["mutated"]:
            with shelve.open(os.path.expanduser(storagefile)) as shelvingfile:
                for k in persist:
                    if k == "mutated":
                        continue  # mutated will never be saved!
                    shelvingfile[k] = persist[k]
                persist["mutated"] = False
        Data.set("channels", str(channels))
        Data.set("people", str(people))
    except Exception as e:
        print(
            f"Exception in savepersist with key {k}:", e, e.args, traceback.format_exc()
        )


async def tick():
    if ticking and time.time() - ticking[0] <= 10:
        print("attempted to doubletick")
        return
    next_call = time.time()
    while True:
        try:
            ticking[0] = time.time()
            while disconnecting:
                await disconnecting.pop().disconnect()
            try:
                nexttime = await reminders(client.get_channel)
            except Exception as e:
                print("Exception reminding:", e, e.args, traceback.format_exc())
                nexttime = 10
            savepersist()
            next_call += nexttime
            if client.is_closed():
                print("loop died of dead client")
                break
            info = await client.application_info()
            if shutdownflag.exists():
                shutdownflag.unlink()
                await info.owner.send("I got Killed")
                await client.close()
            await asyncio.sleep(next_call - time.time(),)
        except Exception as e:
            print(f"Encountered exception in tick loop: {e} {e.args}")


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
    await info.owner.send("I Live... last 10 timings:" + str(ticking))
    persist["owner"] = discordname(info.owner)
    channels.update(ast.literal_eval(Data.get("channels")))
    people.update(ast.literal_eval(Data.get("people")))


@client.event
async def on_disconnect():
    print(
        "Disconnected, accessibility of google:",
        requests.get("http://www.google.com").status_code,
    )


@client.event
async def on_resume():
    print("Resumed...")
    info = await client.application_info()
    await info.owner.send("I have Resumed")


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
async def on_message_delete(message: discord.Message):
    await delete_replies(message)


@client.event
async def on_message(message: discord.Message):
    persist["mutated"] = True
    msg: str = message.content.strip("` ")
    send = get_remembering_send(message)
    author: discord.member.Member = message.author
    people[message.author.mention] = discordname(message.author)
    if message.author == client.user:
        return
    if msg.startswith("NossiBot") or isinstance(message.channel, discord.DMChannel):
        channels[message.channel.id] = discordname(message.author)
        msg = msg[len("NossiBot") :] if msg.startswith("NossiBot") else msg
        if msg.strip() == "help":
            await split_send(message.author.send, getnossihelp().splitlines())
            return
        if "DIE" in msg and discordname(message.author) == persist["owner"]:
            await message.add_reaction("\U0001f480")
            await send("I shall die.")
            await client.close()
            return
        if "JOIN ME" in msg.upper() and discordname(message.author) == persist["owner"]:
            vc: discord.VoiceChannel = author.voice.channel
            connection = await vc.connect()
            connection.play(
                # discord.FFmpegOpusAudio("default", before_options="-f pulse"),
                # contents of pacatffmpeg
                # #!/bin/bash
                # pacat -r -d alsa_output.pci-0000_00_1b.0.analog-stereo.monitor \
                # --format=s32le --rate=48000 > ~/soundpipe
                discord.FFmpegPCMAudio(
                    pathlib.Path("~/soundpipe").expanduser(),
                    before_options="-f s32le -ac 2 -ar 48000",
                ),
                after=lambda e: disconnecting.append(connection),
            )

        if "LEAVE" in msg.upper():
            vcs: List[discord.VoiceClient] = client.voice_clients
            for x in vcs:
                if author.voice.channel == x.channel:
                    await x.disconnect()
                    break
            await message.add_reaction("🔇")

            return
        if msg.lower().startswith("i am ") or msg.lower().startswith("who am i"):
            if msg.lower().startswith("i am"):
                msg = msg[len("i am ") :]
                if persist.get(discordname(message.author), None) is None:
                    persist[discordname(message.author)] = {"defines": {}}
                persist[discordname(message.author)][
                    "NossiAccount"
                ] = msg.strip().upper()
                persist[discordname(message.author)]["DiscordAccount"] = discordname(
                    message.author
                )
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
    else:
        channels[message.channel.id] = message.channel.name

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
    if msg.startswith("remind"):
        if msg.strip() == "remind del":
            await delreminder(message)
        elif msg.strip() == "remind list":
            await listreminder(message, mentionreplacer())
        else:
            newdate = newreminder(message, msg[7:])
            return await send("will remind on " + newdate.isoformat())
    msg, comment = msg.rsplit("//", 1) if "//" in msg else (msg, "")
    comment = " " + comment.strip("` ")
    msg = await handle_defines(msg, message, persist)
    if not msg:
        savepersist()
        return
    if msg.startswith("weapon:") or msg.startswith("magicalweapon:"):
        await weaponhandle(msg, comment, send, message.author, message.add_reaction)
    elif msg.startswith("specific:"):
        await specifichandle(msg, comment, send, message.author)
    elif msg.startswith("oracle"):
        await oraclehandle(msg, comment, send, message.author)
    elif msg.startswith("cards:"):
        await cardhandle(msg, message, persist[discordname(message.author)], send)
    elif msg.startswith("state:"):
        await statehandle(msg, message, persist[discordname(message.author)], send)

    else:
        await rollhandle(
            msg, comment, author, send, message.add_reaction, persist,
        )


def mentionreplacer():
    def replace(m: re.Match):
        u: discord.User = client.get_user(int(m.group(1)))
        print(u.name)
        return "@" + u.name

    return replace


if __name__ == "__main__":
    client.run(TOKEN)
    print("Done.")
