# Phase 3 Brief — Progression, Bosses & Inventory

## Context

Phase 2 is complete. It includes randomly generated multi-floor dungeons, room navigation with backtracking, room types (enemy, empty, staircase), four room themes, scaling enemy difficulty, the `descend` command, and an ASCII `map` of visited rooms. Phase 3 builds on that foundation by adding player progression, boss encounters, an inventory system, and save/load.

---

## Goal

Give the player something to build toward. Phase 3 introduces XP-based leveling with meaningful upgrade choices, escalating boss fights every 3 floors, a full inventory system with four item types, a merchant room, and manual save/load.

---

## Phase 3 Scope

### 1. Player Leveling

- XP is earned from every kill. The amount can vary by enemy type or floor depth (e.g. deeper enemies give more XP).
- Thresholds follow an increasing curve:
  - Level 1 → 2: 100 XP
  - Level 2 → 3: 200 XP
  - Level 3 → 4: 300 XP
  - ...and so on (each threshold increases by 100 XP)
- On level-up, the player is presented with **3 randomly drawn upgrade options** and picks one.
- Upgrades are drawn from a pool covering all four stat dimensions:
  - Increased max HP
  - Increased attack damage
  - Reduced incoming damage (defense stat)
  - Heavy Strike unlock / improvement
- The pool should be weighted so all four dimensions appear regularly — avoid runs where the player never sees a particular upgrade type.
- Display current level and XP progress in the status header after every action (alongside floor number and HP).

---

### 2. Combat Ability — Heavy Strike

- **Command:** `heavy strike` (abbreviation: `hs`)
- Unlocked via leveling (drawn from the upgrade pool).
- Deals significantly higher damage than a normal attack (suggested: 2–3× normal damage range).
- Has a cooldown of **3 turns** after use.
- When unavailable, display the remaining cooldown turns if the player attempts to use it.
- Can be improved by drawing it again in the upgrade draft (e.g. reduce cooldown to 2, then 1 turn).

---

### 3. Boss Encounters

Boss rooms appear every 3 floors (floors 3, 6, 9, ...).

**Boss room behaviour:**
- Visually distinct description when the player enters.
- Shown as `[B]` on the ASCII map.
- The player must defeat the boss to use the staircase on that floor (the staircase is locked until the boss is dead).

**Boss mechanics escalate with each encounter:**

| Boss # | Floor | Mechanics Active |
|---|---|---|
| 1 | Floor 3 | Multi-phase only |
| 2 | Floor 6 | Multi-phase + telegraphed attack |
| 3+ | Floor 9+ | All mechanics, harder stats |

- **Multi-phase:** At 50% HP the boss enters phase 2 and attacks twice per turn. Announce the phase transition with a dramatic description.
- **Telegraphed attack:** One turn before dealing a massive hit, the boss announces it (e.g. *"The creature winds up for a devastating blow..."*). The player has one turn to react (attack, use item, etc.) before the hit lands.
- **Stat scaling:** Boss HP and damage scale on top of the standard floor depth formula. Suggested multiplier: 2.5× the normal enemy stats for that floor.

**Boss drops:** Every boss drops a guaranteed item on defeat (drawn from the full item pool).

---

### 4. Inventory System

The player carries:
- **1 equipped weapon** (permanent attack damage upgrade)
- **1 equipped armour** (permanent defense upgrade)
- **3 consumable slots** (health potions and scrolls)

#### Item Types

| Item | Effect |
|---|---|
| **Health Potion** | Restores a fixed amount of HP when used (suggested: 40 HP) |
| **Weapon** | Permanently increases attack damage when equipped; replaces current weapon |
| **Armour** | Permanently reduces incoming damage when equipped; replaces current armour |
| **Scroll** | One-use special effect (e.g. stun enemy for 1 turn, full HP restoration, double damage for 3 turns) |

#### Finding Items

Items are found through three sources:
- **Empty rooms:** Random chance of containing an item on generation.
- **Enemy drops:** Chance-based drop on kill (suggested: ~20% chance).
- **Boss drops:** Guaranteed item drop on every boss defeat.
- **Merchant rooms:** See Section 5.

#### Inventory Rules

- If the player finds a weapon or armour and already has one equipped, they choose to equip the new one (discarding the old) or leave it.
- If all 3 consumable slots are full and the player finds a potion or scroll, they choose to pick it up (discarding an existing consumable) or leave it.
- The player starts with no weapon, no armour, and empty consumable slots.

---

### 5. Merchant Room

- Merchants appear as a **rare room type** slotted into the same generation pool as enemy and empty rooms (suggested: ~5% of rooms per floor).
- Shown as `[M]` on the ASCII map.
- When the player enters, the merchant offers a small selection of items (2–3 items, randomly drawn).
- Since there is no gold system in Phase 3, the merchant gives the player a **free choice of one item** from their stock. This keeps interaction simple without requiring a currency mechanic.
- Once the player has taken an item, the merchant's stock is exhausted for that visit. The room remains accessible but the merchant has nothing left to offer.

