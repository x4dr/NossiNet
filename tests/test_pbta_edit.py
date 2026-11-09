"""Unit tests for the PBTA markdown edit helpers.

These helpers rewrite a PBTA character sheet's markdown when a gauge is clicked,
a move is toggled, or notes are saved. Getting one wrong corrupts the player's
character sheet, so the edge cases matter more than the happy path.
"""

import pytest

from NossiSite.pbta_edit import set_health, set_notes, toggle_move

HEALTH_PAGE = """---
tags:
- pbta
title: Test
---

# Health

| Type    | Current | Maximum |
|---------|---------|---------|
| Stress  | 2       | 7       |
| Trauma  | 3       | 4       |
| Healing | 0       | 4       |
| Armor   | 1       | 3       |

# Notes
keep me
"""


def test_set_health_updates_only_the_named_row() -> None:
    """Clicking Stress leaves every other health row untouched."""
    out = set_health(HEALTH_PAGE, "Stress", 5)
    assert "| Stress  | 5       | 7       |" in out
    assert "| Trauma  | 3       | 4       |" in out
    assert "| Healing | 0       | 4       |" in out
    assert "| Armor   | 1       | 3       |" in out


def test_set_health_clamps_to_maximum() -> None:
    """A stress value above the maximum is clamped, not written literally."""
    out = set_health(HEALTH_PAGE, "Stress", 99)
    assert "| Stress  | 7       | 7       |" in out


def test_set_health_clamps_to_zero() -> None:
    """A negative value clamps to zero."""
    out = set_health(HEALTH_PAGE, "Armor", -5)
    assert "| Armor   | 0       | 3       |" in out


def test_set_health_can_change_maximum() -> None:
    """Passing a maximum rewrites the third column too."""
    out = set_health(HEALTH_PAGE, "Stress", 9, maximum=12)
    assert "| Stress  | 9       | 12       |" in out
    # The original single-digit padding is preserved after the new value; markdown
    # does not require aligned pipes, so this is cosmetic only.
    assert "| 9 " in out and " 12 " in out


def test_set_health_is_case_insensitive() -> None:
    """Row labels match regardless of case."""
    out = set_health(HEALTH_PAGE, "stress", 4)
    assert "| Stress  | 4       | 7       |" in out


def test_set_health_unknown_row_is_a_no_op() -> None:
    """A label that is not a health row leaves the page byte-identical."""
    assert set_health(HEALTH_PAGE, "Nonsense", 3) == HEALTH_PAGE


MOVES_PAGE = """# Moves
- [ ] Take the hit
- [x] Already done
- [ ] Name has (parens) and [brackets]
"""


def test_toggle_move_flips_unchecked_to_checked() -> None:
    """Toggling an unchecked move checks it."""
    out = toggle_move(MOVES_PAGE, "Take the hit")
    assert "- [x] Take the hit" in out


def test_toggle_move_flips_checked_to_unchecked() -> None:
    """Toggling a checked move unchecks it."""
    out = toggle_move(MOVES_PAGE, "Already done")
    assert "- [ ] Already done" in out


def test_toggle_move_respects_explicit_state() -> None:
    """An explicit checked= does not flip; it sets."""
    assert "- [x] Take the hit" in toggle_move(MOVES_PAGE, "Take the hit", checked=True)
    assert "- [ ] Already done" in toggle_move(MOVES_PAGE, "Already done", checked=False)


def test_toggle_move_handles_regex_metacharacters() -> None:
    """Move names containing regex syntax are matched literally."""
    out = toggle_move(MOVES_PAGE, "Name has (parens) and [brackets]")
    assert "- [x] Name has (parens) and [brackets]" in out


def test_toggle_move_does_not_match_prefix_of_another_move() -> None:
    """Toggling "Take" must not corrupt the line "Take the hit"."""
    page = "# Moves\n- [ ] Take the hit\n"
    assert toggle_move(page, "Take") == page


def test_toggle_move_unknown_move_is_a_no_op() -> None:
    """A move not in the page leaves it byte-identical."""
    assert toggle_move(MOVES_PAGE, "Nonexistent") == MOVES_PAGE


NOTES_PAGE = """# Health

| Stress | 1 | 7 |

# Notes
old note line

# Stats
should survive
"""


def test_set_notes_replaces_until_next_heading() -> None:
    """Only the Notes body is replaced; later sections survive."""
    out = set_notes(NOTES_PAGE, "new note")
    assert "new note" in out
    assert "old note line" not in out
    assert "# Stats" in out
    assert "should survive" in out


def test_set_notes_without_heading_is_a_no_op() -> None:
    """A page with no Notes heading is left alone."""
    assert set_notes("# Stats\nnothing\n", "x") == "# Stats\nnothing\n"


def test_set_notes_at_end_of_page() -> None:
    """Notes at the end of the page are replaced without eating nothing."""
    out = set_notes("# Notes\nold\n", "new")
    assert "new" in out
    assert "old" not in out


@pytest.mark.parametrize("heading", ["# Notes", "## Notes", "### notes"])
def test_set_notes_accepts_any_heading_level(heading: str) -> None:
    """Notes may be marked with any heading level, matched case-insensitively."""
    page = f"{heading}\nold\n"
    out = set_notes(page, "fresh")
    assert "fresh" in out
    assert "old" not in out


def test_set_notes_stops_at_lower_level_heading() -> None:
    """A deeper heading after Notes belongs to the notes section."""
    page = "# Notes\nold\n### detail\nstill notes\n"
    out = set_notes(page, "fresh")
    assert "still notes" not in out
    assert "fresh" in out
