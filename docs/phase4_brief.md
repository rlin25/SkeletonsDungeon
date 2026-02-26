# Phase 4 Brief — Survival, Theme & Economy

## Context

Phase 3 is complete. It includes XP-based leveling with upgrade drafts, Heavy Strike with cooldown, boss encounters every 3 floors with escalating mechanics, a full inventory system (weapon, armour, consumables), merchant rooms, and manual save/load. Phase 4 builds on that foundation by overhauling the HP economy, making room themes mechanically meaningful, introducing a gold system, and adding a persistent minimap panel.

---

## Goal

Make every room matter. Phase 4 removes full HP recovery after combat, adds rest rooms as the primary healing sanctuary, gives each room theme real gameplay effects, introduces a gold economy tied to the merchant, and renders the map persistently alongside the game output so the player always knows where they are.

---

## Phase 4 Scope

### 1. Remove Post-Combat Full HP Recovery

- **Full HP recovery after defeating an enemy is removed.**
- HP persists across all combat encounters and is only restored through potions, scrolls, and rest rooms (see Section 2).
- This applies from floor 1 onward.

---

### 2. Rest Rooms

Rest rooms are a new room type added to the dungeon generation pool.

**Behaviour:**
- When the player enters a rest room, they are prompted that they can use the `rest` command to recover.
- Using `rest` fully restores the player to max HP and displays a short flavour description themed to the room (see below).
- Each rest room can only be used **once** — it is depleted after resting. The room remains traversable but offers no further healing.
- Rest rooms are valid **save locations** (same as empty rooms in Phase 3).

**Generation frequency:** ~15% of rooms per floor.

**Suggested room distribution (all must sum correctly with the guaranteed staircase):**
- Enemy rooms: ~55%
- Empty rooms: ~20%
- Rest rooms: ~15%
- Merchant rooms: ~5%
- 1 guaranteed Staircase Room per floor (outside the percentage pool)

**Map symbols:**
- `[R]` — rest room, available
- `[r]` — rest room, depleted

**Themed flavour descriptions (one per room theme):**

| Theme | Rest Description |
|---|---|
| Damp Cave | A shallow alcove fed by a natural spring. The water is ice-cold and clear. You drink deeply. |
| Torchlit Corridor | A stone bench beside a steady torch. You sit, breathe, and let the warmth settle into your bones. |
| Forgotten Chamber | A cracked altar still faintly warm, as if someone prayed here not long ago. You rest against it and feel restored. |
| Collapsed Tunnel | A gap in the rubble just wide enough to shelter in. Dust settles around you. For a moment, you feel safe. |

---

### 3. Room Theme Gameplay Effects

Room themes are no longer purely cosmetic. Each theme now applies one or more gameplay modifiers while the player is in that room.

#### Theme Modifier Table

| Theme | Modifier |
|---|---|
| **Damp Cave** | +2 DEF while present (moisture-slicked stone dulls blows). On entry, deal 3 chip damage to the player (slippery footing). |
| **Torchlit Corridor** | +2 ATK bonus while present (good visibility sharpens your aim). No hazard. |
| **Forgotten Chamber** | No stat modifier. Enemy rooms in this theme have a 30% chance to spawn an undead variant (Skeleton, Shadow Wraith, Undead Knight — names by depth). Empty rooms in this theme have a 40% chance to contain an item. |
| **Collapsed Tunnel** | Visibility reduced: exits are hidden until the player uses `look` or moves into the room. No stat modifier. |

**Implementation notes:**
- Stat modifiers (ATK/DEF bonuses) are temporary and apply only while the player is in that room. They do not persist when the player moves.
- Chip damage on Damp Cave entry is dealt once per visit — not on re-entry to an already-visited room.
- Undead enemy variants use the same stat formula as standard enemies for their floor but have distinct names. Suggested names by depth:
  - Floor 1–2: Skeleton
  - Floor 3–4: Shadow Wraith
  - Floor 5+: Undead Knight
