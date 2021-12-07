import datetime
import logging.config
import os
from logging import warning

import discord
import requests
from dateutil.tz import tzlocal
from discord.ext import commands

import Data
from NossiInterface.Cogs.NossiCog import NossiCog
from NossiInterface.Tools import (
    get_remembering_send,
    delete_replies,
    handle_defines,
)

logging.config.fileConfig(Data.handle("logging_config_NossiBot.conf"))
logger = logging.getLogger(__name__)

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

logger.info("initializing NossiBot...")

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
        "State",
        "Weapon",
        "Wiki",
        "Minecraft",
    ]
    for cog in cogs_to_load:
        cogname = f"Cogs.{cog}Cog"
        loaded = client.extensions.get(cogname, None)
        if loaded:
            client.unload_extension(cogname)
        client.load_extension(cogname)


async def allowed(msg: discord.Message):
    nc = client.get_cog("NossiBot")
    dmchannel = isinstance(msg.channel, discord.channel.DMChannel)
    mentioned = client.user.mention in msg.mentions if client.user else False
    adressed = msg.content.strip().startswith("NossiBot")
    allowed_in_channel = nc and msg.channel.id in nc.allowed_channels
    if not nc:
        (await client.application_info()).owner.send("NossiCog not loaded!")
    return dmchannel or mentioned or adressed or allowed_in_channel


@client.event
async def on_ready():
    logger.info("Logged in as")
    logger.info(f"Name: {client.user.name}")
    logger.info(f"ID:{client.user.id}")
    await cogreload()
    logger.info("------")
    p = discord.Permissions(117824)
    logger.info(discord.utils.oauth_url(client.user.id, p))
    await (await client.application_info()).owner.send(
        "I Live! My Cogs are:" + str(list(client.cogs.keys()))
    )


@client.event
async def on_disconnect():
    logger.warning(
        f"Disconnected at {datetime.datetime.now(tzlocal())}, accessibility of google:"
        f"{requests.get('https://www.google.com').status_code}"
    )


@client.event
async def on_resume():
    logger.info("Resumed...")
    await (await client.application_info()).owner.send("I have Resumed")


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    ch = await client.fetch_channel(payload.channel_id)
    message = await ch.fetch_message(payload.message_id)
    if message is not None:
        await on_message(message)


@client.event
async def on_message_delete(message: discord.Message):
    await delete_replies(message)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not await allowed(message):
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
    ctx.send = get_remembering_send(message)
    await client.invoke(ctx)


if __name__ == "__main__":
    client.run(TOKEN)
    logger.info("Done.")
