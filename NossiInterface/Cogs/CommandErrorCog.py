from copy import copy

import requests
from discord.ext import commands
from discord.ext.commands import CommandNotFound

from NossiInterface.NossiBot import allowed
from NossiInterface.RollInterface import rollhandle
from NossiInterface.Tools import extract_comment


class CommandErrorCog(commands.Cog):
    client: commands.Bot

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        # return if there is an error handler already
        if hasattr(ctx.command, "on_error") or (
            ctx.cog
            and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None
        ):
            return
        # use original error if it exists
        if hasattr(error, "original"):
            error = error.original

        if "\n" in ctx.message.content:
            for m in ctx.message.content.split("\n"):
                msg = copy(ctx.message)
                msg.content = m
                await self.client.process_commands(msg)
            return

        msg, ctx.comment = extract_comment(ctx.message.content)
        if ctx.message.nonce == "recursed" or ctx.message.content.startswith(
            "NossiBot "
        ):
            return False
        for pref in {"NossiBot "}:
            ctx.message.content = pref + ctx.message.content
            ctx.message.nonce = "recursed"
            await self.client.invoke(ctx)

        if not allowed(ctx):
            return

        msg = " ".join(msg)

        if len(msg) <= 30 and not msg.startswith("?"):
            await rollhandle(
                msg,
                ctx.comment,
                ctx.author,
                ctx.send,
                ctx.message.add_reaction,
                self.client.cogs.get("NossiBot", None).storage,
            )

        try:
            raise error
        except requests.exceptions.ConnectionError:
            await ctx.send("Connection failed.")
        except CommandNotFound:
            if ctx.message.content.startswith("?"):
                await ctx.send("Not found")
            # silently ignore


def setup(client: commands.Bot):
    client.add_cog(CommandErrorCog(client))
