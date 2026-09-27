# Code Improvement Plan

| Tool | Start | Now | Δ |
|------|-------|-----|---|
| ruff violations | 3,374 | 0 | −100% |
| mypy errors | 1,805 | 0 | −100% |

`ruff check .` and `mypy --strict .` are both clean over 65 source files, and
`uv run pytest` is at 141 passed / 0 failed with **no NossiNet server running**.
This file is a record of how that was reached; the phases below are historical.

## Phase 0: Safe auto-fixes ✅
- `ruff check --fix` — 820 safe fixes applied
- `ruff format` — reformatted 18+ files
- **Done**

## Phase 1a: Unsafe ruff fixes (human-in-loop) ✅
- All unsafe rules resolved — see `unsafe-fixes.md`
- **Done**

## Phase 1b: Mypy mechanical ✅
- `-> None` on void functions across 22+ files
- `dict`/`list` generic type params
- `var-annotated` for obvious variables
- `Match | None.group()` → proper None checks (21 fixes in Character.py, VampireCharacter.py, Chatrooms.py, links.py)
- `no-any-return` eliminated (6 fixes)
- **Done**

## Phase 2: Mypy needs human judgment ✅
- Was: 32 `union-attr`, 336 `no-untyped-def`, 230 `no-untyped-call`, 19 `assignment`
- **Done** — landed in `285066c` ("achieve mypy strict zero across all 61 source files").
  This phase was still listed as blocked; it is not. The 19 `assignment` findings
  did not surface as runtime bugs.

## Phase 3: Ruff mechanics (I001, SIM108, UP043, F401, SIM110) ✅
- I001: import sorting in views.py, wiki.py, sheets.py
- SIM108: 25 ternary simplifications across codebase
- UP043: 5 Generator type simplifications in extra.py
- F401: unused WerkzeugResponse import in chat.py
- SIM110: for→any in GamePack MDPack.py
- **Done**

## Phase 4: Ruff docstrings — main codebase ✅
- ~475 `D*` violations resolved across 61 files (NossiSite, NossiPack, tests, root)
- 6 parallel agent batches + 17 manual touch-ups (D205/D401/D417/D103)
- **Done**

## Phase 5: Ruff naming ✅
- Was: N999 (16 violations) from CamelCase module names, deferred as it touched
  every import.
- **Resolved by configuration instead** — `N999` is in the ruff ignore list at
  `pyproject.toml:77` (commit `8c933e9`). The rename never happened and is not
  wanted.

---

## Test-suite repairs

The suite was red (6 failures + 1 collection error) while the linters were
green. All of it is now fixed.

### Fixed
1. **`test_localmarkdown_errors.py` — `NameError: ConsoleMessage`**
   Imported under `TYPE_CHECKING` but the nested `log_error` annotation was
   evaluated at runtime. Fixed with `from __future__ import annotations`.
2. **HTTPS cert flag dropped in `test_chat_timestamps.py`**
   Three modules each defined their own `browser_context_args`; a module-level
   fixture shadows the conftest one, so `ignore_https_errors` silently vanished
   for whichever module defined it. Consolidated into `tests/ui/conftest.py`
   (4 duplicates removed).
3. **`test_priority_conflict` — two bugs**
   `priority = 5` collided with the real `StrikethroughTag`, so the class body
   raised before the `pytest.raises` block was entered; and
   `match="Priority Conflict"` could never match the actual message
   `"Priority conflict"` (`re.search` is case-sensitive).
4. **`test_mecha_core_features.py` — deleted**
   Asserted on a `FuelConserving` loadout that exists in no code path and no DB
   row. `mechtest` only ever gets the auto-generated `Default` loadout.
5. **Wiki tag rendering no longer tested through a browser**
   Was a Playwright test hardcoding the live `/wiki/demo` page's contents. Now 8
   hermetic unit tests in `tests/test_nossi_markdown.py` render inline fixture
   markdown via `NossiMarkdownProcessor.process()` with `WikiPage._wikipath`
   monkeypatched at a tmp dir.
6. **Editor save tests no longer write to the real `~/wiki`**
   See below.

### Test isolation

`tests/ui/test_wiki_live_edit.py` (8 tests) used to run against the dev server on
:5000 and click `#tip-save` on the real `/wiki/demo`, overwriting the
developer's wiki on every run. It now runs against a server started with
`NOSSI_WIKI_PATH` pointed at a temporary git clone of
`tests/fixtures/editor_wiki_page.md`. The temp wiki must be a git repo with at
least one commit, because saving goes through `WikiPage.save_overwrite` →
`commit_and_push` → `Repo(wikipath)`.

`NOSSI_WIKI_PATH` is read at `NossiSite/wiki.py:39`; it defaults to `~/wiki`, so
behaviour is unchanged without it. This mirrors the existing
`DATABASE = os.environ.get("DATABASE", "./NN.db")` pattern at `Data/__init__.py:13`.

---

## Open items

_None. Every item below was open at the start of this pass and is now closed._

### 1. Stale-server squatting made tests assert against the wrong app ✅
An abandoned pytest run leaves a server holding its port. The next run's
"wait for port" check succeeds against the *previous* server, so every test
quietly asserts against the wrong wiki or database. It presented as
"the fixture page is missing", not as a port conflict — which is exactly how it
was diagnosed: `test_sheet_live_edit.py` had claimed :5002 before
`test_wiki_live_edit.py` ran, and its server served the real `~/wiki`.

