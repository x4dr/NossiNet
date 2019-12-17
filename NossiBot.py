import asyncio
import datetime
import os
import string
import time

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
        print("debug:", time.time())
        try:
            await reminders()
        except Exception as e:
            print("Exceptionreminding:", e, e.args, traceback.format_exc())
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
    if msg.startswith("#remind"):
        newreminder(str(message.channel.id), msg[7:])
        await send(str(message))
    else:
        p = WoDParser({})
        r = p.make_roll(msg)
        if p.triggers.get("verbose", None):
            await send(message.author.mention + " " + msg + ":\n" + r.roll_vv())
        else:
            await send(message.author.mention + " " + msg + ":\n" + r.roll_v())


# discord.on_message_edit(before, after)

client.run(TOKEN)
