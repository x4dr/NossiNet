import subprocess
from discord.ext import commands

import Data


class MinecraftCog(commands.Cog, name="Minecraft"):
    def __init__(self, client):
        self.client = client

    @commands.group("mc", case_insensitive=True, invoke_without_command=True)
    async def mc(self):
        pass

    @mc.command("up")
    async def start_mc(self, ctx):
        try:
            usrs = Data.get("mc_powerusers").splitlines(keepends=False)
        except FileNotFoundError:
            usrs = []
            Data.set("mc_powerusers", "")
        if str(ctx.author.id) not in usrs:
            await ctx.message.add_reaction("👎")
            return
        await ctx.message.add_reaction("👍")
        subprocess.call(["mcstart"])

    @commands.is_owner()
    @mc.command("reg")
    async def register_user(self, ctx, *msg):

        ids = {str(x.id) for x in ctx.message.mentions}
        try:
            usrs = set(Data.get("mc_powerusers").splitlines(keepends=False))
        except FileNotFoundError:
            Data.set("mc_powerusers", "")
            usrs = set()
        if "remove" in msg:
            for i in ids:
                usrs.remove(i)
            await ctx.message.add_reaction("👎")
        else:
            usrs.update(ids)
            await ctx.message.add_reaction("👍")
        Data.set("mc_powerusers", "\n".join(usrs))


def setup(client: commands.Bot):
    client.add_cog(MinecraftCog(client))
