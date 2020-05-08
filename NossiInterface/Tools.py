import re
import time

from NossiPack.WoDParser import fullparenthesis
from NossiSite.wiki import load_user_char

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
    whoami = pers.get("NossiAccount", None)
    if whoami:
        cache = statcache.get(whoami, [0, {}])
        if time.time() - cache[0] > cachetimeout:
            defines = cache[1]
        if not defines:
            defines = load_user_char(whoami)
            statcache[whoami] = (time.time(), defines)
    defines.update(pers["defines"])  # add in /override explicit defines
    loopconstraint = 100
    while loopconstraint > 0:
        loopconstraint -= 1
        for k, v in defines.items():
            if k in msg:
                msg = msg.replace(k, v)
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
