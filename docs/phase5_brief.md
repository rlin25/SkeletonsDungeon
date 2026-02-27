# Phase 5 Brief — The Final Descent

## Context

Phase 4 is complete. It includes the removal of post-combat HP recovery, rest rooms, room theme gameplay modifiers, a full gold economy with merchant buying and rerolling, a persistent minimap panel, and updated save/load capturing gold and room state. Phase 5 builds on that foundation by introducing the game's first true endgame, a deep combat overhaul, and a New Game+ mode for players who want to keep going.

---

## Goal

Complete the game. Phase 5 adds a final boss at floor 15, a win condition with run summary, multiple enemies per room with player-controlled targeting, status effects on both sides, trap rooms with dexterity-based disarming, elite enemies with unique abilities, and a New Game+ mode that carries forward earned stats at escalating difficulty.

---

## Phase 5 Scope

### 1. Dexterity Stat

Dexterity (DEX) is a new player stat governing dodge chance in combat and trap disarm success.

**Acquisition:**
- All players start with a base DEX of 5.
- DEX appears in the upgrade draft pool alongside ATK, DEF, and max HP, weighted to appear at similar frequency.
- Weapons and armour can roll with a DEX bonus as a secondary stat in addition to their primary ATK or DEF bonus.

**DEX in combat — dodge:**
- Each incoming attack has a dodge chance calculated as: `dodge_chance = DEX / (DEX + 40) * 100`
- Dodge is checked before DEF reduction. A dodged hit deals 0 damage and bypasses DEF entirely.
- Output on dodge: *"You sidestep the blow."*

**DEX in trap rooms — disarm:**
- Disarm success chance: `disarm_chance = DEX / (DEX + 20) * 100`
- On success: trap is neutralised. Room displays as `[t]` (disarmed) on the map.
- On failure: trap triggers its full effect, then the room is safe to pass through.
- Disarm is one attempt only. If it fails, the trap fires and the room clears.

**Status header with DEX:**
```
Floor 7 | Level 5 | HP: 80/130 | XP: 720/600 | Gold: 52 | DEF: 8 (29%) | ATK: +7 | DEX: 12 (23%)
```
DEX percentage shown uses the dodge formula.

---

### 2. Trap Rooms

Trap rooms are a new room type in the dungeon generation pool.

**Generation frequency:** ~10% of rooms per floor.

**Updated room distribution (per floor, excluding the guaranteed staircase):**

| Room Type | Frequency |
|---|---|
| Enemy rooms | ~50% |
| Empty rooms | ~15% |
| Rest rooms | ~12% |
| Merchant rooms | ~5% |
| Trap rooms | ~10% |
| Boss rooms | Every 3 floors (floors 3, 6, 9, 12) |
| Final boss room | Floor 15 only |

**Behaviour on entry:**
- The trap is always described before it can trigger — the player is never surprised.
- If an alternate path exists on the current floor (i.e. the trap room is not the only route forward), the player can simply not enter and route around it. No command needed — avoidance is a navigation choice.
- If no alternate path exists, the player must proceed through the room.
- On entering the room, the player may use `disarm` before the trap fires. If they do not attempt to disarm, using `proceed` confirms entry and triggers the trap automatically.

**Trap variety — randomly assigned on generation:**

| Trap Type | Effect on Trigger |
|---|---|
| Spike Pit | Deals `15 + (floor × 2)` damage |
| Poison Vent | Inflicts Poisoned (3 turns) |
| Alarm Trap | Spawns one additional enemy in the next enemy room on the current floor |
| Binding Snare | Inflicts Stunned (1 turn) at the start of the next combat encounter |
| Collapse Trap | Deals 10 damage and permanently removes one random exit from the room |

**Map symbols:**

| Symbol | Meaning |
|---|---|
| `[T]` | Trap room (not yet disarmed, or trap triggered) |
| `[t]` | Trap room (successfully disarmed) |

Trap rooms are not valid save locations.

---

### 3. Multiple Enemies Per Room

Some enemy rooms now spawn more than one enemy, scaling with floor depth.

**Spawn rates:**

| Floors | Spawn Rules |
|---|---|
| 1–3 | Always 1 enemy |
| 4–7 | 25% chance of a second enemy |
| 8–11 | 40% chance of a second enemy; 10% chance of a third |
| 12+ | 50% chance of a second enemy; 20% chance of a third |

The final boss room always spawns the Dungeon Architect alone.

**Targeting:**
- When more than one enemy is alive, `attack` and `heavy strike` require a target number: `attack 1`, `attack 2`, `hs 2`, etc.
- At the start of each turn, living enemies are listed with their current HP and any active status effects.
- If only one enemy remains, targeting is automatic and the number may be omitted.
- Each living enemy attacks the player individually on the enemy turn.
- The room clears only when all enemies are dead.

