import asyncio
import datetime
import re
import time

from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot
from pytz import reference

from NossiInterface.Tools import mentionreplacer
from NossiInterface.reminder import (
    delreminder,
    newreminder,
    listreminder,
    next_reminders,
    set_user_tz,
)


class RemindCog(commands.Cog, name="Remind"):
    def __init__(self, client):
        self.client: Bot = client
        self.reminding.start()

    @tasks.loop(minutes=1)
    async def reminding(self):
        repeat = True
        while repeat:
            repeat = False  # probably wont pull reminders more than once
            nr = list(next_reminders())
            for r in nr:  # pull the next relevant reminders
                delta = r[2] - time.time()
                if delta > 60:
                    break  # nothing within a minute, we will be called again before its time
                else:
                    await asyncio.sleep(
                        delta
                    )  # since reminders are in order we consume them in order
                    channel: TextChannel = self.client.get_channel(r[1])
                    if not channel:
                        break  # not connected, try later
                    await channel.send(r[3])
                    delreminder(r[0])
            else:  # if we consume all within a minute, we need to pull more
                repeat = bool(nr)  # but only if there were reminders

    @commands.command()
    async def tzset(self, ctx: commands.Context, tz=None):
        if not tz:
            return await ctx.message.add_reaction("❓")
        try:
            set_user_tz(ctx.author.id, tz)
            return await ctx.message.add_reaction("👍")
        except ValueError:
            await ctx.send(
                ctx.author.mention
                + " Not a Valid TimeZone. Try Europe/Berlin or look up your IANA tzinfo online."
            )

    @commands.group("remind", case_insensitive=True, invoke_without_command=True)
    async def remind(self, ctx: commands.Context, *msg):
        try:
            newdate = newreminder(ctx.message, " ".join(msg), ctx.author.id)
            await ctx.send("will remind on " + newdate.isoformat())
        except KeyError:
            await set_user_tz(ctx.author.id, "Europe/Berlin")
            await ctx.send(
                "No timezone configured, automatically set to Europe/Berlin.\n"
                "Please use the command tzset with your timezone if you want to change it."
            )

    @remind.command("del")
    async def remind_del(self, ctx, *msg):
        await delreminder(" ".join(msg))
        ctx.send("deleted")

    @remind.command("list")
    async def remind_list(self, ctx):
        toshow = ""
        for r in listreminder(ctx.message):
            toshow += f"{datetime.datetime.fromtimestamp(int(r[2]), reference.LocalTimezone())}: {r[3]}\n"

        toshow = re.sub(r"<@!?(.*?)>", mentionreplacer(self.client), toshow)
        await ctx.channel.send("Reminders:\n" + toshow)


def setup(client: commands.Bot):
    client.add_cog(RemindCog(client))
