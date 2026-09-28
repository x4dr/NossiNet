"""Tests for live_edit traversal and fensheet data-path generation."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from flask import Flask, render_template
from gamepack.FenCharacter import FenCharacter
from gamepack.MDPack import MDObj
from gamepack.WikiPage import WikiPage


def _live_edit_get_text(res: str, path: list[str]) -> dict[str, Any]:
    """Import lazily: NossiSite.wiki sets the global wikipath at import time."""
    from NossiSite.wiki import live_edit_get_text

    return live_edit_get_text(res, path)


def _live_edit_get_table(res: str, path: list[str]) -> dict[str, Any]:
    from NossiSite.wiki import live_edit_get_table

    return live_edit_get_table(res, path)


@pytest.fixture(autouse=True)
def restore_wikipath() -> Iterator[None]:
    """Undo wikipath side effects of importing NossiSite.wiki."""
    previous = WikiPage._wikipath
    yield
    WikiPage._wikipath = previous


@pytest.fixture
def test_app() -> Iterator[Flask]:
    """Provide the real NossiSite app with blueprints and filters for rendering."""
    previous = WikiPage._wikipath
    WikiPage._wikipath = None
    try:
        WikiPage.set_wikipath(Path("wiki"))
        from NossiSite import sheets, views, wiki
        from NossiSite.base import app
        from NossiSite.helpers import register as register_helpers

        if "views" not in app.blueprints:
            app.register_blueprint(views.views)
        if "sheets" not in app.blueprints:
            app.register_blueprint(sheets.views)
        if "wiki" not in app.blueprints:
            app.register_blueprint(wiki.views)
        register_helpers(app)
        yield app
    finally:
        WikiPage._wikipath = previous


NESTED_SHEET = """\
# Description
## name
Testcharacter

# Values
## Mental
### Attributes
#### Intelligence
2

## Social
### Attributes
#### Empathy
3
"""


def test_live_edit_get_text_resolves_nested_path() -> None:
    """A fully qualified path into a nested section resolves to its markdown."""
    result = _live_edit_get_text(NESTED_SHEET, ["Values", "Mental"])
    assert result["type"] == "text"
    assert "Intelligence" in result["data"]


def test_live_edit_get_text_missing_step_returns_error() -> None:
    """A path missing an intermediate heading reports an error instead of raising."""
    result = _live_edit_get_text(NESTED_SHEET, ["Mental"])
    assert result["data"] == ""
    assert result["type"] == "error"
    assert "traversal error" in result["error"]


def test_live_edit_get_table_missing_step_returns_error() -> None:
    """A table path missing an intermediate heading reports an error instead of raising."""
    result = _live_edit_get_table(NESTED_SHEET, ["Mental", "Attributes"])
    assert result["data"] == ""
    assert result["type"] == "error"
    assert "traversal error" in result["error"]


@pytest.mark.parametrize("key", ["values", "description"])
def test_fensheet_headings_used_keys_exist(key: str) -> None:
    """FenCharacter stores heading lookups without leading whitespace in the key."""
    char = FenCharacter.from_mdobj(MDObj.from_md(NESTED_SHEET))
    assert key in char.headings_used


def test_fensheet_data_path_includes_values_heading(test_app: Flask) -> None:
    """Category data-paths include the parent heading so server-side traversal resolves."""
    char = FenCharacter.from_mdobj(MDObj.from_md(NESTED_SHEET))
    with test_app.test_request_context():
        rendered = render_template(
            "sheets/fensheet.html",
            character=char,
            context="character/test",
            owner="",
            userconf={"fensheet_dots": "0", "fensheet_dot_max": "5"},
            infolet=lambda x: x,
            md=lambda x: x,
            extract=lambda *_args: ({}),
        )
    assert 'data-path="Values|Mental"' in rendered
    assert 'data-path="|Mental"' not in rendered