**XP and drops:**
- Each enemy awards XP and rolls for drops independently on death.
- The room is marked as cleared on the map only when all enemies are defeated.

---

### 4. Status Effects

Status effects are turn-based conditions lasting up to 3 turns. Both the player and enemies can be afflicted.

**Effect definitions:**

| Effect | Targets | Duration | Behaviour |
|---|---|---|---|
| Poisoned | Player or Enemy | 3 turns | Deals `3 + floor_number` damage at the start of the afflicted entity's turn |
| Burned | Player or Enemy | 3 turns | Deals `5 + floor_number` damage at the start of the afflicted entity's turn |
| Stunned | Player or Enemy | 1 turn | Skips the afflicted entity's action for one turn |
| Enraged | Enemy only | Until death | Increases enemy damage by 50%; applied when an enrage-capable enemy drops below 50% HP |

**Sources:**
- Players inflict effects via scrolls (Poison and Burn scroll types added to the item pool).
- Enemies inflict effects via elite abilities (Section 5) or trap room triggers (Section 2).

**Display:**
- Active effects on an enemy are shown on their info line during combat: *"Veteran Goblin (28/40 HP) [Poisoned — 2 turns]"*
- Active effects on the player are shown in the status header: `[Poisoned: 2] [Burned: 1]`

**Stacking rules:**
- The same effect cannot stack on the same target — re-applying resets duration to 3 turns.
- Poisoned and Burned stack with each other and tick independently.
- Stunned cannot stack — applying it while already stunned has no effect.

---

### 5. Elite Enemies

Some enemy rooms spawn an elite variant with enhanced stats and a unique ability.

**Spawn chance:** ~20% of enemy rooms on floors 3 and above. No elites on floors 1–2.

**Elite identification:**
- Elites use a descriptor prefix drawn from a pool, combined with the standard enemy name for that floor depth. Example prefixes: *Veteran, Cursed, Frenzied, Ancient, Rotting, Withered, Scarred, Hollow, Savage, Forsaken.*
- Example names: *Veteran Goblin, Cursed Skeleton, Frenzied Orc, Ancient Shadow Wraith, Rotting Troll, Withered Dungeon Horror.*
- Room entry description and the `look` command both include a distinct line identifying the elite: *"A Veteran Goblin stands here — scarred and battle-hardened, with a dangerous look in its eyes."*

**Elite stat scaling:**
- HP: `standard_max_hp × 1.5`
- Damage: `standard_dmg_min × 1.3` to `standard_dmg_max × 1.3` (rounded to nearest integer)

**Elite ability pool — one randomly assigned per elite:**

| Ability | Behaviour |
|---|---|
| Heal | Once per fight, when HP drops below 40%, recovers 25% of max HP. Announced: *"The [name] binds its wounds!"* |
| Enrage | When HP drops below 50%, enters Enraged state (+50% damage). Announced: *"The [name] enters a blood rage!"* |
| Summon | Once per fight, at the start of turn 3, spawns one standard (non-elite) enemy of the current floor. Announced: *"The [name] calls forth a companion from the shadows!"* |
| Shield | Blocks the first hit of the fight entirely (0 damage). Announced on block: *"Your attack glances off the [name]'s barrier!"* |
| Poison Strike | Each attack has a 40% chance to inflict Poisoned (3 turns) on the player. No special announcement — status display handles feedback. |
| Stun Strike | Once per fight, on the elite's third attack, inflicts Stunned (1 turn) on the player. Announced: *"The [name]'s blow leaves you reeling!"* |

Only one ability can be used per enemy turn, even if multiple would trigger simultaneously. Priority order if two conditions are met at once: Stun Strike > Heal > Enrage > Summon > Shield > Poison Strike.

**Elite drops:**
- 40% item drop chance on death (vs ~20% for standard enemies).
- Always drop gold on death: `(floor_number × 3) + random(2, 8)`.

---

### 6. Final Boss — The Dungeon Architect

The Dungeon Architect occupies a unique room on floor 15 and is the game's win condition.

**Room:**
- The final boss room replaces the staircase on floor 15. Instead of a staircase, the player finds the Dungeon Architect.
- On entry, a multi-line dramatic description is displayed before combat begins.
- Shown as `[F]` on the map.
- Not a valid save location.

**Phase 1 (100% → 50% HP):**
- HP: `400 + (ng_plus_cycle × 40)`
- Damage: `20–35 + (ng_plus_cycle × 3)`
- Two abilities randomly assigned from the full elite pool at fight start. Both are available throughout Phase 1. Only one ability fires per enemy turn.

