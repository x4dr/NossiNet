# Endworld Rules - Agent Context

Deep understanding of the Endworld mecha system for resuming work after context loss. This captures rules nuances, design intent, and decisions that aren't obvious from reading the wiki files alone.

## Core Resolution (Selector System)

- A Check rolls 5d10, sorted ascending.
- Each selector picks a die by position (1 = lowest, 5 = highest). Default 2 selectors.
- Standard: Attribute + Skill. Situational third selector possible (Tactics, FCS, Cortex Drive).
- Selectors >5 pick the 5th die. Selectors ≤0 pick nothing.
- Result is sum of selected dice, compared against thresholds like [3,7,17].
- **Bonus/Penalty Dice**: cancel each other, then add extra dice and remove lowest/highest.
- **Resonance**: matching dice. Amplitude = matches past the first. Frequency = the number shown.
  - Only matters when an effect specifically references it.
  - Used in targeting (shifts hit location by resonance amplitude).
- **Reinterpret**: take an existing roll and re-read it with different selectors. Syntax: "Reinterpret Affinity ≤ 5". Used for quirks, malfunction triggers.
- Cortex Drive adds a third selector. Self-damage on resonance (wound severity = amplitude).

## Combat Flow

### Attack
- Attribute depends on action type: Focus for mech ranged weapons, Discipline for piloting. Skill depends on approach.
- Roll produces Attack Value. Range modifies: penalty dice below min, free within opt, -1 per drop interval past opt.
- Defense subtracted. Sources: dodge (active roll, takes action), cover (positional, stays until flanked), deflectors (flat bonus). Usually not both dodge and cover. Deflectors add flat 1-5 to defense.
- If still positive: hit.

### Targeting
1. Pick a targetable facing sector. GM decides availability by positioning (Front if face-to-face, Rear if flanked).
2. Called shots shift the hit pre-roll: 1 malus die per shift. Max 4 shifts (before hitting 5 malus dice).
3. After the roll, the attack roll's OWN resonance shifts the hit:
   - Defender shifts: total amplitude of frequencies 1-5 (push toward less critical sector)
   - Attacker shifts: total amplitude of frequencies 6-10 (pull toward desired sector)
   - Each shift moves one sector along the mech's adjacency diagram. Empty neighbor = miss.
4. Defender's defense roll may also influence positioning (GM discretion).

### Damage (Rising Water Model)
- Each sector tracks **accumulated damage** -- a single number that climbs as hits land.
- Each system in the sector has three thresholds: **Damaged** / **Disabled** / **Destroyed**.
- Higher tech = more fragile (Experimental: 5/12/25, Base: 12/25/50). Compact high performance = less room for punishment.
- When accumulated damage crosses a threshold, all systems at or below it trigger their effect.
- Damage flow: shields activate first -> armor reduces remaining -> remaining adds to sector accumulated damage.
- **Malfunctions** picked by GM when Disabled: Sensor Glitch (+1 PD perception/targeting), Actuator Jam (+1 PD movement/melee/dodge), Power Leak (+10% energy cost), Circuits Frying (+2 heat/turn), FCS Error (+1 PD ranged attacks), Structural Weakness (extra damage from hits).

### Sectors
- Number determined by mech size class. 1/3 (rounded up) must be "facing" sectors.
- Facing sectors are directly targetable (Front, Rear, Left, Right -- whatever the mech design says).
- Internal sectors (Head, Torso, Limbs) can only be hit via resonance shifts or called shots.
- Sector adjacency diagram is defined during mech construction. Each mech has its own layout.

## Energy & Loadouts

- **Supply vs demand**: Reactors produce a budget. Active systems deduct from it. System cannot be turned on if it would bring budget below 0.
- **Static until changed**: No per-turn tracking. Recalculated when something toggles, gets damaged, runs out of fuel, or gets a quirk.
- **Fuel**: Consumed in bulk at activation for a time period ("1 ton coal/hour" = consume 1 ton, runs 1 hour). Some systems consume per turn in combat (overdrive).
- **Loadouts**: The order in which systems are turned on, with budget brackets as breakpoints. Not a separate mechanic -- just a written-down sequence.
  - Brackets are all unique sums of active reactor outputs.
  - Example: `[0], WeaponPod, ShieldGrid, [30], Sensors, [60], ActiveVents, [90]`
  - At budget 30: WeaponPod + ShieldGrid active. At 60: Sensors also. Past 90: nothing more to activate.

## Heat (Flux Loop)

- Single **fluxpool** per mech. Max capacity = Total Flux (sum of active coolant systems).
- Three-phase turn sequence:
  1. **Inbound**: Player pulls heat from active systems into pool. Pool fills until max or no more heat. Residual heat stays in generating system -> possible Overheat Check.
  2. **Outbound**: Player pushes heat from pool into heat systems (sinks, vents). Only systems with heat capacity can receive. Pool empties until 0 or no more capacity.
  3. **Dissipation**: Each heat system processes its own stored heat (vents actively dump, sinks passively bleed).
