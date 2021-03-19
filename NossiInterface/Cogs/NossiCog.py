import pathlib

import discord
from discord.ext import commands, tasks

import Data
from NossiInterface.Tools import discordname


class NossiCog(commands.Cog, name="NossiBot"):
    def __init__(self, client):
        self.client = client
        # self.channels = json.loads(Data.get("channels"))
        self.disconnecting = []
        self.storage = Data.read("NossiBot.storage") or dict()
        self.shutdownflag = pathlib.Path("~/shutdown_nossibot")

    @property
    def allowed_channels(self):
        return self.storage.get("allowed_channels", [])

    def persist(self):
        Data.write("NossiBot.storage", self.storage)

    @tasks.loop(seconds=5)
    async def tasks(self):
        while self.disconnecting:
            await self.disconnecting.pop().disconnect()
        if self.shutdownflag.exists():
            self.shutdownflag.unlink()
            await self.client.owner.send("I got Killed")
            self.client.close()

    @commands.group()
    async def nossi(self, ctx: commands.Context):
        """ currently disabled """
        pass
        """self.channels[ctx.message.channel.id] = (
            ctx.channel.name
            if hasattr(ctx.channel, "name")
            else discordname(ctx.message.author)
        )"""
        pass

    @commands.is_owner()
    @nossi.command("DIE")
    async def die(self, ctx):
        await ctx.message.add_reaction("\U0001f480")
        await ctx.send("I shall die.")
        await self.client.close()

    @commands.is_owner()
    @nossi.command("JOIN ME")
    async def joinme(self, ctx):
        vc: discord.VoiceChannel = ctx.author.voice.channel
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
            after=lambda e: self.disconnecting.append(connection),
        )

    @commands.is_owner()
    @nossi.command("LEAVE")
    async def leave(self, ctx):
        self.disconnecting += self.client.voice_clients
        await ctx.message.add_reaction("🔇")

    @nossi.command("i")
    async def iam(self, ctx, am: str, *msg):
        if not am == "am":
            raise commands.CommandNotFound(f'Command "i {am}" is not found')
        if self.storage.get(discordname(ctx.message.author), None) is None:
            self.storage[discordname(ctx.message.author)] = {"defines": {}}
        self.storage[discordname(ctx.message.author)]["NossiAccount"] = (
            " ".join(msg).strip().upper()
        )
        self.storage[discordname(ctx.message.author)]["DiscordAccount"] = discordname(
            ctx.message.author
        )
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        self.persist()
        await self.whoami(ctx)

    @nossi.command("who")
    async def whoami(self, am, i, ctx):
        if not ((am == "am") and (i == "i")):
            raise commands.CommandNotFound(f'Command "who {am} {i}" is not found')
        try:
            await ctx.send(
                "You are "
                + self.storage[discordname(ctx.message.author)]["NossiAccount"]
            )
        except KeyError:
            await ctx.send("I have no recollection of you.")

    @commands.guild_only()
    @nossi.command("BANISH")
    async def banish(self, ctx):
        self.storage["allowed_rooms"].remove(ctx.message.channel.id)
        await ctx.send("I will no longer listen here.")

    @commands.guild_only()
    @nossi.command("INVOKE")
    async def invoke(self, ctx):
        self.storage["allowed_rooms"] = {ctx.message.channel.id} | self.storage.get(
            "allowed_rooms", set()
        )
        await ctx.send(
            "I have been invoked and shall do my duties here until BANISHed."
        )


def setup(client: commands.Bot):
    client.add_cog(NossiCog(client))
