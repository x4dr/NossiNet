# Mecha UI Design Document

## Design Philosophy

The Mecha UI is a companion for live TTRPG play at the table. Players use it on laptops (phones eventually) to manage their mecha during sessions. The system is mid-crunch — detailed enough for tactical decisions but leaning toward rules-light where possible.

### Design Values
- **Any-order interaction**: Players adjust speed, toggle systems, assign heat, declare combat actions in whatever order makes sense for the moment.
- **Steady-state automation**: If nothing interesting is happening, the UI stays quiet. No forced clicks.
- **Pending-first**: All changes are ephemeral until committed. The player previews their intended turn, then commits.
- **Time travel**: Every action is logged. Players can undo/redo/replay history to explore "what if" scenarios or correct mistakes.
- **Wiki-integrated**: Every system card can open its rules definition from the wiki.
- **State is authoritative on the backend**: Client shows optimistic/preview state; backend validates and provides ground truth.

## Information Architecture

### Layout
- **Narrow sidebar** (always visible): Decision domains, each with a compact status indicator. Hover expands for more info.
- **Main content area**: Shows the selected domain's controls/information.
- **Modals**: Complex interactions (heat sink fine-tuning, weapon targeting) open as overlays.

### Sidebar Categories
1. **Overview** (default) — Speed graph, key vitals (fluxpool, energy balance, system health), pending changes summary.
2. **Movement** — Target speed, movement system status/cards, position.
3. **Power** — Energy allocation, reactor management, fuel tracking.
4. **Thermal** — Heat generation, fluxpool, sink assignment, dissipation.
5. **Combat** — Weapons, shields, damage, boni/penalties, heat signature.
6. **Support** — Bonus systems (scanners, coolant dump, food processors, computers) — not touched every turn.

Each category groups related systems. System toggle/boot/status lives within its domain (toggle weapons in Combat, toggle movement in Movement). Sector damage shown as a floating mini-map or always-visible panel.

### Sidebar Item Behavior
- Shows a compact status summary (e.g., "45/120 km/h" for Movement, "34/50 flux" for Thermal).
- Hover/tap expands to show richer summary.
- Color/badge indicates: ⬤ Grey = steady state / no pending changes, 💛 Yellow = has pending uncommitted changes, 🔴 Red = needs attention.

## Interaction Model

### Turn Flow
1. Player sees **Overview** with current mecha state (committed from last turn).
2. Player navigates to any domain in any order, makes changes.
3. All changes accumulate in a **Pending Actions** list — visible in Overview and as a per-domain counter.
4. Player can undo individual pending changes at any time.
5. Player hits **Commit Turn** — all pending actions are serialized and sent to the server via JSON POST.
6. Server validates, applies events, advances turn, returns new state.
7. UI refreshes to committed state.

### State Layers
- **Client (ephemeral)**: `window.mechaState.pending` — all uncommitted changes. UI renders optimistically from this.
- **Server (authoritative)**: Events replay + `next_turn()` in Python. Returns validated state.
- **Encounter file**: Persistent log of all committed events, enabling time travel and replay.

### Pending Changes
- Speed target changes
- System toggles
- Heat assignments
- Loadout changes
- Combat action declarations
- Manual heat overrides

### Commit
- Sends full pending state as JSON to `/mecha_commit_turn/<id>`.
- Server validates: heat assignments don't exceed capacity, energy budget isn't exceeded, etc.
- Server calls `next_turn()`, logs all events to encounter file.
- Returns validated turn result, client reloads.

## Combat View
- Shows weapon cards with stats (damage, range, ammo, heat, handling, attack modes).
- Shows shield/armor configuration per sector.
- Attack declaration: select weapon, target sector, attack mode.
- Heat signature display (fluxpool + projected).
- Boni/penalties from malfunctions, terrain, pilot skills.
- Resolution happens on paper/dice; UI tracks state and modifiers.

### Weapon Data Model (OffensiveSystem)
Weapons are `OffensiveSystem` objects with these fields:

| Field | Type | Description |
|-------|------|-------------|
| Damage | float | Base damage on a successful hit (single number) |
| Range | str | "Min/Opt/Drop" in meters |
| Ammo | str | "kg techlevel" per shot; "-" for energy/melee |
| Energy | float | Power draw while system is active (turned on) |
| Heat | str | Burst heat from firing (in heats dict) |
| Handling | float | Bonus/penalty dice to attack roll |
| Modes | str | Attack modes: D/I/S/B |
| Type | str | Laser / Ballistic / Missile / Melee |

**Ammo system**: Ammo is tracked as kg of a tech level consumed per shot. Ammo is stored in cargo and autoloaded. Reload is not an action (unless specified otherwise). Manual tracking for now, with a future ammo-type selector planned.

**Weapon types**:
- **Lasers**: High constant energy draw when active, no ammo, high heat (constant + burst). Heat is the "ammo" — the limiter is cooling capacity.
- **Ballistics**: Low/no energy draw (autoloader/electric trigger), uses ammo, moderate heat per shot.
- **Missiles**: Low energy (guidance/tracking), expensive ammo, low heat.
- **Melee**: No energy, no ammo, no heat. Damage scales with mech size/momentum.

**Power model**: A system (including weapons) draws its rated Energy every turn it is active/on. There is no power accumulation — it's a supply vs demand system. If total demand exceeds supply, some systems must be deactivated. Capacitors (future) could change this.

## Key Design Decisions
1. **Sidebar + content area + modals** — not tabs, not pure accordion.
2. **Any-order decisions** — no mandatory sequence. Player manages their own flow.
3. **Separate Combat and Support domains** — Combat is tactical core, Support is utility/niche.
4. **Duplicate classic UI to /obsolete/**, build fresh on new branch `MechaUI2`.
5. **System rules popup** — each system card links to its wiki page or inline rules.
6. **Client-side preview** — changes render instantly; no round-trip until commit.
7. **Pilot stats displayed inline** — relevant character attributes (Focus, Discipline, Intuition, skills) shown where they matter (e.g., Focus next to weapon cards).
8. **Pending changes badge** — floating badge/banner (sticky header bar) showing pending count, click to expand full list.

## Implementation Status

### Done
- **MECHA_DESIGN.md** created with design philosophy, info architecture, interaction model.
- **Wiki: `mecha/systems/offensive.md`** written with full mecha weapon rules, stat block, example weapons, attack modes.
- **Python: `OffensiveSystem` class** created with weapon-specific fields (damage, range, ammo, handling, modes, type).
- **Python: `Mecha.py`** updated to use `OffensiveSystem` for the Offensive category.
- **Pre-existing test failures**: 2 tests in `test_mecha_poc.py` fail due to `next_turn()` return dict key mismatch and missing boot_progress advancement — not caused by these changes.

### Next Steps
- Move classic UI to `/obsolete/` and create `MechaUI2` branch.
- Build the new UI layout (HTML skeleton: sidebar + content + modals).
- Build the Overview page (speed graph, key vitals, pending summary).
- Build individual domain pages (Movement, Power, Thermal, Combat, Support).
- Implement the pending changes system (badge + expanded list).
- Rebuild the status bar.
- Port the speed graph to the new layout.
- Test with `testmecha.md` data.

## Open Design Questions (Updated)
- How do support systems interact with the UI? (Some are passive/no interaction needed.)
- What's the character-to-mecha stat conversion formula? (Needed for pilot stats display.)
- How does steady-state detection work technically?
- What does the Sector Damage mini-map look like?
- Mobile responsive strategy?
- Ammo type selector UI (future).