**Phase transition (at 50% HP):**
- Announced with a dramatic multi-line description: *"The Dungeon Architect shatters — its form dissolving into shadow. Then, from the darkness, it rises again, larger and more terrible than before."*
- The boss revives to full HP.
- All six abilities become active. Only one fires per enemy turn (priority order from Section 5 applies).

**Phase 2 (full HP → 0):**
- Damage: `30–50 + (ng_plus_cycle × 3)`
- All six abilities active; one per turn.

**On defeat:**
- Guaranteed item drop (drawn from full item pool).
- Guaranteed gold drop: `50 + random(10, 30)`.
- Win screen and run summary displayed (Section 7).

---

### 7. Win Condition and Run Summary

Defeating the Dungeon Architect ends the run and displays the win screen.

**Win screen:** A short flavour description followed by the full run summary.

**Stats tracked from the start of the run and shown on the summary screen:**

| Stat | Description |
|---|---|
| Floors cleared | Total floors descended through |
| Enemies killed | Total, with elites broken out separately |
| Bosses defeated | Floor bosses + final boss |
| Total gold earned | Cumulative gold across the run (not current gold) |
| Damage dealt | Total damage output across all combat |
| Damage taken | Total damage received (combat, traps, and chip damage) |
| Times rested | Number of successful `rest` uses |
| Items used | Total consumable uses |
| Traps disarmed | Successful disarm count |
| Traps triggered | Traps that fired (failed disarm or unattempted) |
| Wall clock time | Real time elapsed since run start |
| Turns taken | Total in-game turns across the run |

After the run summary, the player is offered: `quit` to end, or `ng+` to begin a New Game+ cycle.

---

### 8. New Game+ (NG+)

Typing `ng+` after the win screen begins a fresh run with modified starting conditions.

**What carries over:**
- Player level.
- All stat upgrades accumulated during the run (max HP, ATK bonus, DEF, DEX).
- Heavy Strike unlock status and cooldown tier.
- Heavy Strike cooldown resets to ready at the start of NG+.

**What resets:**
- Current HP resets to max HP.
- Gold resets to 0.
- Equipped weapon resets to none.
- Equipped armour resets to none.
- Consumable slots reset to empty.
- XP resets to 0 (player level is kept; XP threshold resumes from the next level).
- All floor and room state is regenerated fresh.

**Enemy difficulty scaling:**
- All enemy HP and damage values are multiplied by `1 + (ng_plus_cycle × 0.10)`.
- Cycle 1 = ×1.10, Cycle 2 = ×1.20, and so on.
- This multiplier applies on top of the standard floor depth scaling formula.
- The final boss scales with `ng_plus_cycle` as noted in Section 6.

**NG+ display:**
- The current cycle is shown in the status header and map header when cycle ≥ 1.
- Example status header: `Floor 3 [NG+2] | Level 8 | HP: 110/130 | ...`
- Example map header: `Floor 3 [NG+2] — Level 8 — Gold: 18`

---

### 9. ASCII Map Updates

**New symbols added to the legend:**

| Symbol | Meaning |
|---|---|
| `[T]` | Trap room (unvisited, or trap triggered) |
| `[t]` | Trap room (disarmed) |
| `[F]` | Final boss room |

All Phase 4 symbols remain active.

---

### 10. Commands to Add or Update

| Command | Abbreviation | Behaviour |
|---|---|---|
| `attack [n]` | `a [n]` | Attack enemy number n; auto-targets if only one enemy is alive |
| `heavy strike [n]` | `hs [n]` | Heavy strike enemy number n; auto-targets if only one enemy is alive |
| `disarm` | `da` | Attempt to disarm a trap on entry to a trap room (one attempt) |
| `proceed` | `pr` | Confirm entry into a trap room without attempting to disarm |
| `ng+` | — | Begin New Game+ (available on win screen only) |

**All Phase 4 command abbreviations remain active.**

> **Parser notes:** `a` and `hs` now accept an optional integer argument. If omitted while multiple enemies are alive, prompt the player to specify a target. `da` and `pr` are valid only during trap room entry. `ng+` is valid only on the win screen.

---

### 11. Save File Updates

The save file must now also capture:

- DEX stat value
- Current NG+ cycle number
- All live run summary stats (tracked continuously, not just on win)
- Trap room states per floor (triggered or disarmed)
- Active status effects on the player (effect type and turns remaining)

---

### 12. Status Header (Final Form)

