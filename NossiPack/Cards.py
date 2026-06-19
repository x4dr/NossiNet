"""Playing card deck management for NossiNet."""

import ast
import random
from collections.abc import Callable
from typing import Any, ClassVar

from gamepack.Dice import DescriptiveError

from NossiPack.User import Config


class Cards:
    """Represents a collection of playing cards divided into hand, deck, pile, and removed stacks."""

    Hand: set[str]
    Deck: set[str]
    Pile: set[str]
    Removed: set[str]
    Notes: dict[str, str]

    values: ClassVar[dict[str, float]] = {
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
        "X": 12,
    }

    def __init__(self, hand: str, deck: str, pile: str, removed: str, notes: str, longform: str | None = None) -> None:
        """Initialize a Cards instance.

        Args:
            hand: Space-separated string of cards in hand.
            deck: Space-separated string of cards in deck.
            pile: Space-separated string of cards in pile.
            removed: Space-separated string of removed cards.
            notes: String representation of a dict mapping cards to notes.
            longform: Optional string representation of a dict mapping short
                card codes to full names.
        """
        self.Hand = {x for x in hand.split(" ") if x}
        self.Deck = {x for x in deck.split(" ") if x}
        self.Pile = {x for x in pile.split(" ") if x}
        self.Removed = {x for x in removed.split(" ") if x}
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

    def scorehand(self) -> dict[str, float]:
        """Calculate scores for each suit in the hand.

        Returns:
            A dict mapping suit names to their total point values.
        """
        scores = dict.fromkeys(self.Longform.values(), 0.0)
        card = "<no card>"
        try:
            for card in self.Hand:
                scores[self.Longform[card[0]].lower()] = (
                    scores.get(self.Longform[card[0]].lower(), 0) + self.values[card[1]]
                )
        except KeyError:
            raise DescriptiveError("Could not score card:" + str(card)) from None
        return scores

    @property
    def serialized_parts(self) -> dict[str, str]:
        """Return the card collections serialized as strings.

        Returns:
            A dict with keys 'hand', 'deck', 'pile', 'removed', 'notes',
            and 'longform' suitable for storage.
        """
        return {
            "hand": " ".join(sorted(sorted(self.Hand), key=self.cardvalue())),
            "deck": " ".join(sorted(sorted(self.Deck), key=self.cardvalue())),
            "pile": " ".join(sorted(sorted(self.Pile), key=self.cardvalue())),
            "removed": " ".join(sorted(sorted(self.Removed), key=self.cardvalue())),
            "notes": str(self.Notes),
            "longform": str(self.Longform),
        }

    @property
    def render(self) -> dict[str, Any]:
        """Render the card collections grouped by color.

        Returns:
            A dict with 'hand' (sorted list), 'deck', 'pile', 'removed'
            (each grouped by suit color), and 'notes' (inverted by note text).
        """

        def bycolor(inp: set[str]) -> dict[str, list[str]]:
            bycolors: dict[str, list[str]] = {}
            for c in inp:
                if not c:
                    continue
                bycolors[c[0]] = sorted(
                    [*bycolors.get(c[0], []), c[1:]],
                    key=self.cardvalue(0),
                )
            return bycolors

        deckbycolors = bycolor(self.Deck)
        pilebycolors = bycolor(self.Pile)
        removedbycolors = bycolor(self.Removed)

        invertnotes: dict[str, Any] = {}
        for card, note in self.Notes.items():
            invertnotes[note] = sorted(
                [*invertnotes.get(note, []), card],
                key=self.cardvalue(),
            )
        return {
            "hand": sorted(sorted(self.Hand), key=self.cardvalue()),
            "deck": deckbycolors,
            "pile": pilebycolors,
            "removed": removedbycolors,
            "notes": invertnotes,
        }

    def elongate(self, inp: Any) -> Any:
        """Convert short card codes to long descriptive names.

        Args:
            inp: A dict, list, set, or string to convert.

        Returns:
            The input with short card codes replaced by longform names.
        """
        if isinstance(inp, dict):
            out = {}
            for k, j in list(inp.items()):
                new = self.Longform.get(k)
                if new is not None:
                    out[new] = self.elongate(j)
                    del inp[k]
                else:
                    out[k] = self.elongate(j)
            return out
        if isinstance(inp, (list, set)):
            return [self.elongate(x) for x in inp]
        if isinstance(inp, str):
            if len(inp) > 2:
                msg = f"{inp} is not in shortform!"
                raise DescriptiveError(msg)
            return (self.Longform.get(inp[0]) or inp[0]) + (
                " " + (self.Longform.get(inp[1]) or inp[1]) if len(inp) > 1 else ""
            )

    @property
    def renderlong(self) -> Any:
        """Render the card collections with long descriptive names."""
        return self.elongate(self.render)

    @classmethod
    def move(cls, source: set[str], target: set[str], par: str, movemode: int = 0) -> set[str]:
        """Move cards between collections.

        Args:
            source: The set to move cards from.
            target: The set to move cards to.
            par: Card identifiers or count (depends on movemode).
            movemode: 0 = by name, 1 = random draw, 2 = highest value.

        Returns:
            The set of cards that were moved.
        """
        moved: set[str] = set()
        try:
            if movemode == 1:
                moved = set(random.sample(list(source), int(par)))
                target.update(moved)
            elif movemode == 2:
                moved = set(sorted(source, key=cls.cardvalue())[-int(par) :])
                target.update(moved)
            else:
                for p in par.split(" "):
                    p = p.upper()
                    if not p:
                        continue  # "  "
                    if p in source:
                        moved.add(p)
                    else:
                        msg = f"{p} not found in {source if len(source) else 'empty collection'}."
                        raise DescriptiveError(
                            msg,
                        )
                    target.update(set(moved))
        except ValueError:
            if movemode == 0:
                raise
            return cls.move(source, target, par, 0)
        finally:
            source -= target
        return moved

    def draw(self, todraw: str) -> set[str]:
        """Draw cards from the deck to the hand.

        Args:
            todraw: Number of cards to draw.

        Returns:
            The set of cards drawn.
        """
        return self.move(self.Deck, self.Hand, todraw, 1)

    def spend(self, tospend: str) -> set[str]:
        """Move cards from hand to the discard pile.

        Args:
            tospend: Number of cards to spend (highest value first).

        Returns:
            The set of cards spent.
        """
        return self.move(self.Hand, self.Pile, tospend, 2)

    def pilereturn(self, toreturn: str) -> set[str]:
        """Return cards from the pile back to the deck.

        Args:
            toreturn: Number of cards to return.

        Returns:
            The set of cards returned.
        """
        return self.move(self.Pile, self.Deck, toreturn, 1)

    def remove(self, toremove: str) -> set[str]:
        """Remove cards from play into the removed stack.

        Tries hand first, then deck, then pile.

        Args:
            toremove: Card names or count to remove.

        Returns:
            The set of cards removed.
        """
        try:
            return self.move(self.Hand, self.Removed, toremove, 2)
        except DescriptiveError:
            try:
                return self.move(self.Deck, self.Removed, toremove, 1)
            except DescriptiveError:
                return self.move(self.Pile, self.Removed, toremove, 1)

    def dedicate(self, todedicate: str, purpose: str) -> set[str]:
        """Remove cards and assign them a purpose note.

        Args:
            todedicate: Cards to dedicate.
            purpose: The purpose note to attach to the removed cards.

        Returns:
            The set of cards dedicated.
        """
        removed = self.remove(todedicate)
        for r in removed:
            self.Notes[r] = purpose
        return removed

    def free(self, tofree: str) -> tuple[set[str], set[str]]:
        """Return dedicated cards back to the pile and remove their notes.

        Args:
            tofree: Cards to free.

        Returns:
            A tuple of (freed_cards, messages) where messages are the
            removed notes.
        """
        freed = self.move(self.Removed, self.Pile, tofree)
        messages = self.undedicate(" ".join(freed))
        return freed, messages

    def undedicate(self, toundedicate: str) -> set[str]:
        """Remove purpose notes from cards.

        Args:
            toundedicate: Space-separated card codes to undedicate.

        Returns:
            A set of removed note messages.
        """
        messages = []
        for f in toundedicate.split(" "):
            f = f.upper()
            m = self.Notes.get(f, None)
            if m:
                messages.append(m)
                del self.Notes[f]
        return {x for x in messages if x}

    @classmethod
    def cardvalue(cls, offs: int = 1) -> Callable[[str], float]:
        """Return a key function for sorting cards by value.

        Args:
            offs: Character offset in the card code for the value part.

        Returns:
            A callable that extracts the numeric value of a card.
        """

        def val(x: str) -> float:
            x = x.strip()
            return cls.values.get(x[offs:], 0) if x else 0

        return val

    @classmethod
    def new_cards(cls) -> Cards:
        """Create a new, shuffled full deck of cards.

        Returns:
            A Cards instance with a complete 52-card deck.
        """
        return cls(
            "",
            " ".join(sorted(Cards.full_deck(), key=cls.cardvalue())),
            "",
            "",
            "{}",
        )

    @classmethod
    def full_deck(cls) -> list[str]:
        """Generate the full 52-card deck.

        Returns:
            A list of two-character card codes for all suits and values.
        """
        d = []
        for color in "SHDC":
            for value in "234567890JQKA":
                d.append(color + value)
        return d

    @classmethod
    def getdeck(cls, username: str) -> Cards:
        """Load a user's card deck from config storage.

        Args:
            username: The user whose deck to load.

        Returns:
            A Cards instance loaded from saved data, or a new deck if none
            exists.
        """
        hand = Config.load(username, "carddeck_hand")
        deck = Config.load(username, "carddeck_deck")
        pile = Config.load(username, "carddeck_pile")
        removed = Config.load(username, "carddeck_removed")
        notes = Config.load(username, "carddeck_notes")
        longform = Config.load(username, "carddeck_longform")
        if (
            hand is not None
            and deck is not None
            and pile is not None
            and removed is not None
            and notes is not None
            and longform is not None
        ):
            return cls(hand, deck, pile, removed, notes, longform)
        return cls.new_cards()

    @classmethod
    def savedeck(cls, username: str, deck: Cards) -> None:
        """Save a user's card deck to config storage.

        Args:
            username: The user whose deck to save.
            deck: The Cards instance to persist.
        """
        for option, value in deck.serialized_parts.items():
            Config.save(username, "carddeck_" + option, value)