- The visibility reduction in Collapsed Tunnel only hides exit directions. The room description still displays. Using `look` reveals all exits normally.
- Display active room modifiers clearly when entering a room and when using `look` (e.g. `[Damp Cave: +2 DEF, -3 HP on entry]`).

---

### 4. Gold System

Gold is a new persistent resource tracked on the player.

#### Earning Gold

| Source | Amount |
|---|---|
| Enemy kill | Random drop: 1–5 gold (every kill) |
| Empty room | ~25% chance of containing 3–8 gold on generation |
| Boss kill | Guaranteed drop: 15–30 gold (random range) |

Gold amounts should scale mildly with floor depth — multiply the gold range by `1 + (floor_number - 1) * 0.1` (i.e. +10% per floor), rounded to the nearest integer.

#### Spending Gold

Gold is spent exclusively at merchant rooms.

**Buying items:**
- The merchant offers 3 items with randomly assigned prices.
- Price ranges per item type:

| Item Type | Price Range |
|---|---|
| Health Potion | 8–15 gold |
| Weapon | 20–40 gold |
| Armour | 20–40 gold |
| Scroll | 12–25 gold |

- Prices are randomised on merchant room generation and fixed for that visit.
- The player buys by typing `buy [item number]` (e.g. `buy 1`, `buy 2`, `buy 3`).
- Normal inventory rules apply on purchase (replace or discard prompts as per Phase 3).

**Re-rolling merchant stock:**
- The player can type `reroll` at a merchant to discard the current stock and generate 3 new items with new prices.
- Cost: **10 gold** per reroll.
- Only one reroll is permitted per merchant visit.
- If the player cannot afford the reroll, display the cost and their current gold.

**Free pick is removed.** The Phase 3 mechanic of receiving one free item is replaced entirely by the gold system.

#### Gold in the Status Header

Gold is always displayed in the status header:

```
Floor 5 | Level 4 | HP: 60/120 | XP: 520/500 | Gold: 34 | DEF: 6 (23%) | ATK bonus: +7
```

#### Save/Load

Gold is captured in the save file alongside all other player state.

---

### 5. Persistent Minimap Panel

The ASCII map is no longer only available via the `map` command. It now renders **persistently** alongside every game output, to the right of the main text.

**Layout:**

```
=========================================================
You move north into a Torchlit Corridor.          [R] - [ ]
A flickering torch casts long shadows.                  |
[Torchlit Corridor: +2 ATK]                       [*] - [E]
Exits: South, East                                      |
                                                  [ ] - [S]

Floor 5 | Level 4 | HP: 60/120 | XP: 520/500 | Gold: 34 | DEF: 6 (23%) | ATK bonus: +7
=========================================================
```

**Behaviour:**
- The minimap updates after every action, showing the current floor's visited rooms.
- Width scales to fit the current floor — it expands as more rooms are discovered, up to the terminal width.
- The `map` command still works and prints a full-width version of the map with the legend below it, for detailed reference.
- Unvisited rooms remain hidden on the persistent minimap (same rule as the `map` command).
- The current room is always `[*]`.

**Legend** (shown only when `map` command is used, not in the persistent panel):

| Symbol | Meaning |
|---|---|
| `[*]` | Current room |
| `[ ]` | Visited room |
| `[S]` | Staircase room |
| `[E]` | Room with a living enemy |
| `[B]` | Boss room |
| `[M]` | Merchant room |
| `[R]` | Rest room (available) |
| `[r]` | Rest room (depleted) |
| `-` / `\|` | Connected doors |

---

### 6. ASCII Map Updates

Map header displays floor, player level, and gold:

```
Floor 5 — Level 4 — Gold: 34
```

---

### 7. Commands to Add or Update

| Command | Abbreviation | Behaviour |
|---|---|---|
| `rest` | `r` | Fully restore HP (rest rooms only; once per room) |
| `buy [number]` | `b [number]` | Purchase a numbered item from merchant stock |
| `reroll` | `rr` | Re-roll merchant stock for 10 gold (once per visit) |

