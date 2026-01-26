# Future Changes & Refinements

## Gameplay Logic
- [ ] **Reactor Heat (Baseload)**: Implement heat generation for all reactors.
- [ ] **Heat System Energy Cost**: Active cooling systems (Coolant/Vent) should consume energy when toggled on.
- [ ] **Flux Pool Shimming**: Allow moving heat from systems back to the flux pool for free (non-budgeted).
- [ ] **Heat System Flux Split**: Implement active and passive fluxpool components for heat systems (necessary for `fluxpool_max`).
- [ ] **Loadout Queuing**: Selecting a loadout should queue the change for the next turn transition commit rather than applying it immediately.

## User Interface & Experience
- [ ] **Pure Clientside Turn State**: Move all "Pending" logic to `mechasheet.js`. The server only sees the final delta during "COMMIT".
- [ ] **Reactive Forecasts**: The Next Turn breakdown should update instantly in JS as sliders are moved or systems are toggled.
- [ ] **Mission Parameters Tab**: Relocate Encounter Log, Rename, and NEW encounter buttons to the top of the **Overview** tab.
- [ ] **Themed UI**: Apply the "Cyber-Button" (clipped polygon) styling to all primary buttons.
- [ ] **Emoji Elimination**: Ensure no emojis are used for functional icons or warnings.

## Technical Verification
- [ ] **Robust Heat Test**: Implement `tests/ui/test_mecha_heat_robust.py` to verify high-frequency bidirectional assignments.
- [ ] **Lifecycle Test**: Test overfilling heat, deactivating systems to compensate, and multi-turn decay.
