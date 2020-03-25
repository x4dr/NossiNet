import asyncio
import time
from concurrent.futures.thread import ThreadPoolExecutor

import discord

from NossiInterface.Tools import discordname, load_fen_char
from NossiPack.WoDDice import WoDDice
from NossiPack.WoDParser import WoDParser, DiceCodeError
from NossiPack.krypta import terminate_thread

numemoji = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
numemoji_2 = ("❗", "‼️", "\U0001F386")

lastroll = {}
statcache = {}


def prepare(msg: str, author, persist, comment):
    errreport = msg.startswith("?")
    cachetimeout = 3600
    if errreport:
        cachetimeout = 0
        msg = msg[1:]
    msg = msg.strip()
    if all(x == "+" for x in msg):
        which = msg.count("+")
        msgs = lastroll.get(author, [])
        msg = msgs[-min(which, len(msgs))]
        print("repl", msg, msgs, which)
    else:
        print(msg, comment, lastroll)
        lastroll[author] = (
            lastroll.get(author, []) + [msg + (("//" + comment) if comment else "")]
        )[-10:]

    pers = persist.get(discordname(author), {"defines": {}})
    defines = {}
    whoami = pers.get("NossiAccount", None)
    if whoami:
        cache = statcache.get(whoami, [0, {}])
        if time.time() - cache[0] > cachetimeout:
            defines = cache[1]
        if not defines:
            defines = load_fen_char(whoami)
            statcache[whoami] = (time.time(), defines)
    defines.update(pers["defines"])  # add in /override explicit defines
    p = WoDParser(defines)
    return msg, p, errreport


def get_verbosity(verbose):
    if verbose:

        def v(self):
            return self.roll_vv(verbose)

        verbose = v
    else:
        verbose = WoDDice.roll_v
    return verbose


def construct_multiroll_reply(p: WoDParser, verbose):
    v = get_verbosity(verbose)
    return "\n".join(x.name + ": " + v(x) for x in p.rolllogs if v(x)) + "\n"


def construct_shortened_multiroll_reply(p: WoDParser, verbose):
    last = ""
    reply = ""
    v = get_verbosity(verbose)
    for x in p.rolllogs:
        if not x.roll_v():
            continue  # skip empty rolls
        if x.name != last:
            last = x.name
            reply += "\n" + ((x.name + ": ") if verbose else "") + v(x)
        else:
            reply += ", " + str(x.result)
    return reply.strip("\n") + "\n"


async def get_reply(author, comment, msg, send, reply, r):
    tosend = (
        author.mention
        + f"{comment} `{msg}`:\n{reply} "
        + (r.roll_v() if not reply.endswith(r.roll_v() + "\n") else "")
    )
    # if message is too long we need a second pass
    if len(tosend) > 2000:
        tosend = (
            f"{author.mention} {comment} `{msg}`:\n"
            f"{reply[: max(4000 - len(tosend), 0)]} [...]"
            f"{r.roll_v()}"
        )
    # if message is still too long
    if len(tosend) > 2000:
        tosend = (
            f"{author.mention} {comment} `{msg}`:\n"
            + r.name
            + ": ... try generating less output"
        )
    sent = await send(tosend)
    if r.returnfun.endswith("@") and r.result >= r.max * len(
        r.returnfun[:-1].split(",")
    ):
        await sent.add_reaction("\U0001f4a5")
    if r.max == 10 and (r.returnfun.endswith("@") or r.amount == 5):
        for frequency in range(1, 11):
            amplitude = r.resonance(frequency)
            if amplitude > 0:
                await sent.add_reaction(numemoji[frequency - 1])
            if amplitude > 1 and len(r.r) == 5:
                await sent.add_reaction(numemoji_2[amplitude - 2])


async def process_roll(r: WoDDice, p: WoDParser, msg: str, comment, send, author):
    verbose = p.triggers.get("verbose", None)

    if isinstance(p.rolllogs, list) and len(p.rolllogs) > 1:
        reply = construct_multiroll_reply(p, verbose)

        if len(reply) > 1950:
            reply = construct_shortened_multiroll_reply(p, verbose)
    else:
        reply = ""

    tosend = "uninitialized"
    try:
        await get_reply(author, comment, msg, send, reply, r)
    except Exception as e:

        raise Exception(
            f"Exception during sending: {str(e)}\n"
            f"length:{len(tosend)} \nfirst 100 {tosend[:100]}"
        )


async def timeout(func, arg, time_out=1):
    loop = asyncio.get_event_loop()
    ex = ThreadPoolExecutor(max_workers=1)
    try:
        return await asyncio.wait_for(loop.run_in_executor(ex, func, arg), time_out)
    except asyncio.exceptions.TimeoutError:
        # noinspection PyUnresolvedReferences,PyProtectedMember
        # skipcq: PYL-W0212
        for t in ex._threads:  # Quite impolite form of killing that thread,
            # but otherwise it keeps running
            terminate_thread(t)
            print(f"terminated: {arg}")
        raise


async def rollhandle(msg, comment, message: discord.Message, persist):
    author = message.author
    comment = comment.strip()
    msg, p, errreport = prepare(msg, author, persist, comment)
    try:
        r = await timeout(p.do_roll, msg, 2)
        await process_roll(r, p, msg, comment, message.channel.send, author)
    except DiceCodeError as e:
        if errreport:  # query for error
            await author.send("Invalid Dicecode:" + "\n".join(e.args)[:2000])
    except asyncio.exceptions.TimeoutError:
        await message.add_reaction("\U000023F0")
    except Exception as e:
        print(type(e), e)
        ermsg = f"big oof during rolling {msg}" + "\n" + "\n".join(e.args)
        if errreport:  # query for error
            await author.send(ermsg[:2000])
        else:
            await message.add_reaction("😕")
        print(ermsg)
