import logging
from urllib.parse import quote

import requests
from discord.ext import commands

from NossiInterface.RollInterface import chunk_reply
from NossiInterface.Tools import extract_comment

logger = logging.getLogger(__name__)


class WikiCog(commands.Cog, name="Wiki"):
    def __init__(self, client):
        self.client = client

    @commands.command(
        "wiki",
        brief="Accesses the Nosferatu net wiki",
        description="usage :\n wiki <site> [:accessor]\n"
        "where accessor is a :-separated list of the path of headings to follow."
        "if multiple headings match, the first is taken",
    )
    async def wiki(self, ctx, *msg):
        msg, ctx.comment = extract_comment(msg)
        msg = " ".join(msg)
        reply = requests.get(
            self.client.nossiUrl + "specific/" + quote(msg.strip()) + "/raw"
        )
        if reply.status_code == 200:
            content = reply.content.decode("utf-8")
            if (
                len(content) > 1900
                and sum(line.strip().startswith("#") for line in content.splitlines())
                > 1
            ):
                await chunk_reply(
                    ctx.send,
                    ctx.author.mention
                    + ctx.comment
                    + " There was too much text, please select from:\n",
                    "\n".join(
                        line
                        for line in content.splitlines()
                        if line.strip().startswith("#")
                    ),
                )
            else:
                await chunk_reply(ctx.send, ctx.author.mention + ctx.comment, content)
            return
        elif reply.status_code == 404:
            logger.error(f"{msg} not found")
            await ctx.send(
                ctx.author.mention + "\n" + msg.replace(":", r"\:") + " Not Found"
            )
        logger.error(f"failed request: {reply.status_code}, {reply.url}")


def setup(client: commands.Bot):
    client.add_cog(WikiCog(client))
