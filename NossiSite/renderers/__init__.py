"""Renderer registration and dispatch for character sheet types."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from gamepack.BaseCharacter import BaseCharacter

if TYPE_CHECKING:
    from gamepack.WikiCharacterSheet import WikiCharacterSheet

T = TypeVar("T", bound=BaseCharacter)

_renderers: dict[type[BaseCharacter], Callable[[WikiCharacterSheet[Any]], Any]] = {}


def register_renderer[T: BaseCharacter](
    char_type: type[T],
) -> Callable[[Callable[[WikiCharacterSheet[Any]], Any]], Callable[[WikiCharacterSheet[Any]], Any]]:
    """Register a renderer function for a specific character type."""

    # Registering...
    def decorator(func: Callable[[WikiCharacterSheet[Any]], Any]) -> Callable[[WikiCharacterSheet[Any]], Any]:
        _renderers[char_type] = func
        return func

    return decorator


def render_sheet(sheet: WikiCharacterSheet[Any]) -> Any:
    """Dispatches the rendering of a character sheet to the appropriate registered renderer."""
    if not sheet.char:
        return None

    # Find the best matching renderer (handling inheritance)
    for char_type in type(sheet.char).mro():
        if char_type in _renderers:
            return _renderers[char_type](sheet)

    return None


# Import renderers to register them
from . import characterrenderer, mecharenderer, pbtarenderer  # noqa: E402, F401
