import re
import time

from discord import Message

import Data
from NossiPack.Cards import Cards
from NossiPack.DiceParser import fullparenthesis
from NossiPack.User import Config
from NossiPack.krypta import DescriptiveError
from NossiSite.wiki import load_user_char_stats, load_user_char, spells, transitions

statcache = {}
sent_messages = {}


def discordname(user):
    return user.name + "#" + user.discriminator


async def delete_replies(message: Message):
    r: Message
    if message.id in sent_messages:
        for r in sent_messages[message.id]["replies"]:
            await r.delete()
        del sent_messages[message.id]


def get_remembering_send(message: Message):
    async def send_and_save(msg):
        sent = await message.channel.send(msg)
        sent_messages[message.id] = sent_messages.get(
            message.id, {"received": time.time(), "replies": []}
        )
        sent_messages[message.id]["replies"].append(sent)
        sent_messages[message.id]["received"] = time.time()
        byage = sorted(
            [(m["received"], k) for k, m in sent_messages.items()], key=lambda x: x[0]
        )
        for m, k in byage[100:]:
            del sent_messages[k]  # remove references for the oldes ones
        return sent

    return send_and_save


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
            await message.add_reaction("\N{THUMBS UP SIGN}")
        elif command == "return":
            await send(mention + " " + form(deck.elongate(deck.pilereturn(par))))
        elif command == "dedicate":
            deck.dedicate(*par.split(":", 1))
            await message.add_reaction("\N{THUMBS UP SIGN}")
        elif command == "remove":
            deck.remove(par)
            await message.add_reaction("\N{THUMBS UP SIGN}")
        elif command == "undedicate":
            message = deck.undedicate(par)
            await send(
                mention
                + f" Affected Dedication{'s' if len(message) != 1 else ''}: "
                + ("\n".join(message) or "none")
            )
        elif command == "free":
            _, message = deck.free(par)
            await send(
                mention
                + f" Affected Dedication{'s' if len(message) != 1 else ''}: "
                + (",\n and ".join(message) or "none")
            )
        elif command == "help":
            await split_send(message.author.send, Data.getcardhelp().splitlines())
        elif command == "spells":
            await spellhandle(deck, whoami, par, send)
        else:
            infos = deck.renderlong
            if command in infos:
                await send(mention + " " + form(infos[command]))
            else:
                await send(mention + f" invalid command {command}")
    except DescriptiveError as e:
        await send(mention + " " + str(e.args[0]))
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


async def spellhandle(deck: Cards, whoami, par, send):
    spellbook = {}
    existing = {}
    power = deck.scorehand()
    spelltexts = load_user_char(whoami).Meta.get("Zauber", ("", {}))[1]
    if not spelltexts:
        await send("No spells found")
    for spelltext in spelltexts.values():
        matches = re.findall(r"specific:(.*?):([^-]*?)(:-)?]", spelltext[0], flags=re.I)
        for m in matches:
            school = m[0]
            spell = m[1].split(":")[-1]
            spellbook[school] = spellbook.get(school, spells(school))
            existing[school + ":" + spell] = spellbook[school].get(
                spell.lower(), {"Name": spell, "Error": "?"}
            )

    if par == "all":
        res = "All Spells:\n"
        for spec, spelldict in existing.items():
            if not spelldict.get("Name", None):
                continue
            sr = ", ".join(
                [
                    f"{v} {k}".strip()
                    for k, v in spelldict.get("Effektive Kosten", {}).items()
                ]
            )
            res += f"specific:{str(spec)+':-': <45}  {sr}\n"
        await split_send(send, res.splitlines())
    elif par == "":
        res = "Available Spells:\n"
        for spec, spelldict in existing.items():
            if not spelldict.get("Name", None):
                continue
            spelltime = spelldict.get("Zauberzeit", "0").strip()
            if "Runde" in spelltime or spelltime == "0":
                if satisfy(power, spelldict.get("Effektive Kosten")):
                    sr = ", ".join(
                        [
                            (str(v) + " " + k).strip()
                            for k, v in spelldict.get("Effektive Kosten", {}).items()
                        ]
                    )
                    res += (
                        f"{spelldict['Name']: <25} "
                        f"{sr: >25} "
                        f"\n(specific:{spec}:-)\n"
                    )
        await split_send(send, res.splitlines())
    else:
        await send(f"unknown spell command: '{par}'")


def satisfy(source, reqs):
    if not reqs:
        return True
    for req, val in reqs.items():
        if not req:
            if sum(source.values()) < val:
                return False
        elif source.get(req.lower(), 0) < val:
            return False

    else:
        return True


def available_transitions():
    pass


async def statehandle(msg, message, persist, send):
    curstate = None
    mention = message.author.mention
    whoami = None
    msg = msg[6:] if msg.startswith("state:") else msg  # remove state:
    msg = [x.strip() for x in msg.lower().split(":")]
    if not msg or not msg[0]:
        return await message.add_reaction("😕")
    try:
        whoami = who_am_i(persist)
        curstate = Config.load(whoami, "state_" + msg[0]) or ""
        if len(msg) == 1:
            return await send(mention + " " + curstate or "None")
        selection = [
            v for k, v in transitions(msg[0], curstate).items() if msg[1] in k.lower()
        ]
        if len(selection) > 1:
            return await send(
                mention
                + f" Ambiguous command \"{msg[1]}\" between {', '.join(x.title() for x in selection)}"
            )
        if len(selection) == 0:
            return await send(
                mention
                + f' No transition for "{msg[1]}" in state "{curstate}", available are: ```'
                + "\n".join(
                    [
                        k.title() + " => " + v[1].title()
                        for k, v in transitions(msg[0], curstate).items()
                    ]
                )
                + "```"
            )
        curstate = selection[0][1]
        return await send(mention + f" => {curstate.title()}")
    except DescriptiveError as e:
        await send(mention + " " + str(e.args[0]))
    finally:
        if curstate is not None and whoami:
            Config.save(whoami, "state_" + msg[0], curstate)


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
        return None
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
        print("User", author, "not found, regenerating")
        persist[author] = {"defines": {}}

    cachetimeout = 0 if msg.startswith("?") else 3600
    pers = persist[author]

    if msg.startswith("def "):
        await define(msg, message, persist)
        return ""
    elif msg.startswith("undef "):
        await undefine(msg, message, persist)
        return ""

    defines = {}
    try:
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
    except DescriptiveError as e:
        await message.author.send(e.args[0])
    return msg


def dict_path(path, d):
    res = []
    for k, v in d.items():
        if isinstance(v, dict):
            res += dict_path(path + "." + k, v)
        else:
            res.append((path + "." + k, v))
    return res
