from discord.ext import commands

import Data
from NossiInterface.Tools import who_am_i, split_send, spellhandle
from NossiPack.Cards import Cards
from NossiPack.krypta import DescriptiveError


class CardCog(commands.Cog, name="Cards"):
    def __init__(self, client):
        self.client = client

    def form(self, inp):
        if isinstance(inp, dict):
            outp = ""
            for k, j in inp.items():
                outp += "\n" + str(k) + ": " + self.form(j)
            return outp
        elif isinstance(inp, list):
            return ", ".join(inp)
        elif isinstance(inp, str):
            return inp
        else:
            DescriptiveError("HUH?")

    @commands.group("cards", invoke_without_command=True)
    async def cards(self, ctx, cmd):

        infos = ctx.deck.renderlong
        if cmd in infos:
            await ctx.send(ctx.author.mention + " " + self.form(infos[cmd]))
        else:
            await ctx.send_help("cards")

    @cards.before_invoke
    async def cards_setup(self, ctx):
        nc = self.client.cogs.get("NossiBot")

        ctx.whoami = who_am_i(nc.storage)
        if not ctx.whoami:
            return await ctx.send(
                ctx.message.author.mention + " Could not ascertain Identity!"
            )
        else:
            ctx.deck = Cards.getdeck(ctx.whoami)

    @cards.after_invoke
    async def cards_teardown(self, ctx):
        deck = getattr(ctx, "deck", None)
        whoami = getattr(ctx, "whoami", None)
        if deck and whoami:
            deck.savedeck(whoami, deck)

    @cards.command("draw")
    async def draw(self, ctx, *par):
        await ctx.send(
            ctx.mention + " " + self.form(ctx.deck.elongate(ctx.deck.draw(par)))
        )

    @cards.command("spend")
    async def spend(self, ctx, *par):
        ctx.deck.spend(par)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    @cards.command("returnfun")
    async def returnfun(self, ctx, *par):
        await ctx.send(
            ctx.author.mention
            + " "
            + self.form(ctx.deck.elongate(ctx.deck.pilereturn(par)))
        )

    @cards.command("dedicate")
    async def dedicate(self, ctx, *par):
        ctx.deck.dedicate(" ".join(par).split(":", 1))
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    @cards.command("remove")
    async def remove(self, ctx, *par):
        ctx.deck.remove(par)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")

    @cards.command("undedicate")
    async def undedicate(self, ctx, *par):
        message = ctx.deck.undedicate(par)
        await ctx.send(
            ctx.author.mention
            + f" Affected Dedication{'s' if len(message) != 1 else ''}: "
            + ("\n".join(message) or "none")
        )

    @cards.command("free")
    async def free(self, ctx, *par):
        _, message = ctx.deck.free(par)
        await ctx.send(
            ctx.author.mention
            + f" Affected Dedication{'s' if len(message) != 1 else ''}: "
            + (",\n and ".join(message) or "none")
        )

    @cards.command("help")
    async def help(self, ctx):
        await split_send(ctx.message.author.send, Data.getcardhelp().splitlines())

    @cards.command("spells")
    async def spells(self, ctx, *par):
        await spellhandle(ctx.deck, ctx.whoami, par, ctx.send)
        await ctx.message.add_reaction("\N{THUMBS UP SIGN}")


def setup(client: commands.Bot):
    client.add_cog(CardCog(client))
