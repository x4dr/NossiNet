import logging
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Greedy
from gamepack.fasthelpers import montecarlo

from NossiInterface.RollInterface import timeout
from NossiInterface.Tools import extract_comment
from gamepack.fengraph import chances, versus

logger = logging.getLogger(__name__)


class OracleCog(commands.Cog, name="Oracle"):
    def __init__(self, client):
        self.client = client

    @staticmethod
    def extract_mode(msg):
        mode = None
        if msg[-1].strip() in ("under", "asc", "below"):
            mode = 1
            msg = msg[:-1]
        if msg[-1].strip() in ("over", "desc", "above"):
            mode = -1
            msg = msg[:-1]
        return msg, mode

    @classmethod
    def common(cls, ctx, msg):
        if not msg:
            msg = [""]
        msg, ctx.comment = extract_comment(msg)
        msg, ctx.mode = cls.extract_mode(msg)
        ctx.sentmessage = None
        return msg

    @commands.group("oracle", case_insensitive=True, invoke_without_command=True)
    async def oraclehandle(
        self,
        ctx,
        params: Greedy[int],
        comment: Optional[str],
    ):
        msg = self.common(ctx, comment)
        mod = params[-1]
        params = params[:-1]
        if msg[0].startswith("v"):
            if len(params + [mod]) == len(msg[1:]) == 3:
                it = versus(params, msg[1:], ctx.mode)
            else:
                await ctx.send(
                    ctx.author.mention
                    + "versus mode needs exactly 3 numbers on each side"
                )
                return
            feedback = (
                ",".join(str(x) for x in params)
                + f"@5R{mod} v "
                + ",".join(str(x) for x in msg[1:-1])
                + f"@5R{msg[-1]}"
            )

        else:
            it = chances(params, mod, mode=ctx.mode)
            feedback = (
                ",".join(str(x) for x in params)
                + "@5"
                + (("R" + str(mod)) if mod else "")
            )
        sentmessage = await ctx.send("received")
        i = None
        for i in it:
            if isinstance(i, str):
                await sentmessage.edit(
                    content=ctx.author.mention + ctx.comment + " " + i
                )
        else:
            n, avg, dev = i
            logger.info(n)
            await sentmessage.edit(
                content=(
                    ctx.author.mention
                    + ctx.comment
                    + "```"
                    + feedback
                    + " avg:"
                    + str(avg)
                    + " dev: "
                    + str(dev)
                    + "\n"
                    + n
                    + "```"
                )
            )

    @oraclehandle.command("try")
    async def oracle_try(self, ctx, *msg):
        msg = self.common(ctx, msg)
        ctx.sentmessage = await ctx.send(
            "Applying the numerical HAMMER for 10 seconds..."
        )
        r = await timeout(montecarlo, " ".join(msg), 12)
        await ctx.sentmessage.edit(
            content=ctx.author.mention + ctx.comment + "\n" + str(r)[:1950]
        )

    @oraclehandle.command("show")
    async def oracle_show(
        self,
        ctx,
        params: Greedy[int],
        comment: Optional[str],
    ):
        mod = params[-2]
        percentiles = params[-1]
        params = params[:-2]
        await self.common(ctx, comment)
        it = chances(params, mod, percentiles, mode=ctx.mode)
        sentmessage = await ctx.send(ctx.author.mention + ctx.comment + " " + next(it))
        for n in it:
            if isinstance(n, str):
                await sentmessage.edit(
                    content=ctx.author.mention + ctx.comment + " " + n
                )
            else:
                await sentmessage.delete(delay=0.1)
                await ctx.send(
                    ctx.author.mention + ctx.comment,
                    file=discord.File(n, "graph.png"),
                )

    @oraclehandle.error
    async def handle_error(self, ctx, e):
        logger.exception("exception during oracle", e)

        if hasattr(ctx, "sentmessage") and ctx.sentmessage:
            await ctx.sentmessage.edit(content=ctx.author.mention + " ERROR")
            await ctx.sentmessage.delete(delay=3)
        if (not hasattr(ctx, "errreport")) or ctx.errreport:
            await ctx.author.send("Oracle error: " + " ".join(str(x) for x in e.args))
        await ctx.send_help()
        raise


def setup(client: commands.Bot):
    client.add_cog(OracleCog(client))
