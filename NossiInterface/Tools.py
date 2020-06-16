import re
import time

import Data
from NossiPack.Cards import Cards
from NossiPack.DiceParser import fullparenthesis
from NossiPack.User import Config
from NossiPack.krypta import DescriptiveError
from NossiSite.wiki import load_user_char_stats

statcache = {}


def discordname(user):
    return user.name + "#" + user.discriminator


async def split_send(send, lines, i=0):
    replypart = ""
    while i < len(lines):
        while len(replypart) + len(lines[i]) < 1950:
            replypart += lines[i] + "\n"
            i += 1
            if len(lines) <= i:
                break

        if replypart:
            await send("```" + replypart + "```")
            replypart = ""
        elif i < len(lines):
            await send("```" + lines[i][:1990] + "```")
            i += 1
            replypart = ""
        else:
            print("aborting sending: unexpected state", i, lines)
            break


async def cardhandle(msg, message, persist, send):
    def form(inp):

        if isinstance(inp, dict):
            outp = ""
            for k, j in inp.items():
                outp += "\n" + str(k) + ": " + form(j)
            return outp
        elif isinstance(inp, list):
            return ", ".join(inp)
        elif isinstance(inp, str):
            return inp
        else:
            DescriptiveError("HUH?")

    command = msg.split(":")[1]
    par = ":".join(msg.split(":")[2:])
    mention = message.author.mention
    deck = None
    whoami = None
    try:
        whoami = who_am_i(persist)
        if not whoami:
            return await send(mention + " Could not ascertain Identity!")

        deck = Cards.getdeck(whoami)
        if command == "draw":
            await send(mention + " " + form(deck.elongate(deck.draw(par))))
        elif command == "spend":
            deck.spend(par)
            await send(mention + " " + "OK")
        elif command == "return":
            await send(mention + " " + form(deck.elongate(deck.pilereturn(par))))
        elif command == "dedicate":
            deck.dedicate(*par.split(":", 1))
            await send(mention + " " + "OK")
        elif command == "remove":
            deck.remove(par)
            await send(mention + " " + "OK")
        elif command == "undedicate":
            message = deck.undedicate(par)
            await send(
                mention
                + f" Affected Dedication{'s' if len(message)!=1 else ''}: "
                + ("\n".join(message) or "none")
            )
        elif command == "free":
            _, message = deck.free(par)
            await send(
                mention
                + f" Affected Dedication{'s' if len(message)!=1 else ''}: "
                + (",\n and ".join(message) or "none")
            )
        elif command == "help":
            await split_send(message.author.send, Data.getcardhelp().splitlines())
        else:
            infos = deck.renderlong
            if command in infos:
                await send(mention + " " + form(infos[command]))
            else:
                await send(mention + f" invalid command {command}")
    except DescriptiveError as e:
        await send(mention + " " + e.args[0])
    finally:
        if deck and whoami:
            deck.savedeck(whoami, deck)


def fakemessage(message):
    if isinstance(message, str):  # message is name already

        async def error(a):
            raise Exception(a)

        class Fake:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        n, d = message.split("#")
        message = Fake(
            author=Fake(name=n, discriminator=d, send=error), add_reaction=print
        )
        return message


async def define(msg, message, persist):
    author = discordname(message.author)
    msg = msg[3:].strip()
    if "=" in msg:
        question = re.compile(r"^=\s*?")
        if question.match(msg):
            msg = question.sub(msg, "").strip()
            if not msg:
                defstring = "defines are:\n"
                for k, v in persist[author]["defines"].items():
                    defstring += "def " + k + " = " + v + "\n"
                for replypart in [
                    defstring[i : i + 1950] for i in range(0, len(defstring), 1950)
                ]:
                    await message.author.send(replypart)
                return None
        definition, value = [x.strip() for x in msg.split("=", 1)]
        persist[author]["defines"][definition] = value
        persist["mutated"] = True
        await message.add_reaction("\N{THUMBS UP SIGN}")
        return None
    if persist[author]["defines"].get(msg, None) is not None:
        await message.author.send(persist[author]["defines"][msg])
    else:
        await message.add_reaction("\N{THUMBS DOWN SIGN}")
    return None


