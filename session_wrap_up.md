# Session Wrap-Up

## How I Learned to Work With You (Crucial Context)

- **Wiki rules are sacrosanct**: Never modify rules pages (`wiki/endworld/`) without explicit permission. Only formatting when specifically asked. The user was visibly annoyed when I added a rounding rule to heat.md without asking.
- **"In your style"** means: direct, brief, tables, bullet points, minimal preamble, no UI language, technical but conversational. Read `combat.md` or `mecha.md` for the tone. In-character = the Quaesitor narrator in `intro.md`.
- **No em dashes**. Use `-` instead. The user specifically pointed out AI rewriting inserted them everywhere and they had to manually clean up.
- **No "System" prefix** or "flickers" in effect descriptions. Use: Damaged/Disabled/Destroyed. Keep it punchy.
- **Avoid UI/web language in wiki rules**: No "hover", "click", "UI", "preset", "config", "named preset", "default". Rules are for a TTRPG played on paper with dice. The UI is a separate layer.
- **No editorializing about frequency**: Don't say "common", "rare", "usually", "typically" unless the rules themselves say so. The user said the rules "don't care and I don't have enough data to be definitive."
- **Test data is fake/shorthand**: testmecha.md values are unbalanced and provisional. The user called them "dumb numbers" and told me to just fix them for testing purposes.
- **Check before changing rules content** but be proactive about code/UI. If it's a Python bug or a CSS issue, just fix it. If it's a rule interpretation, ask first.
- **No sidequests**: Don't add extra features the user didn't ask for. If I spot an issue, flag it in a todo but don't implement it without approval.
- **The user is quick to correct** and has strong opinions about visual design. When they say something doesn't work, listen to the *what* not the *how* -- they usually know the right direction.
- **No inline CSS unless absolutely necessary** (dynamic values like widths/offsets). Everything else belongs in CSS classes.
- **Never add rounding rules or other general mechanics to the wiki without asking.** The user considers this "changing the rules" and it requires specific consent.

## What We Did This Session (In Detail)

### Phase 1: Understanding the Mess
Started with the user unhappy about the mecha UI. They said it was vibe-coded, clunky, didn't model the game flow. I explored both the codebase (old mechasheet.html, 1012-line mecha.css, 713-line mechasheet.js) and the Endworld wiki rules (28 files across endworld/). We established:
- The UI doesn't work because the rules were half-baked and the UI was built on vibes
- We needed to establish the game flow first, then rebuild the UI around it
- The user wanted me to understand both the rules AND the UI, then help design both

### Phase 2: Rules Deep-Dive
We spent a lot of session time on rules:
- **Combat flow**: attack → defense → shields → armor → sector damage. Defined targeting as "pick facing sector, called shots for shifts, resonance moves it" (Option A). Established rising-water damage model with Damaged/Disabled/Destroyed thresholds.
- **Heat flux**: Corrected my misunderstanding multiple times. No "throughput limit" — just a pool with max. Fill first, then empty, then dissipate. Player chooses transfers. Same Total Flux cap applies to both inbound and outbound sequentially.
- **Energy/Power**: Static supply-vs-demand, not per-turn. Loadouts are just priority-ordered lists with budget brackets. Fuel consumed in bulk at activation for a time period.
- **Weapons**: Defined stat block (damage, range, ammo, energy, heat, boot, modes, type, keywords). Three weapon types with different resource profiles. Lasers = constant draw + burst heat, Ballistics = ammo + moderate heat, Missiles = expensive ammo + low heat.
- **Repair**: Thresholds [5,9,13] by tech level. Quirks on field repairs. 10 example quirks using Reinterpret triggers.
- **Reinterpret**: New mechanic for re-reading rolls with different selectors. Used for quirk triggers, malfunction checks.

### Phase 3: UI Architecture (MechaUI2 branch)
Replaced the old tab-based layout with:
- **Sidebar** (collapsible 48px → 200px on hover): Overview, Movement, Power, Thermal, Combat, Support
- **Overview dashboard**: Speed display, dual power bars (generation + consumption), heat overview (gen/cooling/saturation), systems count, pending changes list
- **Domain views**: Each category has its own page with system cards loaded via HTMX
- **Floating pending-changes badge**: Shows change count, click to go to Overview
- **Sticky footer**: Manual heat input + Commit Turn button
- **Old UI archived** to `NossiSite/obsolete/` for reference

