import pathlib

import discord
from discord.ext import commands, tasks

import Data
from NossiInterface.Tools import discordname


class NossiCog(commands.Cog, name="NossiBot"):
    def __init__(self, client):
        self.client: discord.client = client
        self.storage = Data.read("NossiBot.storage") or dict()
        self.shutdownflag = pathlib.Path("~/shutdown_nossibot")
        self.tasks.start()

    @property
    def allowed_channels(self):
        return self.storage.get("allowed_rooms", [])

    def persist(self):
        Data.write("NossiBot.storage", self.storage)

    @tasks.loop(seconds=5)
    async def tasks(self):
        for c in self.client.voice_clients:
            if not c.is_playing():
                await c.disconnect()
        if self.shutdownflag.exists():
            self.shutdownflag.unlink()
            await self.client.owner.send("I got Killed")
            self.client.close()

    @commands.group(name="NossiBot")
    async def nossi(self, ctx: commands.Context):
        pass

    @commands.is_owner()
    @nossi.command("DIE")
    async def die(self, ctx):
        await ctx.message.add_reaction("\U0001f480")
        await ctx.send("I shall die.")
        await self.client.close()

    @commands.is_owner()
    @nossi.command("JOIN")
    async def joinme(self, ctx):
        vc = ctx.author.voice.channel
        connection: discord.VoiceClient = await vc.connect()
        print("Voice Connection:", connection.is_connected())
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
            after=lambda e: print(
                "disconnected with " + (f"{e}" if e else "no errors.")
            ),
        )

    @nossi.command("SYNC")
    async def sync(self, ctx):
        vc = ctx.author.voice.channel
        for c in self.client.voice_clients:
            if vc == c.channel:
                connection = c
                break
        else:
            return
        r = discord.FFmpegPCMAudio(
            pathlib.Path("~/soundpipe").expanduser(),
            before_options="-f s32le -ac 2 -ar 48000",
        )

        connection.stop()
        connection.play(
            r,
            after=lambda e: print(
                "disconnected with " + (f"{e}" if e else "no errors.")
            ),
        )
        connection.resume()

    @commands.is_owner()
    @nossi.command("LEAVE")
    async def leave(self, ctx):
        vc = ctx.author.voice.channel
        for c in self.client.voice_clients:
            if vc == c.channel:
                connection = c
                break
        else:
            return
        await connection.disconnect()
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
