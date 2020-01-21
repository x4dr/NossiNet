import asyncio
import datetime
import os
import string
import time

import requests

import fengraph
import discord
import random
import traceback
from dateparser import parse as dateparse

from NossiPack import WoDParser

remindfile = os.path.expanduser("~/reminders.txt")
remindnext = os.path.expanduser("~/reminers_next.txt")
now = datetime.datetime.now

TOKEN = open(os.path.expanduser("~/token.discord"), "r").read().strip()

description = '''NossiBot in Python'''
print("selftest 1-100:", WoDParser({}).make_roll("1d100").roll_v())
client = discord.Client()
repeats = {}
lastroll = {}
active_channels = []


async def reminders(clearjob=None):
    global repeats
    jobs = []
    nextevent = 600
    with open(remindfile, "r") as f:
        for l in f.readlines():
            print(l)
            channelid, jobid, date, message, repeat, interval = [p.strip() for p in l.split(";")]
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
                        status = "" if int(repeat.split(" ")[1]) < 2 else str(repeats[jobid]) + "/" + repeat.split(" ")[
                            1]
                        await client.get_channel(int(channelid)).send(message + " " + status + jobid)
                        nextevent = (reminddate + delay - time.time())
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
                jobs.append(";".join([channelid, jobid, str(round(date)), message, repeat, str(interval)]))
            else:
                print("job", jobid, "deleted")
    with open(remindnext, "w") as f:
        f.write("\n".join(jobs))
    os.replace(remindnext, remindfile)


def newreminder(channelid, message):
    jobid = ''.join([random.choice(string.ascii_letters).lower() for _ in range(4)])
    print(message)
    date, message, repeat, interval = [x.strip() for x in (message.split(";") + ["", ""])[:4]]
    date = datetime.datetime.timestamp(dateparse(date))
    #    print("trying to figure out what this is:",repeat,  repeat.split(" ")[0],dateparse(repeat.split(" ")[0]))
    repeat = str(round(abs(dateparse(repeat.split(" ")[0]) -
                           datetime.datetime.now()).total_seconds())) + " " + repeat.split(" ")[1]
    interval = str(round(abs(dateparse(interval) - datetime.datetime.now()).total_seconds()))
    newline = ";".join([channelid, jobid, str(round(date)), message, repeat, interval]) + "\n"
    print("new line:", newline)
    with open(remindfile, "a") as f:
        f.write(newline)


async def tick():
    next_call = time.time()
    while True:
        try:
            await reminders()
        except Exception as e:
            print("Exception reminding:", e, e.args, traceback.format_exc())
        next_call += 10
        await asyncio.sleep(next_call - time.time())


@client.event
async def on_ready():
    print('Logged in as')
    print("Name:", client.user.name)
    print("ID:", client.user.id)
    print('------')
    asyncio.create_task(tick())
    p = discord.Permissions(117824)
    print(discord.utils.oauth_url(client.user.id, p))


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    message = None
    for ch in active_channels:
        try:
            message = await ch.fetch_message(payload.message_id)
        except:
            pass
    if message is not None:
        await on_message(message)


@client.event
async def on_message(message):
    msg = message.content
    send = message.channel.send
    if message.author == client.user:
        return
    if str(message.channel) not in ["würfel", "dice", "remind", "dice-rolls"]:
        return
    if message.channel not in active_channels:
        active_channels.append(message.channel)
        print("new channel:", message.channel.name, "on", message.channel.guild.name)
    #    if "dump" in message.content :
    #        await send(str(message)+ str(message.channel))
    sentmessage = None
    if "\n" in msg:
        for m in msg.split("\n"):
            n = message
            n.content = m
            await on_message(n)
        return

    if msg.startswith("#remind"):
        newreminder(str(message.channel.id), msg[7:])
        await send(str(message))
    msg, comment = msg.split("//", 1) if "//" in msg else (msg, "")
    comment = (" " + comment.strip())
    if msg.startswith("weapon:"):
        n = requests.get("http://nosferatu.vampir.es/" + "/".join(msg.split(":")) + "/txt")
        if n.status_code == 200:
            n = n.content.decode("utf-8")
            await send(message.author.mention + comment + "```" + msg + "\n" + n + "```")
        else:
            return

    if msg.startswith("oracle"):
        if msg.startswith("oracle show"):
            try:
                parameters = msg[12:].split(" ")
                it = fengraph.chances(parameters[:-2], parameters[-2], parameters[-1])
                sentmessage = await send(message.author.mention + comment + " " + next(it))
                for n in it:
                    if isinstance(n, str):
                        await sentmessage.edit(content=message.author.mention + comment + " " + n)
                    else:
                        await sentmessage.delete(delay=0.1)
                        await send(message.author.mention + comment, file=discord.File(n, 'graph.png'))
            except Exception as e:
                print("exception during oracle show", e)
                if sentmessage:
                    await sentmessage.edit(content=message.author.mention + " ERROR")
                    await sentmessage.delete(delay=3)
                await send(message.author.mention + " <selectors> <modifier> <number of quantiles>")
        else:
            try:
                parameters = msg[7:].split(" ")
                it = fengraph.chances(parameters[:-1], parameters[-1])
                sentmessage = await send(message.author.mention + comment + " " + next(it))
                n = ""
                for n in it:
                    print("iterating:", n)
                    await sentmessage.edit(content=message.author.mention + comment + " " + n)
                if n:
                    await sentmessage.edit(content=message.author.mention + comment + "```" + n + "```")
                else:
                    raise Exception("no values past the first")
            except Exception as e:
                print("exception during oracle", e)
                if sentmessage:
                    await sentmessage.edit(content=message.author.mention + " ERROR")
                    await sentmessage.delete(delay=3)
                await send(message.author.mention + " <selectors> <modifier>")
    else:
        msg = msg.strip()
        if msg == "+":
            msg = lastroll.get(message.author, "")
        if msg.endswith("v"):
            msg = msg[:-1] + " &verbose&"
        p = WoDParser({})
        try:
            r = p.make_roll(msg)
        except Exception as e:
            return " ".join(e.args)
        lastroll[message.author] = msg
        if isinstance(p.altrolls, list) and len(p.altrolls) > 0:
            await send(message.author.mention + comment + " " + msg + ":\n" +
                       "\n".join(x.name + ": " + x.roll_v() for x in p.altrolls))
        if p.triggers.get("verbose", None):
            await send(message.author.mention + comment + " " + msg + ":\n" +
                       r.name + ": " + r.roll_vv(p.triggers.get("verbose")))
        else:
            try:
                await send(message.author.mention + comment + " " + msg + ":\n" + r.roll_v())
            except:
                print("big oof during rolling ", r, msg)


# discord.on_message_edit(before, after)

client.run(TOKEN)