All servers now start through one factory, `nossi_server` in
`tests/ui/conftest.py`, which refuses to start if the port is taken. The
hand-rolled `time.sleep(8)` waits in `test_chat_timestamps.py` and
`test_sheet_live_edit.py` are gone.

### 2. The UI tests needed a manually started dev server ✅
`test_clock_interaction.py`, `test_localmarkdown_errors.py`,
`test_localmarkdown_rendering.py` and `test_sse_connectivity.py` targeted
`https://127.0.0.1:5000` and only passed if a server happened to be running, so
a clean checkout failed them. They now use the `app_server` fixture (throwaway
wiki + throwaway database copy), and the suite passes with no server running at
all.

`test_clock_interaction.py` had also hardcoded a clock id
(`IRUWOQ3FNRWGC4Q-MNWG6Y3LOMXG2ZA`) hashed from the developer's real
`~/wiki/clocks.md`; it now selects `.clock-container` from a fixture page
(`tests/fixtures/clocks_wiki_page.md`).

### 3. JS ↔ template drift was silent ✅
The root cause of the `closebutton` and duplicate `table_editor` bugs was not
that JS used ids — it was that a mismatch produced no error, `getElementById`
just returned `null` and the feature quietly stopped working.

Rather than cosmetically renaming the last six id selectors to `data-*` (all of
them are in `mechasheet.js`, which is being cut, and two of them live inside an
SVG), `tests/test_js_template_contract.py` now asserts that every id the static
JavaScript reaches for is either declared in a template or explicitly listed as
JS-owned. Verified against injected drift: renaming `id="wikibody"` in
`wikipage.html` fails the test with a clear message.

Two categories are listed explicitly in that test:
- **JS-owned** — the whole TipTap overlay (`tip-*`) is injected as an HTML
  template literal in `tip-wiki-editor.js`, plus `tooltip-container`,
  `nossi-tooltip-style` and `wiki-tag-validator-init`.
- **Known-missing** — `js-projected-heat`, `js-heat-forecast-bar`,
  `js-heat-forecast-val`, `js-heat-forecast-warning` are referenced by
  `mechasheet.js` but declared by no template. All four are already
  null-guarded, so nothing crashes; the mecha heat-forecast feature is simply
  unwired. Delete this set when mecha is removed.

### 4. The editor tests rested on unexplained blind sleeps ✅
`test_live_link_conversion` had a commented `wait_for_timeout(500)` with no
explanation. It was hiding **two** defects, both fixed at the root:

1. **Validation re-dispatch.** Opening the editor fires a `/tag-validate`
   request per `.tag-dirty` tag. Each settled request re-dispatches a
   transaction to force re-decoration (`tip-wiki-editor.js:328`), which moves
   the caret. `wikiTagValidator === 'ready'` was set when the observer
   *started*, not when validation *finished*, so waiting on it was useless.
   `wiki-tag-validator.js` now exposes a real `validating` → `ready` phase, and
   the tests wait for the unambiguous end state: at least one tag resolved and
   no `.tag-dirty` left.

2. **The click never placed a caret.** The test clicked the geometric centre of
   `.ProseMirror`, which with 12 block children lands in the gap *between*
   blocks — the editor took focus (`ProseMirror-focused`) but the selection
   anchor stayed at offset 0, so typed text went nowhere. It only ever passed by
   luck of layout. It now clicks a real paragraph, which is deterministic (3/3).

This also fixes a genuine UX bug, not just the test: keystrokes typed
immediately after opening the editor were being dropped.

The same anti-pattern existed in six more places — the glitch, clock and
source-mode tests all slept 500–1000 ms waiting for the source textarea to
populate, and one read the textarea's value *before* waiting for it. All of them
now go through `read_source()` / `back_to_wysiwyg()` helpers that wait on the
actual condition. `tests/ui/test_wiki_live_edit.py` now contains **zero**
`wait_for_timeout` calls, and runs 40% faster as a result.

---

## Known debt (deliberately not actioned)

- **Mecha is unfinished and being cut.** `tests/ui/test_mecha_core_features.py`
  was deleted because it asserted on a `FuelConserving` loadout that exists in
  no code path and no DB row. The other ~26 mecha files are untouched, as
  agreed. Two follow-ups for whenever mecha is picked up:
  - `mechasheet.js` reaches for `js-projected-heat`, `js-heat-forecast-bar`,
    `js-heat-forecast-val` and `js-heat-forecast-warning`, none of which any
    template declares. All four are null-guarded so nothing crashes — the heat
    forecast feature is simply unwired. Listed in `KNOWN_MISSING_IDS` in
    `tests/test_js_template_contract.py`; delete that set as the markup lands.
  - `tests/browser_test.py` is a standalone `asyncio` script (pytest collects
    nothing from it) that opens `https://127.0.0.1:5000/sheet/mechtest`, so it
    needs a hand-started dev server. It is the last `:5000` reference in the
    tree.
- **`black` was run over three files nobody had touched** (`views.py`,
  `sheets.py`, `mecha_history.py`) to clear formatting drift from earlier
  commits, as agreed it should be run regularly.
- **`nossinet.egg-info/` is untracked and not gitignored** — a build artifact
  that will get committed by an indiscriminate `git add -A`.

---

## Struck

- **`lightning.js` binds `.editable` handlers only at `window.load`** — the
  premise is wrong. `lightning.js` contains no `.editable` binding; its only
  `dblclick` handler is a capture-phase suppressor at `lightning.js:393`. There
  is nothing to fix here.
- **Phase 2 as an open blocker** — see above; it is done.