> **Parser note:** `r` (rest) should only activate in rest room context. `rr` (reroll) should only activate in merchant room context.

**All Phase 3 command abbreviations remain active:**

| Command | Abbreviation |
|---|---|
| `attack` | `a` |
| `heavy strike` | `hs` |
| `move north/south/east/west` | `mn` / `ms` / `me` / `mw` |
| `look` | `l` |
| `health` | `h` |
| `descend` | `d` |
| `map` | `m` |
| `inventory` | `i` |
| `use [item]` | `u [item]` |
| `equip [item]` | `eq [item]` |
| `save` | `sv` |
| `load` | `ld` |

---

### 8. Status Header

```
Floor 5 | Level 4 | HP: 60/120 | XP: 520/500 | Gold: 34 | DEF: 6 (23%) | ATK bonus: +7
```

- Gold is always shown, even at 0.
- DEF percentage uses the diminishing returns formula from Phase 3: `DEF / (DEF + 20) * 100`.
- Active room modifiers (ATK/DEF bonuses from themes) are reflected in the ATK bonus and DEF values shown — annotate with `*` if a modifier is active (e.g. `DEF: 8* (29%)`) so the player knows it's temporary.

---

### 9. Save File Updates

The save file must now also capture:
- Current gold amount
- Rest room depletion states per floor (which `[R]` rooms have been used)
- Merchant reroll state per room (whether the one permitted reroll has been used)

---

## What Phase 4 Does NOT Include

- Multiple enemies per room
- Status effects (poison, burn, stun) — scrolls may reference stun but it is already scoped in Phase 3
- Named NPC dialogue for merchants beyond item listings
- Multiple save slots
- Trap rooms as a dedicated room type (chip damage from Damp Cave entry is environmental, not a trap room)

---

## Brief for Claude Code

> Build Phase 4 of the text-based dungeon crawler. Phases 1–3 are complete and handle: turn-based combat, multi-floor procedural generation, room types (enemy/empty/staircase/merchant/boss), four room themes (cosmetic only), scaling enemy difficulty, `descend`, ASCII `map`, XP leveling with upgrade drafts, Heavy Strike, boss encounters, full inventory system, and manual save/load.
>
> Phase 4 adds:
>
> **Remove post-combat full HP recovery.** HP only restores via potions, scrolls, and rest rooms.
>
> **Rest rooms:** New room type (~15% frequency). `rest` / `r` command fully restores HP once per room. Depleted rooms shown as `[r]` on map vs `[R]` available. Four themed flavour descriptions. Valid save location.
>
> **Room theme gameplay effects:** Damp Cave — +2 DEF while present, 3 chip damage on first entry. Torchlit Corridor — +2 ATK while present. Forgotten Chamber — 30% chance of undead enemy variant, 40% item chance in empty rooms. Collapsed Tunnel — exits hidden until `look` or entry. Display active modifiers in room description and status header (annotated with `*`).
>
> **Gold system:** Earned from enemy kills (1–5 gold), empty rooms (25% chance, 3–8 gold), boss kills (15–30 gold guaranteed). All amounts scale +10% per floor. Spent at merchants: buy items (`buy [n]` / `b [n]`) at randomised prices (potions 8–15, weapons/armour 20–40, scrolls 12–25), or reroll stock once per visit for 10 gold (`reroll` / `rr`). Free item pick from Phase 3 is removed. Gold shown in status header and saved to file.
>
> **Persistent minimap:** Map renders to the right of every game output, not just on `map` command. Scales width to the current floor. `map` command still works for a full-width view with legend.
>
> **Map updates:** Add `[R]` / `[r]` to legend. Map header shows floor, level, and gold.
>
> **Status header:** Add Gold field. Annotate temporary theme modifiers with `*`.
>
> **Save file updates:** Capture gold, rest room depletion states, and merchant reroll states.
>
> Do not add multiple enemies per room, status effects, trap rooms, or multiple save slots.
