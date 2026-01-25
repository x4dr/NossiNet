# Mecha Sheet POC Implementation Plan (Refined)

This document outlines the steps to enhance the NossiNet mecha sheet into a functional TTRPG support tool, focusing on
state-aware turn management, interactive system booting, and detailed damage tracking.

## Phase 1: Turn Management & Encounter Persistence

**Goal**: Establish a reliable turn-based state machine with non-git-persisted encounter history.

### Step 1: The "Next Turn" Tab & Logic

- **a) Next Turn Tab**: Add a new "NEXT TURN" tab to the mecha sheet.
    - **Content**: Show all pending changes (systems booting, target speed changes, heat adjustments).
    - **Action**: A prominent "NEXT TURN" button that commits these changes.
- **b) Turn Logic**: Implement `/mecha/next_turn/<sheet_id>` to:
    - Increment the `turn` counter in the mecha's "Description".
    - Call `mech.tick_heat()` for dissipation.
    - **Movement**: Calculate speed transition towards the "Target Speed" using the iterative acceleration algorithm.
    - **Systems**: Advance the boot progress of `PoweringUp` systems.
- **c) UI Refresh**: Use HTMX `hx-trigger="turn-updated from:body"` to refresh all dashboard components.

### Step 2: Encounter History & Undo

- **a) Encounter History File**: Create `wiki/backups/mecha_<id>_encounters.json` (not tracked by Git).
    - **Structure**: A list of encounters, each containing a list of turn states (Markdown snapshots + event logs).
    - **Management**: UI to "Start New Encounter" or "Load Past Encounter" (sorted by date/time).
- **b) Restore Point**: Clicking a turn in the history allows "Restore to this point," updating the current mecha state.
- **c) Undo/Redo**: Quick navigation through the current encounter's turn history.

## Phase 2: Interactive Systems & Booting

**Goal**: Implement complex system activation with roll-based breakpoints.

### Step 1: System Booting State Machine

- **a) Boot Stats**: Update the `System` class to support per-system boot configurations:
    - `activation_rounds`: Base time to activate.
    - `breakpoints`: Success thresholds (e.g., [5, 8, 13]) that accelerate booting or unlock features.
- **b) Booting UI**:
    - Show a "Booting..." progress bar on the system card.
    - **Roll Input**: A field to enter the IRL roll result at any point during the boot sequence.
    - **Blocking**: If a roll is required for the next stage of booting, the "Next Turn" logic should pause that
      system's progress until the result is input.
- **c) System Wiki Integration**:
    - Create a standard "System Library" in the wiki.
    - Allow loading system stats from arbitrary wiki pages to support "custom/modified" gear.

### Step 2: Heat & Energy Projection

- **a) Projected Heat**: The Heat UI shows "Current" vs. "Projected" (next turn) flux.
- **b) Manual Overrides**: A "Manual Heat" input for external environmental factors or specific attacks.

## Phase 3: Damage & Malfunctions

**Goal**: Track sector-based damage and its impact on character actions.

### Step 1: Damage Overview & Entry

- **a) Overview Tab**: A new tab showing a map of all sectors (Front, Rear, etc.).
- **b) Penalty Summary**: List all common actions (e.g., "Attack", "Dodge", "Sensor Scan") and the total Penalty Dice
  applied from malfunctions in relevant sectors.
- **c) Damage Modal**:
    - Add/Remove damage points.
    - Select standard malfunctions from a wiki-loaded list.
    - Custom text input for unique damage effects.

### Step 2: Visual Feedback

- **a) System Cards**: Add "Damaged" overlays or warning icons if a system's sector is compromised.
- **b) Detail Pages**: `/mecha/<id>/system/<name>` for a full history of damage and specific rules for that component.

## Phase 4: Timeline & Narrative Log

**Goal**: Provide a vertical log of the encounter.

### Step 1: Vertical Timeline

- **a) Timeline View**: A vertical list of events (Turn Start, System Booted, Damage Taken, etc.) with timestamps.
- **b) Event Logging**: Automatically capture all state transitions and user inputs (like roll results).

## Phase 5: Rule Alignment & Refinement

**Goal**: Sync the wiki rules with the code's "Source of Truth".

### Step 1: Movement Algorithm Documentation

- **a) Wiki Update**: Describe the iterative acceleration algorithm in `wiki/endworld/mecha/systems/movement.md` in a
  way that is understandable for TTRPG players (e.g., "Each round, the mecha gains X speed until it reaches Y...").
- **b) Code Pinning**: Implement unit tests for `Mecha.speeds()` to ensure the algorithm remains consistent during
  refactoring.

### Step 2: Malfunction Standardization

- **a) Wiki Update**: Standardize the mechanical impact of malfunctions in `wiki/endworld/combat.md`.

## Phase 6: Encounter-Based Persistence & Replay
**Goal**: Shift the source of truth for ephemeral data (heat, speed, turn count) to the encounter log and implement a delta-based replay system.

### Step 1: Decouple Ephemeral State from Markdown
- **a) Clean Markdown**: Modify `Mecha.py` to stop writing `Flux Pool`, `Current Speed`, `Target Speed`, and `Turn` into the Markdown `Description` table.
- **b) Base Configuration**: The Markdown file will now serve as the "Base Sheet," containing only permanent data like installed systems, sectors, and permanent damage/malfunctions.

### Step 2: Delta-Based Encounter Log
- **a) Log Structure**: Update `wiki/backups/mecha_<id>_encounters.json` to store a sequence of **Events** and **Turn Commits**.
- **b) Event Types**:
    - `SYSTEM_TOGGLE`: `{ "name": "Reactor", "state": "active" }`
    - `HEAT_ASSIGNMENT`: `{ "system": "Sink", "amount": 10, "reason": "Manual assignment" }`
    - `SPEED_TARGET`: `{ "value": 50 }`
    - `TURN_COMMIT`: `{ "turn": 5, "summary": { ... } }`
- **c) Replay Engine**: Implement a `Mecha.replay(events)` method that takes a list of events and applies them to a base Mecha instance to reconstitute the current state. This ensures the "Combat Log" is the definitive history.

### Step 3: Session-Based "Pending" Changes
- **a) Flask Session Storage**: Store uncommitted UI changes (current slider positions, pending toggles) in the Flask `session`.
- **b) Persistence**: These changes persist across page refreshes but are **cleared** when a turn is committed or a new encounter starts.
- **c) Session Size Management**: Research and ensure the session cookie (typically 4KB) can handle the pending state. If the state grows too large, implement a server-side session or a temporary `.tmp/pending_<id>.json` file.

### Step 4: Encounter Management UI
- **a) New Encounter Button**: Add a "START NEW ENCOUNTER" button to the Timeline tab. This clears the current encounter pointer and starts a fresh log.
- **b) Automatic Initialization**: If no encounter exists for a mecha, automatically create an empty one on page load.
- **c) Reset to Here**: Re-implement "Reset to here" by truncating the event log to the selected turn and replaying from the base sheet.

### Step 5: Refined UI Interactions
- **a) Slider Logic**: Sliders generate "Pending" heat assignments in the session.
- **b) Next Turn Summary**: The "Next Turn" tab displays all "Pending" events from the session that will be committed to the log upon clicking "COMMIT".

---

## Technical Solutions

- **Persistence**: `pathlib` for backup directories, `json` for encounter history.
- **HTMX**: Event-based triggers for cross-component updates.
- **State Management**: The mecha's Markdown remains the primary state, with the JSON history providing the "
  time-travel" capability.
