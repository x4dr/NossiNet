import os
import time
from logging import warning

import discord
import requests
from discord.ext import commands
from discord.ext.commands import Context

from NossiInterface.Cogs.NossiCog import NossiCog
from NossiInterface.Tools import (
    get_remembering_send,
    delete_replies,
    handle_defines,
)

# Change only the no_category default string
help_command = commands.DefaultHelpCommand(no_category="Commands")

# Create the bot and pass it the modified help_command
client = commands.Bot(
    command_prefix="",
    description="NossiBot",
    help_command=help_command,
)

with open(os.path.expanduser("~/token.discord"), "r") as tokenfile:
    TOKEN = tokenfile.read().strip()

print("initializing NossiBot...")

client.nossiUrl = "http://127.0.0.1:5000/"


@commands.is_owner()
@commands.command("cogreload")
async def cogreload():
    cogs_to_load = [
        "Nossi",
        "CommandError",
        "Remind",
        "Oracle",
        "Card",
        "Dice",
        "State",
        "Weapon",
        "Wiki",
    ]
    for cog in cogs_to_load:
        loaded = client.extensions.get(cog + "Cog", None)
        if loaded:
            client.unload_extension(f"Cogs.{cog}Cog")
        client.load_extension(f"Cogs.{cog}Cog")


@client.check_once
def allowed(ctx: Context):
    nc = client.get_cog("NossiCog")
    return (
        isinstance(ctx.channel, discord.channel.DMChannel)
        or client.user.mention in ctx.message.mentions
        or (nc and ctx.message.channel in nc.allowed_channels)
    )


@client.event
async def on_ready():
    print("Logged in as")
    print("Name:", client.user.name)
    print("ID:", client.user.id)
    await cogreload()
    print("------")
    p = discord.Permissions(117824)
    print(discord.utils.oauth_url(client.user.id, p))
    info = await client.application_info()
    await info.owner.send("I Live!")
    client.owner = info.owner


@client.event
async def on_disconnect():
    print(
        f"Disconnected at {time.time()}, accessibility of google:",
        requests.get("http://www.google.com").status_code,
    )


@client.event
async def on_resume():
    print("Resumed...")
    info = await client.application_info()
    await info.owner.send("I have Resumed")


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    ch = await client.fetch_channel(payload.channel_id)
    message = await ch.fetch_message(payload.message_id)
    if message is not None:
        await on_message(message)


@client.event
async def on_message_delete(message: discord.Message):
    await delete_replies(message)


@client.before_invoke
async def test_before(ctx: Context):
    ctx.send = get_remembering_send(ctx.message)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    errreport = message.content.startswith("?")
    if errreport:
        message.content = message.content[1:]

    nc: NossiCog = client.cogs.get("NossiBot")
    if not nc:
        warning("no NossiCog!")
    msg: str = message.content.strip("` ")
    message.content = await handle_defines(msg, message, nc.storage, nc.persist)
    ctx = await client.get_context(message)
    ctx.errreport = errreport
    await client.invoke(ctx)


if __name__ == "__main__":
    client.run(TOKEN)
    print("Done.")