```
Floor 7 [NG+1] | Level 5 | HP: 80/130 | XP: 720/600 | Gold: 52 | DEF: 8* (29%) | ATK: +7* | DEX: 12 (23%) | [Poisoned: 2]
```

- `*` annotates temporary theme modifier bonuses (carried forward from Phase 4).
- Active player status effects shown at the end with turns remaining.
- NG+ cycle tag shown only when cycle ≥ 1.

---

## What Phase 5 Does NOT Include

- Multiple save slots or named saves
- Ranged or split-damage attack types
- NPC dialogue beyond merchant item listings
- Player-inflicted Enrage or Summon (player status sources remain scrolls only)
- Procedural boss variety (the Dungeon Architect is the sole final boss)
- Trap rooms as an enemy room sub-type — they are their own room type in the generation pool

---

## Brief for Claude Code

> Build Phase 5 of the text-based dungeon crawler. Phases 1–4 are complete and handle: turn-based combat, multi-floor procedural generation, room types (enemy/empty/staircase/rest/merchant/boss), four room themes with gameplay modifiers, scaling enemy difficulty, XP leveling with upgrade drafts, Heavy Strike with cooldown, boss encounters every 3 floors, full inventory system, gold economy with merchant buying and rerolling, persistent minimap, and manual save/load.
>
> Phase 5 adds:
>
> **Dexterity stat:** Base 5. Acquired via upgrade draft pool and as secondary stat on weapons/armour. Governs dodge chance in combat (`DEX / (DEX + 40) * 100`) and trap disarm chance (`DEX / (DEX + 20) * 100`). Shown in status header with percentage. Dodge is checked before DEF and bypasses it on success.
>
> **Trap rooms:** ~10% generation frequency. Always described on entry — player can route around if alternate path exists, otherwise must proceed. `disarm` / `da` attempts neutralisation (one attempt, DEX formula). On success: `[t]` on map. On failure: trap fires, room clears. Five trap types: Spike Pit (damage), Poison Vent (inflict Poisoned), Alarm Trap (spawn extra enemy nearby), Binding Snare (Stunned at next combat start), Collapse Trap (damage + remove one exit). Not valid save locations.
>
> **Multiple enemies:** Floor 4+ rooms have scaling chances of 2–3 enemies. Player targets with `attack [n]` / `hs [n]`; auto-targets if one enemy remains. All living enemies attack each turn. Room clears when all dead. XP and drops per enemy.
>
> **Status effects (3-turn max):** Poisoned (`3 + floor` dmg/turn), Burned (`5 + floor` dmg/turn), Stunned (skip turn), Enraged (enemy only, +50% damage at <50% HP). Poison and Burn stack; Stun does not. Re-applying resets duration. Shown on enemy info line and in player status header.
>
> **Elite enemies:** ~20% of enemy rooms on floor 3+. Named with a descriptor prefix + base name. Identified by distinct room entry and `look` description. Stats: 1.5× HP, 1.3× damage. One randomly assigned ability: Heal (recover 25% HP once at <40%), Enrage (activate at <50% HP), Summon (spawn enemy on turn 3), Shield (block first hit), Poison Strike (40% chance per attack), Stun Strike (stun on third attack). Only one ability fires per turn. 40% item drop, guaranteed gold drop.
>
> **Final boss — The Dungeon Architect:** Floor 15, replaces staircase, shown as `[F]`. Phase 1 (full HP → 50%): two random abilities active, one per turn, HP `400 + (cycle × 40)`, damage `20–35 + (cycle × 3)`. At 50%: dramatic transition, revives to full HP. Phase 2: all six abilities active, damage `30–50 + (cycle × 3)`. Guaranteed item + gold drop on death.
>
> **Win condition + run summary:** Win screen on final boss death. Track and display: floors cleared, enemies killed (elites separate), bosses defeated, total gold earned, damage dealt, damage taken, times rested, items used, traps disarmed, traps triggered, wall clock time, turns taken. Offer `quit` or `ng+` after summary.
>
> **New Game+:** Carries over level and all stat upgrades. Resets gold, equipped items, consumables, XP, and floor state. Enemy HP and damage multiplied by `1 + (cycle × 0.10)`. NG+ cycle shown in status header and map header as `[NG+N]`.
>
> **New commands:** `disarm` / `da`, `proceed` / `pr`, `attack [n]` / `a [n]`, `heavy strike [n]` / `hs [n]` (with optional target), `ng+` (win screen only).
>
> **Save file additions:** DEX, NG+ cycle, live run summary stats, trap room states per floor, active player status effects with turns remaining.
>
> Do not add multiple save slots, ranged attacks, NPC dialogue beyond merchants, or procedural boss variety.