### Phase 4: Visual Polish (The Long Tail)
- Fixed flux values in test data (Vent=5, Coolant=10, Sink=1 → 16 total)
- Made heat bars use accent-color (blue #1070a0)
- Added per-system heat bars with mini fill levels
- Rewrote CSS three times: first with wrong variables, then with proper theme variables, then to fix the meter hover/label behavior
- Added `.meter-wrap` to reserve space for expanded bars, preventing layout shifts
- Centered bars with flexbox, hover expands from center with scaleY, then switched to height-change-in-wrapper approach
- Power bar: generation bar shows reactors by state (green active, dim available, red disabled), consumption bar shows systems within budget
- Fixed `energy_allocation()` to multiply by amount and only return systems that fit budget
- Fixed `projected_cooling()` to cap at stored heat

### Phase 5: Physics Engine (Cyber-Labels)
The old mechasheet.js has a physics engine for floating labels on the power/heat bars. It was janky:
- Added bounding-box overlap collision detection (was just center-based repulsion)
- Reduced mouse repulsion force (5000→2000) to prevent oscillation
- Tuned damping (0.55), attraction (0.008), and overlap threshold (3px)
- Labels still jiggle when caught between mouse and another label

### Phase 6: Python Backend Cleanup
- Deleted dead code: `heatflux`, `thermal`, `flux_used` fields (set but never read)
- Implemented overdrive on EnergySystem (parse "50/150" style values)
- Fixed `energy_allocation()` to use `energy * amount` for cost calculation
- Fixed `energy_allocation()` to only return systems that fit in budget
- Added `generated_heat()` to EnergySystem for overdrive heat values
- Added `mode=overview` parameter to heat_ui route

## Current UI State (What It Looks Like)

### Overview Page
```
[Sidebar (48px)]  |  [Status Bar: SPEED | POWER | FLUX | TURN]
                   |  [Overview title]
                   |  +------------------+------------------+
                   |  | Speed            | Heat (HTMX)      |
                   |  | XX.X km/h        | [gen bar]        |
                   |  | Target: XX.X     | [cool bar]       |
                   |  |                  | [sat bar]        |
                   |  +------------------+ Forecast/Pool    |
                   |  | Power (HTMX)     +------------------+
                   |  | [GEN bar]        | Systems          |
                   |  | [CON bar]        | cat counts       |
                   |  +------------------+------------------+
                   |  | Pending Changes                    |
                   |  +------------------------------------+
[Footer: Manual Heat ___ SET]            [COMMIT TURN]
```

### Sidebar Items (Hover-Expand)
Each shows compact info in sidebar + hover popup:
- Overview: speed/flux/budget summary
- Movement: current/target speed
- Power: output/demand
- Thermal: fluxpool/baseload/cooling
- Combat: weapon count
- Support: system count

### Domain Views
Each domain page loads system cards via HTMX. System cards have toggle/cycle/boot controls. The Thermal and Power tabs have full interactive meters with assign controls and cyber-labels.

## What's Still Broken / Glitchy

### UI Polish
- **Cyber-labels on heat bar** still jitter when pushed by mouse into another label (physics needs more damping tuning)
- **Heat bar labels** overlap each other horizontally when there are many segments (need smarter label placement or text truncation)
- **Energy bar container width** (`--max` currently 100%) — the old version constrained the bar width to show budget vs total proportion. Currently both generation and consumption bars are full width. The user mentioned it "should be wider" then said no, it was fine.
- **Overview Systems card** is still basic (just category counts). The user never gave feedback on what it should show.
- **No responsive design** — everything assumes desktop width
- **No mobile layout** — phones will break entirely
- **No loading states** for HTMX fragments — the placeholder text flashes briefly
- **The classic/old system card CSS** was ported over from the old mecha.css but hasn't been visually verified. Some system card styles might look off.

### Heat Bar (Next Steps)
The user mentioned wanting to tackle the heat management UI next. The planned design:
- Modal opens for heat management
- **Gather phase**: Sliders on fluxpool and systems carrying heat. Drag system slider down = transfers to pool. Drag pool slider = equally pushes/pulls from all systems. Can't push over initial value. Sum invariant. Transfer All button.
- **Disperse phase**: Sliders on pool and sinks. Disperse All fills highest projected dissipation in order.
- **Auto checkbox**: Available only if Transfer All can be clicked in both phases.

### Python Backend
- `next_turn()` heat model doesn't match wiki (uses separate inbound/outbound flux budgets instead of single pool fill-then-empty)
- `next_turn()` doesn't advance boot progress
- No overheat check implementation
- No damage/sector system in code
- No weapon firing (burst heat)

## Detailed Future Work / TODOs

### Immediate UI Next Steps (Heat Management)
- Build the heat gather/disperse modal with sliders
- "Gather" phase: system sliders → fluxpool, pool slider → evenly distributes
- "Disperse" phase: pool → sinks, with auto-fill by highest dissipation
- Automate checkbox when Transfer All is possible in both phases
- Only integer amounts (no fractional heat)

### Short Term
- Fix 2 pre-existing test failures (next_turn return key mismatch, boot progress not advancing)
- Rewrite mechasheet.js pending changes system for new layout
- Move overview "Systems" card to show meaningful data (maybe active vs total system counts)
- System detail page: replace raw `to_dict()` dump with a proper read-only view
- Action Penalties section in combat view (currently placeholder in old UI)

### Medium Term
- Weapon fire mechanism: `fire()` on OffensiveSystem generating burst heat, consuming ammo
- Overheat notification: basic notes field, tell player if overheating, GM adjudicates
- Shield/armor display (read-only, all rolling IRL)
- Combat view: weapon cards with fire button, damage marking per sector
- Fuel consumption logging per encounter
- Sector damage UI: click sector to mark damage, accumulate, show thresholds
- Character-to-mecha stat display (pilot Focus/Discipline/Affinity inline)

### Rules (Wiki) TODOs
- `offensive.md` Keywords table needs filling out (Armor Piercing, Blast, Rapid Fire, Overcharge mechanics)
- `offensive.md` Bonus Rules section needs content
- `support.md` needs expansion beyond just seals
- `mecha/computers.md` and `mecha/systems/computers.md` need deduplication
- Multi-action / multi-roll per turn rules need formalizing
- Ammo type selector rules (future: "find X kg of shield-piercing EMP ammo")

### Technical Debt
- `mechasheet.js` is 713 lines of old tab-layout code. Needs clean rewrite for new layout.
- System cards are loaded via HTMX from individual endpoints — this works but creates many round trips on page load
- `next_turn()` heat model is wrong per wiki (auto processes both phases instead of player-choice)
- `energy_allocation()` and `energy_demand()` use different formula patterns (amount multiplier)
- CSS still has some inline styles in HTMX templates that should be classes
- HeatSystem.flux_used is set but never consumed by any Mecha method (dead field on HeatSystem, alive but unused)

## Key Design Decisions Made This Session

1. **Sidebar + content + modals** — not tabs, not pure accordion. Sidebar collapses to 48px.
2. **Any-order decisions** — no mandatory sequence. Player manages their own flow.
3. **Power as static supply/demand** — no per-turn tracking. Recalculated when something toggles.
4. **Heat flux as fill-then-empty** — single pool, 3 phases (Inbound/Outbound/Dissipation). Player chooses transfers.
5. **Rising-water sector damage** — accumulated damage per sector, Damaged/Disabled/Destroyed thresholds.
6. **Higher tech = more fragile** — Experimental has lowest damage thresholds (5/12/25), Base most rugged (12/25/50).
7. **Two-meter power visualization** — generation bar (reactors by state) + consumption bar (draw within budget).
8. **Reinterpret** — re-reading a roll with different selectors for quirk/malfunction triggers.
9. **Numbers rounded down** — general rule in ewrules.md.
10. **Disabled heat systems contribute 0 flux** — clarified in heat.md.
11. **Heat is integers** — no fractional heat in UI. `"%.0f"|format` and `|int` for display.
12. **Weapons are data objects for now** — no fire/ammo/damage pipeline yet. Display only.
13. **Dynamics=0 drag formula** — `100 * Speed²` (matches Python code).

## Branch Info
- **Branch**: `MechaUI2` (checkout to resume work)
- **Position**: 1 commit ahead of master
- **GamePack submodule**: modified (OffensiveSystem, Mecha, EnergySystem, HeatSystem changes)
- **Untracked files to stage**: MECHA_DESIGN.md, AGENT_RULES_INSIGHTS.md, session_wrap_up.md, NossiSite/obsolete/, heat_ui_overview.html
- **Modified to commit**: sheets.py, mecha.css, mechasheet.js, mechasheet.html, bar.html, testmecha.md
