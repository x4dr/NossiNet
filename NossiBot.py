import asyncio
import datetime
import os
import string
import time
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


@client.event
async def on_message(message):
    msg = message.content
    send = message.channel.send
    if message.author == client.user:
        return
    if str(message.channel) not in ["würfel", "dice"]:
        return

    #    if "dump" in message.content :
    #        await send(str(message)+ str(message.channel))
    sentmessage = None
    if msg.startswith("#remind"):
        newreminder(str(message.channel.id), msg[7:])
        await send(str(message))
    elif msg.startswith("oracle"):
        if msg.startswith("oracle show"):
            try:
                parameters = msg[12:].split(" ")
                it = fengraph.chances(parameters[:-2], parameters[-2], parameters[-1])
                sentmessage = await send(message.author.mention + " " + next(it))
                for n in it:
                    if isinstance(n, str):
                        await sentmessage.edit(content=message.author.mention + " " + n)
                    else:
                        await sentmessage.delete(delay=0.1)
                        await send(message.author.mention, file=discord.File(n, 'graph.png'))
            except Exception as e:
                print(e)
                if sentmessage:
                    await sentmessage.edit(content=message.author.mention + " ERROR")
                    await sentmessage.delete(delay=3)
                raise
                await send(message.author.mention + " <selectors> <modifier> <number of quantiles>")
        else:
            try:
                parameters = msg[7:].split(" ")
                it = fengraph.chances(parameters[:-1], parameters[-1])
                sentmessage = await send(message.author.mention + " " + next(it))
                n = ""
                for n in it:
                    print(n)
                    await sentmessage.edit(content=message.author.mention + " " + n)
                if n:
                    await sentmessage.edit(content=message.author.mention + "```" + n + "```")
                else:
                    raise Exception("no values past the first")
            except Exception as e:
                print(e)
                if sentmessage:
                    await sentmessage.edit(content=message.author.mention + " ERROR")
                    await sentmessage.delete(delay=3)
                raise
                await send(message.author.mention + " <selectors> <modifier>")
    else:
        msg = msg.strip()
        if msg.endswith("v"):
            msg = msg[:-1] + " &verbose&"
        p = WoDParser({})
        r = p.make_roll(msg)
        if isinstance(p.altrolls, list) and len(p.altrolls) > 0:
            await send(message.author.mention + " " + msg + ":\n" +
                       "\n".join(x.name + ": " + x.roll_v() for x in p.altrolls))
        if p.triggers.get("verbose", None):
            await send(message.author.mention + " " + msg + ":\n" +
                       r.name + ": " + r.roll_vv(p.triggers.get("verbose")))
        else:
            await send(message.author.mention + " " + msg + ":\n" + r.roll_v())


# discord.on_message_edit(before, after)

client.run(TOKEN)
