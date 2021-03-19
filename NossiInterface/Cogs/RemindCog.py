from discord.ext import commands

from NossiInterface.Tools import mentionreplacer
from NossiInterface.reminder import delreminder, newreminder, listreminder


class RemindCog(commands.Cog, name="Remind"):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def onready(self):
        info = await self.client.application_info()
        await info.owner.send("Wörkwörk")

    @commands.group("remind", case_insensitive=True, invoke_without_command=True)
    async def remind(self, ctx: commands.Context, *msg):
        newdate = newreminder(ctx.message, " ".join(msg))
        return await ctx.send("will remind on " + newdate.isoformat())

    @remind.command("del")
    async def remind_del(self, ctx, *msg):
        await delreminder(" ".join(msg))
        ctx.send("deleted")

    @remind.command("list")
    async def remind_list(self, ctx):
        await listreminder(ctx.message, mentionreplacer(self.client))


def setup(client: commands.Bot):
    client.add_cog(RemindCog(client))
