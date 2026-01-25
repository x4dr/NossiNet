from typing import Dict, Callable, Any, Type, TypeVar
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.BaseCharacter import BaseCharacter

T = TypeVar("T", bound=BaseCharacter)

_renderers: Dict[Type[BaseCharacter], Callable[[WikiCharacterSheet[Any]], Any]] = {}


def register_renderer(char_type: Type[T]):
    """
    Decorator to register a renderer function for a specific character type.
    """

    # Registering...
    def decorator(func: Callable[[WikiCharacterSheet[Any]], Any]):
        _renderers[char_type] = func
        return func

    return decorator


def render_sheet(sheet: WikiCharacterSheet[Any]) -> Any:
    """
    Dispatches the rendering of a character sheet to the appropriate registered renderer.
    """
    if not sheet.char:
        return None

    # Find the best matching renderer (handling inheritance)
    for char_type in type(sheet.char).mro():
        if char_type in _renderers:
            return _renderers[char_type](sheet)

    return None


# Import renderers to register them
from . import mecharenderer, characterrenderer, pbtarenderer  # noqa: E402, F401
