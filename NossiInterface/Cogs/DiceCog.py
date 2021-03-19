from discord.ext import commands


class DiceCog(commands.Cog, name="Dice"):
    def __init__(self, client):
        self.client = client

    # @commands.command("yo")
    async def test(self, ctx: commands.Context):
        print("yo")
        await ctx.send("yo")


def setup(client: commands.Bot):
    client.add_cog(DiceCog(client))
