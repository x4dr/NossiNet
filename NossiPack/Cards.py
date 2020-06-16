import ast
import random
from typing import Dict, Set, List

from NossiPack.User import Config
from NossiPack.krypta import DescriptiveError


class Cards:
    Hand: Set[str]
    Deck: Set[str]
    Pile: Set[str]
    Removed: Set[str]
    Notes: Dict[str, str]

    values = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "0": 10,
        "J": 10.001,
        "B": 10.001,
        "D": 10.002,
        "Q": 10.002,
        "K": 10.003,
        "A": 11,
    }

    def __init__(self, hand, deck, pile, removed, notes, longform=None):
        self.Hand = set(x for x in hand.split(" ") if x)
        self.Deck = set(x for x in deck.split(" ") if x)
        self.Pile = set(x for x in pile.split(" ") if x)
        self.Removed = set(x for x in removed.split(" ") if x)
        self.Notes = ast.literal_eval(notes)
        self.Longform = (
            ast.literal_eval(longform)
            if longform
            else {
                "C": "Clubs",
                "D": "Diamonds",
                "H": "Hearts",
                "S": "Spades",
                "0": "10",
                "J": "Jack",
                "Q": "Queen",
                "K": "King",
                "A": "Ace",
            }
        )

    @property
    def serialized_parts(self):
        return {
            "hand": " ".join(sorted(sorted(self.Hand), key=self.cardvalue())),
            "deck": " ".join(sorted(sorted(self.Deck), key=self.cardvalue())),
            "pile": " ".join(sorted(sorted(self.Pile), key=self.cardvalue())),
            "removed": " ".join(sorted(sorted(self.Removed), key=self.cardvalue())),
            "notes": str(self.Notes),
            "longform": str(self.Longform),
        }

    @property
    def render(self):
        def bycolor(inp):
            bycolors: Dict[str, List[str]] = {}
            for c in inp:
                if not c:
                    continue
                bycolors[c[0]] = sorted(
                    bycolors.get(c[0], []) + [c[1:]], key=self.cardvalue(0)
                )
            return bycolors

        deckbycolors = bycolor(self.Deck)
        pilebycolors = bycolor(self.Pile)
        removedbycolors = bycolor(self.Removed)

        invertnotes = {}
        for card, note in self.Notes.items():
            invertnotes[note] = sorted(
                invertnotes.get(note, []) + [card], key=self.cardvalue()
            )
        return {
            "hand": sorted(sorted(self.Hand), key=self.cardvalue()),
            "deck": deckbycolors,
            "pile": pilebycolors,
            "removed": removedbycolors,
            "notes": invertnotes,
        }

    def elongate(self, inp):
        if isinstance(inp, dict):
            out = {}
            for k, j in list(inp.items()):
                new = self.Longform.get(k, None)
                if new is not None:
                    out[new] = self.elongate(j)
                    del inp[k]
                else:
                    out[k] = self.elongate(j)
            return out
        if isinstance(inp, list):
            return [self.elongate(x) for x in inp]
        if isinstance(inp, str):
            if len(inp) > 2:
                raise DescriptiveError(f"{inp} is not in shortform!")
            res = (self.Longform.get(inp[0], None) or inp[0]) + (
                " " + (self.Longform.get(inp[1], None) or inp[1])
                if len(inp) > 1
                else ""
            )
            return res

    @property
    def renderlong(self):
        return self.elongate(self.render)

    @classmethod
    def move(cls, source: set, target: set, par: str, movemode=0):
        moved = set()
        try:
            if movemode == 1:
                moved = random.sample(source, int(par))
                target.update(set(moved))
            elif movemode == 2:
                moved = sorted(list(source), key=cls.cardvalue())[: -int(par)]
                target.update(set(moved))
            else:
                for p in par.split(" "):
                    p = p.upper()
                    if not p:
                        continue  # "  "
                    if p in source:
                        moved.add(p)
                    else:

                        raise DescriptiveError(
                            f"{p} not found in {source if len(source) else 'empty collection'}."
                        )
                    target.update(set(moved))
        except ValueError:
            if movemode == 0:
                raise
            else:
                return cls.move(source, target, par, 0)
        finally:
            source -= target
        return moved

    def draw(self, todraw: str):
        return self.move(self.Deck, self.Hand, todraw, 1)

    def spend(self, tospend: str):
        return self.move(self.Hand, self.Pile, tospend)

    def pilereturn(self, toreturn: str):
        return self.move(self.Pile, self.Deck, toreturn, 1)

    def remove(self, toremove: str):
        try:
            return self.move(self.Hand, self.Removed, toremove, 2)
        except:
            try:
                return self.move(self.Deck, self.Removed, toremove, 1)
            except:
                return self.move(self.Pile, self.Removed, toremove, 1)

    def dedicate(self, todedicate, purpose):
        removed = self.remove(todedicate)
        for r in removed:
            self.Notes[r] = purpose
        return removed

    def free(self, tofree):
        freed = self.move(self.Removed, self.Deck, tofree)
        messages = self.undedicate(" ".join(freed))
        return freed, messages

    def undedicate(self, toundedicate):
        messages = []
        for f in toundedicate.split(" "):
            f = f.upper()
            m = self.Notes.get(f, None)
            if m:
                messages.append(m)
                del self.Notes[f]
        return set(x for x in messages if x)

    @classmethod
    def cardvalue(cls, offs=1):
        """
        :return: key function getting keyvalue for a card
        """

        def val(x: str):
            x = x.strip()
            res = cls.values.get(x[offs:], 0) if x else 0
            return res

        return val

    @classmethod
    def new_cards(cls):
        return cls(
            "", " ".join(sorted(Cards.full_deck(), key=cls.cardvalue())), "", "", "{}"
        )

    @classmethod
    def full_deck(cls):
        d = []
        for color in "SHDC":
            for value in "234567890JQKA":
                d.append((color + value))
        return d

    @classmethod
    def getdeck(cls, username):
        carddata = (
            Config.load(username, "carddeck_hand"),
            Config.load(username, "carddeck_deck"),
            Config.load(username, "carddeck_pile"),
            Config.load(username, "carddeck_removed"),
            Config.load(username, "carddeck_notes"),
            Config.load(username, "carddeck_longform"),
        )
        if not any(x is None for x in carddata):
            return cls(*carddata)
        else:
            return cls.new_cards()

    @classmethod
    def savedeck(cls, username, deck):
        for option, value in deck.serialized_parts.items():
            Config.save(username, "carddeck_" + option, value)
