# Mecha Sheet POC Implementation Log

## Session: 2026-01-24
**Objective**: Initialize Phase 1 (Turn Management & Encounter Persistence).

### Decisions & Architecture
- **Encounter History**: Stored in `wiki/backups/mecha_<id>_encounters.json`. This file is excluded from Git to keep the repository clean and avoid noise from transitive session data.
- **State Persistence**: 
    - **Transitive data** (boot progress, turn-specific events) goes into the JSON encounter log.
    - **Permanent data** (damage, turn counter in description) is written back to the mecha's Markdown file.
- **Turn Lifecycle**: The "Next Turn" button commits pending changes from the "Next Turn" tab and triggers resource dissipation/updates.

### Progress
- [x] Create `implementation_log.md` (This file)
- [x] Implement Encounter History manager (Python)
- [x] Add "Next Turn" tab to UI
- [x] Implement `/next_turn` endpoint
- [x] Fix `HeatSystem` property error (added setter for `flux`)
- [x] Verify `mechtest` page loads correctly
- [x] Add unit tests for Phase 1 components (`tests/test_mecha_poc.py`)
- [x] Refine "Next Turn" button style (CSS class, variables, better contrast)
- [x] Fix "Next Turn" button functionality (CSRF headers, 204 response)
- [x] Remove intrusive `hx-confirm` alert
- [x] Implement System Booting state machine (activation rounds, breakpoints)
- [x] Add Booting UI (progress bars, roll input, clickable breakpoints)
- [x] Implement Heat Projection (Current vs. Projected flux)
- [x] Add Manual Heat Override (Pending heat in Next Turn tab)
- [x] Document Movement Algorithm in Wiki (`wiki/endworld/mecha/systems/movement.md`)
- [x] Refine Speed & Duration Rules of Thumb (Verified with 100+ test cases)
- [x] Standardize Malfunctions in Wiki (`wiki/endworld/combat.md`)
- [x] Add Speed Pinning Unit Test (`tests/test_mecha_poc.py`)
- [x] Fix UI Layout (All view panels now inside `main-screen`)
- [x] Fix CSRF in "Add Sector" form
- [x] Implement Heat Sliders (Storage-based assignment with flux limits)
- [x] Correct Heat Logic (Systems store up to `capacity`, provide `flux` to mech)
- [x] Revert and Improve Speed Graph (Added endpoint, fixed scaling, added end-of-turn extension)
- [x] Move Undo/Redo to Timeline and add "Reset to here" functionality
- [x] Audit and fix 404/500 errors in mecha sheet routes
- [x] Fix Heat Persistence (Unassigned heat now accumulates in `fluxpool`)
- [x] Implement Heat Overage Penalties (Logged in timeline)
- [x] Fix Speed Transition (Current speed now correctly updates towards target)
- [x] Refine Speed Slider UI (Fixed max value and starting position)
- [x] Improve Heat Slider Ergonomics (Added delay to triggers, fixed assignment logic)
- [x] Enhance Encounter Logging (Detailed entries for heat, speed, and system booting)

## Phase 6 Summary (Completed)
- **Non-Destructive Playback**: Switched from log truncation to a "playback pointer" model. Users can jump between turns without losing future data (until they commit a new turn from the past).
- **Session-Based Delta Engine**: UI interactions (sliders, toggles) create pending events in the session, allowing robust Undo before turn commitment.
- **Persistence Layer**: Encounter logs are now stored in individual timestamped files in `wiki/encounters/` with support for custom naming.
- **Granular HTMX UI**: Refactored the dashboard to use specific HTML fragments for partial updates, preventing full page reloads during common interactions.
- **Standardized Architecture**: Fixed routing mismatches and ensured all mecha-related endpoints follow consistent parameter naming conventions.
- **Base Sheet Calibration**: Modified `/home/maric/wiki/mechtest.md` to include active cooling systems and heat-generating support systems for reliable testing.
- **Project Structure**: Removed redundant `wiki/` directory in the project root.
- **Verification**: Implemented a comprehensive Playwright test suite (`tests/ui/test_mecha_phase6.py` and `tests/ui/test_mecha_heat_ui.py`) covering all Phase 6 features.

## Potential Improvements (Future)
- **Re-write History Warning**: Show a confirmation dialog if committing from a past turn (as it truncates the Redo stack).
- **Undo Log Support**: Extend the UNDO button to pop committed events from the log if no pending changes exist.
- **Encounter Export**: Option to archive encounter logs into the wiki permanent history as Markdown tables.
- **Graph Optimization**: Transition the speed graph to a more lightweight partial update (currently reloads full SVG).

## Phase 2 Summary
- **Interactive Booting**: Systems now take time to power up. The UI shows progress and allows entering roll results to satisfy breakpoints or advance booting.
- **Resource Projection**: Players can see how their heat flux will change in the next turn based on booting systems.
- **Manual Overrides**: Added a way to queue manual heat adjustments for the next turn.

## Phase 1 Summary
- **Turn Management**: The mecha sheet now has a "Next Turn" tab. Clicking "COMMIT & START TURN" increments the turn counter, ticks heat, and logs the state to a JSON encounter file.
- **Persistence**: Permanent changes (turn counter) are saved to the mecha's Markdown. Transitive state (turn history) is saved to `wiki/backups/mecha_<id>_encounters.json`.

## Next Steps: Phase 2
- **System Booting**: Implement the state machine for systems that take multiple rounds to activate.
- **Roll Integration**: Add UI for entering IRL roll results during the boot sequence.