- The fill-then-empty sequence naturally limits throughput to pool_max per direction per turn. There is NO separate throughput cap -- just pool size + ordering.
- Overheat Check: 2d10 + Affinity - Residual Heat. Check result against table: 11+ (penalty die), 8-10 (-1 actions), 5-7 (shutdown 1 turn), 3-4 (damage), 1-2 (destroyed).
- Pool full >1 turn: speed halved, computers crash, reactor auto-scram.
- Reactor shutoff delay: reactors keep generating baseload heat for X turns after deactivation.

## Mecha Weapons

- Lasers: high constant energy draw when active + burst heat on fire. No ammo. Heat is the ammo.
- Ballistics: low/no energy draw. Uses ammo (kg + tech level). Moderate heat. Auto-loads from cargo.
- Missiles: low energy draw. Expensive ammo. Very low heat.
- Melee: no energy, no ammo, no heat. Scales with size/momentum.
- Weapons table needs expansion (Keywords section has TODO, Bonus Rules has TODO).

## Repair & Quirks

- Default repair thresholds [5,9,13] modified by tech level (Experimental hardest).
- Below first: no effect. First: functions but gains a quirk. Second: fully functional, optional quirk. Third: flawless.
- Facility overhaul clears all damage and quirks.
- Quirks use **Reinterpret** for triggers. Named (for UI hover tags). GM picks from table or invents.
- Quirks ideas: Feedback Loop, Flicker, Overeager, Ghost Reading, Slow Reset, Intermittent, Hot Run, Resonant Chatter, Ammo Hungry, Unstable Output.

## Movement

- Iterative speed calculation (0.1s timesteps) using Thrust, Anchor (friction), Dynamics (drag), Mass.
- Rule-of-thumb formulas available for quick reference.
- Speed graph in UI shows projected speed curves across turns.

## Character-to-Mecha

- Not implemented in UI yet. Mecha shows its own bonuses/quirks; players and GM adjudicate applicability.
- Connections (for future): Focus -> Ranged Mech Weapons (attacks). Discipline -> Piloting Practice (maneuvering). Affinity -> overheat checks + tech gating. Cortex Drive -> third selector with self-damage.
- Skills are situational -- the player describes their approach and the GM picks appropriate attribute+skill pairings.

## Open TODOs & Future Work

### Rules
- `offensive.md` Keywords section is a placeholder TODO.
- `offensive.md` Bonus Rules section is a placeholder TODO.
- `support.md` needs expansion (currently just seals + computers link -- deferred to later session).
- Multi-action / multi-roll per turn needs formalizing (can a pilot shoot AND dodge? shoot AND reconfigure shield? Not all 3 without perks -- needs brainstorming).
- Ammo type selector (future: find X kg of shield-piercing EMP ammo, swap ammo types).
- Steady-state detection for heat/energy: when does the UI auto-mark a domain as "no changes needed"?

### Future UI Work (see MECHA_DESIGN.md for full design)
- Sector damage mini-map visual design.
- Mobile responsive strategy.
- Character-to-mecha stat display (deferred -- mecha shows own bonuses, players/GM adjudicate).

### Python Code
- `next_turn()` doesn't correctly model the flux loop (uses separate inbound/outbound flux budgets instead of a single pool fill-then-empty).
- `next_turn()` doesn't advance boot progress.
- 2 failing tests in `test_mecha_poc.py` from the above issues.

## Design Intent

- "3-5 Round Rule": full combat load should overheat in 3-5 turns by design.
- "100-Token Goal": heat values aimed at 0-100 range for readability.
- Flux is the real bottleneck, not sink capacity (design_combat_loops.md explains).
- Combat resolution happens on paper/dice. UI tracks state, modifiers, and damage. No digital dice.
- Multi-action penalties: double actions get 2 penalty dice on both. Further actions add more penalties.

## Files Created/Modified This Session

### Wiki
- `mecha/systems/offensive.md` -- weapon rules, example weapons, keywords (with TODO)
- `mecha/systems/heat.md` -- flux loop rewritten with 3-phase sequence
- `mecha/systems/energy.md` -- loadout rules, fuel, static power model
- `combat.md` -- Option A targeting, rising water sector damage, Damaged/Disabled/Destroyed
- `ewrules.md` -- Reinterpret mechanic
- `mecha/repair.md` -- repair thresholds, quirks table

### Code
- `GamePack/gamepack/endworld/OffensiveSystem.py` -- weapon class
- `GamePack/gamepack/endworld/Mecha.py` -- updated to use OffensiveSystem
