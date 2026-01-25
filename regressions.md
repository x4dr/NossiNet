# Regressions & Lost Features Audit

## NossiSite/sheets.py

- [ ] **`doroll` function**: Completely removed. This handled attribute/skill rolls for FenCharacters and posted to the
  chat webhook. **Status**: Needs full restoration.
- [ ] **`infolet` helpers**: `infolet_filler` and `infolet_extractor` were removed. These handled dynamic link and value
  extraction in character sheets. **Status**: Needs restoration.
- [ ] **Character-Specific Renderers**: `fensheet_render`, `pbta_render`, and `EWCharacter` renderers were removed.
  While a generic `render_sheet` exists, it may not have all the context variables (like `owner` logic) of the
  originals. **Status**: Verify and restore if necessary.
- [ ] **Duplicate Logic**: Regex edits created duplicate route decorators and corrupted function arguments (
  e.g. `identifierethods`). **Status**: Cleanup required.
- [ ] **Loadout Name Case Sensitivity**: `loadout_name.title()` was changed to `loadout_name`, which might cause mismatches with Markdown definitions.
- [ ] **Default Loadout Ordering**: Energy systems should come first in the default loadout.
- [ ] **Heat Assignment Restriction**: Code prevents assigning heat to inactive heat systems; this should be allowed.
- [ ] **HeatSystem Underflow**: `HeatSystem.withdraw_heat` (or similar) does not return the "underage" (analogous to overage) when drawing more than is present.
- [ ] do another pass for functionality that may be used by the other parts of the website that you removed or touched.
  report on them so that i can decide what needs to be done with them

## wiki/mechtest.md

- [ ] **Zeroed Stats**: `Energy`, `Mass`, and `Amount` for `Vent`, `Coolant`, and `Sink` were set to `0`. Original
  values like `Energy: 2` for Vent were lost. **Status**: Restore from git history.
- i have restored some of them a little. use your game-dev brain to figure out good stats that still roughly make sense.
  balance comes later but i don't want to develop on comepletely unrealistic stats
- [ ] **Reactor Calibration**: Baseload reactor was increased to 500. **Status**: Review if this is excessive for the
  game balance.

## GamePack/gamepack/endworld/Mecha.py

- [ ] **`energy_total` removal**: Caused breakage in the energy meter. **Status**: Restored partially, needs cleanup.
- [ ] **Energy Allocation Logic**: Changed from original priority-based iteration to a simplified version. **Status**:
  Review if the original priority markers `[0], [10], ...` are still handled correctly.
- [ ] **Energy Demand Logic**: `energy_demand` should check specifically for system types instead of just excluding energy systems.

## UI / Aesthetics

- [ ] **Emoji Usage**: `↻` (Cycle) and `⚠️` (Warning) are still present. **Status**: Replace with CSS icons or themed
  text.
- [ ] **Header Pollution**: Mission parameters (Encounter log, rename, NEW) are in the header across all views. **Status
  **: User wants them restricted to the "Overview" tab.
- [ ] **Save Button**: Described as "looking weird." **Status**: Standardize with `.cyber-button` class.

## Lost Features for Review (Signed off?)

- Standardizing parameter `identifier` back to `m`. (Agent speculation: Standardizing on `m` is better for codebase
  consistency).
- m for mecha
- Disabling background `fetch()` for every slider move. (Agent speculation: Correct, moving to clientside JS state is
  more responsive).
- the interface should only call to the server if something needs updating on the server, which with a few exceptions is
  just when state needs to be persisted or UI updated (the energy and heat meters should live-update, being rendered by
  the server, but not persist stuff to db)