async def undefine(msg, message, persist):
    author = discordname(message.author)
    msg = msg[6:]
    change = False
    for k in list(persist[author]["defines"].keys()):
        if re.match(msg + r"$", k):
            change = True
            del persist[author]["defines"][k]
    if change:
        persist["mutated"] = True
        await message.add_reaction("\N{THUMBS UP SIGN}")
    else:
        await message.add_reaction("\N{BLACK QUESTION MARK ORNAMENT}")
    return None


def splitpara(msg):
    sections = []
    while msg:
        para = fullparenthesis(msg, "&", "&", include=True)
        parapos = msg.find(para)
        sections += [msg[:parapos], para]
        msg = msg[parapos + len(para) :]
    return sections


async def replacedefines(msg, message, persist):
    oldmsg = ""
    author = discordname(message.author)
    send = message.author.send
    counter = 0
    while oldmsg != msg:
        oldmsg = msg
        counter += 1
        if counter > 100:
            await send(
                "... i think i have some issues with the defines.\n" + msg[:1000]
            )
        sections = splitpara(msg)
        for i in range(len(sections)):
            if "&" not in sections[i]:
                for k, v in persist[author]["defines"].items():
                    pat = r"(^|\b)" + re.escape(k) + r"(\b|$)"
                    sections[i] = re.sub(pat, v, sections[i])
        msg = "".join(sections)
    return msg


def who_am_i(persist):
    whoami = persist.get("NossiAccount", None)
    if whoami is None:
        raise DescriptiveError(f"No NossiAccount linked!")
    checkagainst = Config.load(whoami, "discord")
    da = persist.get("DiscordAccount", None)
    if da is None:  # should have been set up at the same time
        persist["NossiAccount"] = "?"  # force resetup
        raise DescriptiveError(
            f"Whoops, I have forgotten who you are, tell me again please."
        )
    if da == checkagainst:
        return whoami
    raise DescriptiveError(
        f"The NossiAccount {whoami} has not confirmed this discord account!"
    )


async def handle_defines(msg, message, persist):
    """
    processes defines and mutates the message accordingly.
    msg:
        "def a = b" defines a to resolve to b
        "def a" retrieves the definition of a
        "def =?" retrieves all definitions
        "undef <r>" removes all definitions for keys matching the regex
        (` will be stripped, and might be necessary to send through discord)
    :param msg: the message to be processed
    :param message: message object containing author
        (which contains name and send) and add_reaction
    :param persist: dictionary that is intended to persist between calls
    :return: the mutated message or None if message was consumed
    """
    msg = msg.strip("` ")
    author = discordname(message.author)
    try:
        persist[author]["defines"]
    except KeyError:
        persist[author] = {"defines": {}}

    cachetimeout = 0 if msg.startswith("?") else 3600
    pers = persist[author]

    if msg.startswith("def "):
        await define(msg, message, persist)
    elif msg.startswith("undef "):
        await undefine(msg, message, persist)

    defines = {}
    whoami = who_am_i(pers)
    if whoami:
        cache = statcache.get(whoami, [0, {}])
        if time.time() - cache[0] > cachetimeout:
            defines = cache[1]
        if not defines:
            defines = load_user_char_stats(whoami)
            statcache[whoami] = (time.time(), defines)
    defines.update(pers["defines"])  # add in /override explicit defines
    loopconstraint = 100
    used = []
    while loopconstraint > 0:
        loopconstraint -= 1
        for k, v in defines.items():
            if k in msg and k not in used:
                msg = msg.replace(k, v)
                used.append(k)
                break
        else:
            loopconstraint = 0  # no break means no replacements
    return msg


def dict_path(path, d):
    res = []
    for k, v in d.items():
        if isinstance(v, dict):
            res += dict_path(path + "." + k, v)
        else:
            res.append((path + "." + k, v))
    return res