---

### 6. Save & Load

- **Commands:** `save` / `load` (abbreviations: `sv` / `ld`)
- Saving is only permitted in **empty rooms** or **immediately after defeating a boss**.
- One save slot (overwrites previous save).
- The save file captures full game state:
  - Current floor number and room layout
  - Which rooms have been visited and their state (enemies defeated, items taken)
  - Player HP, max HP, level, XP
  - Equipped weapon and armour
  - Consumable slots
  - Heavy Strike cooldown and unlock status
  - Defense stat

---

### 7. ASCII Map Updates

The `map` command is extended to show new room types introduced in Phase 3:

```
[ ] - [B] - [S]
              |
[*] - [M] - [ ]
```

**Updated legend:**

| Symbol | Meaning |
|---|---|
| `[*]` | Current room |
| `[ ]` | Visited room |
| `[S]` | Staircase room |
| `[E]` | Room with a living enemy |
| `[B]` | Boss room |
| `[M]` | Merchant room |
| `-` / `\|` | Connected doors |

The map header should display the current floor number and player level (e.g. `Floor 4 — Level 3`).

---

### 8. Commands to Add or Update

| Command | Abbreviation | Behaviour |
|---|---|---|
| `heavy strike` | `hs` | Deal high damage; unavailable for N turns after use |
| `inventory` | `i` | Display equipped weapon, armour, consumables, level, and XP |
| `use [item]` | `u [item]` | Use a consumable (e.g. `use potion`, `u potion`) |
| `equip [item]` | `eq [item]` | Equip a weapon or armour |
| `save` | `sv` | Save game state (empty rooms and post-boss only) |
| `load` | `ld` | Load last saved game |

**All Phase 2 command abbreviations remain active:**

| Command | Abbreviation |
|---|---|
| `attack` | `a` |
| `move north/south/east/west` | `mn` / `ms` / `me` / `mw` |
| `look` | `l` |
| `health` | `h` |
| `descend` | `d` |
| `map` | `m` |

> **Parser note:** `m` (map) and `mn/ms/me/mw` (move) must be handled carefully to avoid ambiguity. `d` (descend) should only trigger in a staircase room.

---

### 9. Status Header

After every action, display a status header containing:

```
Floor 4 | Level 3 | HP: 85/120 | XP: 340/400 | DEF: 2 | ATK bonus: +5
```

Adjust fields based on what the player has unlocked (e.g. omit DEF if no armour equipped yet).

---

## What Phase 3 Does NOT Include

Do not build any of the following. These are planned for later phases.

- Gold or a full economy/trading system
- Multiple save slots or named saves
- Trap rooms or environmental hazards
- NPC dialogue beyond merchant item selection
- Multiple enemies per room
- Player-facing XP bar animations (plain text notification on level-up is fine)

---

## Brief for Claude Code

> Build Phase 3 of the text-based dungeon crawler. Phases 1 and 2 are complete and handle: single-room combat, turn-based fighting, multi-floor procedural dungeon generation, room navigation (N/S/E/W), room types (enemy/empty/staircase), four room themes, scaling enemy difficulty, the `descend` command, and an ASCII `map` of visited rooms.
>
> Phase 3 adds:
>
> **Leveling:** XP from kills, increasing curve thresholds (100/200/300...), level-up draft (pick 1 from 3 random upgrades drawn from: max HP, attack damage, defense stat, Heavy Strike unlock/improve).
>
> **Heavy Strike:** New combat command (`heavy strike` / `hs`), high damage, 3-turn cooldown, unlocked via leveling, improvable via repeated draft picks (cooldown reduction).
>
> **Bosses:** Every 3 floors. Escalating mechanics — boss 1: multi-phase (2× attacks at 50% HP); boss 2: adds telegraphed big hit; boss 3+: all mechanics. Stats at 2.5× floor formula. Guaranteed item drop. Staircase locked until boss defeated. `[B]` on map.
>
> **Inventory:** 1 weapon slot, 1 armour slot, 3 consumable slots. Item types: health potion (restore 40 HP), weapon (attack bonus), armour (defense bonus), scroll (one-use effects). Items found in empty rooms (random), enemy drops (~20%), boss drops (guaranteed), and merchant rooms.
>
> **Merchant room:** Rare room type (~5%). Offers 2–3 items, player picks one free. `[M]` on map.
>
> **Save/Load:** Manual `save`/`load` commands. Save permitted in empty rooms and post-boss only. One save slot. Captures full game state.
>
> **Map updates:** Add `[B]` and `[M]` to legend. Map header shows floor and player level.
>
> **Status header:** Show floor, level, HP/max HP, XP/threshold, defense, and attack bonus after every action.
>
> **Command abbreviations:** `hs`, `i`, `u [item]`, `eq [item]`, `sv`, `ld` — plus all existing Phase 2 abbreviations (`a`, `mn/ms/me/mw`, `l`, `h`, `d`, `m`).
>
> Do not add gold/economy, multiple save slots, trap rooms, or multiple enemies per room yet.
