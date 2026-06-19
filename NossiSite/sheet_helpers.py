"""Helper utilities for infolet rendering in character sheets."""

from collections.abc import Callable
from pathlib import Path

from NossiPack.markdown.tags.infolet import InfoletTag


def infolet_filler(_context: str | Path) -> Callable[[str], str]:
    """Create a filler function that passes through text unchanged.

    Args:
        _context: Unused context parameter.

    Returns:
        A wrapper function that returns its input unchanged.
    """

    def wrap(s: str) -> str:
        return s

    return wrap


def infolet_extractor(x: str) -> str:
    """Extract the name portion from an infolet tag string.

    Args:
        x: The string to extract from.

    Returns:
        The extracted name, or the original string if no match.
    """
    m = InfoletTag.infolet_re.match(str(x))
    if not m:
        return str(x)
    return m.group("name")
