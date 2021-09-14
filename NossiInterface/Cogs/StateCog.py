from discord.ext import commands

from NossiInterface.Tools import who_am_i, discordname
from NossiPack.User import Config
from NossiPack.krypta import DescriptiveError
from NossiSite.wiki import transitions


class StateCog(commands.Cog, name="State"):
    def __init__(self, client):
        self.client = client

    @commands.group("state", invoke_without_command=True)
    async def state(self, ctx, *msg):
        msg = ":".join(msg)
        msg = [x.strip() for x in msg.lower().split(":")]
        curstate = None
        if not msg or not msg[0]:
            return await ctx.message.add_reaction("😕")
        try:
            curstate = Config.load(ctx.whoami, "state_" + msg[0]) or ""

            if len(msg) == 1:
                return await ctx.send(ctx.message.mention + " " + curstate or "None")
            selection = [
                v
                for k, v in transitions(msg[0], curstate).items()
                if msg[1] in k.lower()
            ]
            if len(selection) > 1:
                return await ctx.send(
                    ctx.author.mention
                    + f" Ambiguous command \"{msg[1]}\" between {', '.join(x.title() for x in selection)}"
                )
            if len(selection) == 0:
                return await ctx.send(
                    ctx.author.mention
                    + f' No transition for "{msg[1]}" in state "{curstate}", available are: ```'
                    + "\n".join(
                        [
                            k.title() + " => " + v[1].title()
                            for k, v in transitions(msg[0], curstate).items()
                        ]
                    )
                    + "```"
                )
            curstate = selection[0][1]
            return await ctx.send(ctx.author.mention + f" => {curstate.title()}")
        except DescriptiveError as e:
            await ctx.send(ctx.author.mention + " " + str(e.args[0]))
        finally:
            if curstate is not None and ctx.whoami:
                Config.save(ctx.whoami, "state_" + msg[0], curstate)

    @state.before_invoke
    async def state_setup(self, ctx):
        nc = self.client.cogs.get("NossiBot")
        ctx.whoami = ctx.whoami = who_am_i(nc.storage.get(discordname(ctx.author), {}))
        if not ctx.whoami:
            return await ctx.send(
                ctx.message.author.mention + " Could not ascertain Identity!"
            )

    @state.after_invoke
    async def cards_teardown(self, ctx):
        deck = getattr(ctx, "deck", None)
        whoami = getattr(ctx, "whoami", None)
        if deck and whoami:
            deck.savedeck(whoami, deck)


def setup(client: commands.Bot):
    client.add_cog(StateCog(client))
