"""Guard against JavaScript and templates drifting apart silently.

The recurring root cause of the ``closebutton`` and duplicate ``table_editor``
bugs was not that JS used ids — it was that a mismatch between a JS selector and
the template markup produced *no* error. A renamed or deleted id simply made
``getElementById`` return ``null`` and the feature quietly stopped working.

This test turns that class of silent breakage into a test failure: every id the
static JavaScript reaches for must either exist in a template, or be listed below
as JS-owned (created by JavaScript itself, with no template behind it).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = REPO_ROOT / "NossiSite" / "static"
TEMPLATE_DIR = REPO_ROOT / "NossiSite" / "templates"

# getElementById("x") and querySelector("#x") / querySelectorAll("#x")
JS_ID_PATTERN = re.compile(r"""getElementById\(\s*['"]([\w-]+)['"]\s*\)|querySelector(?:All)?\(\s*['"]#([\w-]+)['"]""")
TEMPLATE_ID_PATTERN = re.compile(r"""\bid\s*=\s*['"]([\w-]+)['"]""")

# Ids that JavaScript builds itself, so no template is expected to declare them.
# The TipTap overlay (tip-*) is injected as an HTML template literal in
# tip-wiki-editor.js; the tooltip container and its <style> are created by
# tooltip.js; wiki-tag-validator-init is a load-once marker in
# wiki-tag-validator.js.
JS_OWNED_IDS = {
    "nossi-tooltip-style",
    "tip-close",
    "tip-editor",
    "tip-save",
    "tip-source-area",
    "tip-source-toggle",
    "tip-tag-select",
    "tooltip-container",
    "wiki-tag-validator-init",
}


def _js_referenced_ids() -> set[str]:
    """Collect every element id the static JavaScript looks up.

    Returns:
        Sorted list of ids referenced from ``NossiSite/static``.
    """
    found: set[str] = set()
    for js_file in STATIC_DIR.rglob("*.js"):
        source = js_file.read_text(encoding="utf8", errors="replace")
        for match in JS_ID_PATTERN.finditer(source):
            found.add(match.group(1) or match.group(2))
    return found


def _template_ids() -> set[str]:
    """Collect every element id declared by a Jinja template.

    Returns:
        Set of ids found in ``NossiSite/templates``.
    """
    found: set[str] = set()
    for template in TEMPLATE_DIR.rglob("*.html"):
        found.update(TEMPLATE_ID_PATTERN.findall(template.read_text(encoding="utf8", errors="replace")))
    return found


def test_js_id_selectors_exist_in_templates() -> None:
    """Every id JS looks up is either declared in a template or explicitly JS-owned."""
    unaccounted = _js_referenced_ids() - _template_ids() - JS_OWNED_IDS
    assert not unaccounted, (
        "JavaScript queries ids that no template declares and that are not listed as "
        f"JS-owned: {sorted(unaccounted)}. Either the template lost the element or the "
        "JS selector is stale."
    )


def test_js_owned_ids_are_still_referenced() -> None:
    """The JS-owned set has not grown stale."""
    stale = JS_OWNED_IDS - _js_referenced_ids()
    assert not stale, (
        f"{sorted(stale)} are listed in JS_OWNED_IDS but no longer referenced by any "
        "JavaScript. If the element moved into a template, remove it from the set."
    )
