from urllib.parse import quote
import requests
from discord.ext import commands
from NossiInterface.RollInterface import chunk_reply
from NossiInterface.Tools import extract_comment


class WeaponCog(commands.Cog, name="Weapons"):
    def __init__(self, client):
        self.client = client

    @commands.command("weapon")
    async def weapon(self, ctx, *msg):
        msg, ctx.comment = extract_comment(msg)
        msg = "weapon:" + " ".join(msg)
        await self.handle_reply(ctx, self.make_request(msg), msg)

    @commands.command("magicalweapon")
    async def mweapon(self, ctx, *msg):
        msg, ctx.comment = extract_comment(msg)
        msg = "magicalweapon:" + " ".join(msg)
        await self.handle_reply(ctx, self.make_request(msg), msg)

    def make_request(self, msg):
        return requests.get(
            self.client.nossiUrl + "/".join(quote(x.strip()) for x in msg.split(":", 2))
        )

    @staticmethod
    async def handle_reply(ctx, reply, msg):
        if reply.status_code == 200:
            content = reply.content.decode("utf-8")
            if len(content) > 1950:
                await chunk_reply(ctx.author.send, "", content)
            else:
                await chunk_reply(
                    ctx.send, ctx.author.mention + ctx.comment + "\n", content
                )
        elif reply.status_code == 404:
            print(msg, "not found")
            await ctx.send(
                ctx.author.mention + "\n" + msg.replace(":", r"\:") + " Not Found"
            )
        else:
            await ctx.message.react("😕")
            print("failed request:", reply.status_code, reply.url)


def setup(client: commands.Bot):
    client.add_cog(WeaponCog(client))
