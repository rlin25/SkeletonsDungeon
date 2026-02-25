# Phase 2 Brief — Dungeon Crawler: Expand the World

## Context

Phase 1 is complete. It includes a single room, one enemy, turn-based combat, basic commands (`attack`, `move north/south/east/west`, `health`, `look`), and full health recovery after each fight. Phase 2 builds on that foundation by adding a real dungeon to explore.

---

## Goal

Expand the game from a single static room into a fully navigable, randomly generated dungeon with multiple floors. The player explores connected rooms, finds a staircase to descend deeper, and faces increasingly dangerous enemies the further they go.

---

## Phase 2 Scope

### 1. Randomly Generated Floors

- Each floor is procedurally generated on entry — no two runs are the same.
- Floors are made up of rooms connected by doors in cardinal directions (N/S/E/W).
- Dungeon size scales with floor depth plus RNG variance:
  - Floor 1: ~5–8 rooms
  - Floor 3: ~8–13 rooms
  - Floor 5+: ~12–20 rooms
  - Apply ±2 RNG variance to the room count each time.

### 2. Room Navigation

- The player moves between rooms using `move north`, `move south`, `move east`, `move west`.
- Only valid exits (connected doors) should be available from each room.
- The player can backtrack freely — already-visited rooms persist in their current state (enemies defeated stay defeated, empty rooms stay empty).
- Display available exits after every move or `look` command.

### 3. Room Variety

Each room is one of the following types, assigned randomly on generation:

| Room Type | Description |
|---|---|
| **Enemy Room** | Contains one enemy. Must be defeated to freely pass through. |
| **Empty Room** | No enemy. May contain flavour text describing the environment. |
| **Staircase Room** | Contains a staircase. Using it descends to the next floor. |

Room type distribution per floor (approximate):
- 60% Enemy Rooms
- 30% Empty Rooms
- 1 guaranteed Staircase Room (placed randomly, not at the start)

### 4. Room Themes and Descriptions

Each room has a randomly assigned theme that affects its description. Suggested themes:

- **Damp Cave** — dripping water, moss-covered stone, low visibility
- **Torchlit Corridor** — flickering torches, carved stone, scattered bones
- **Forgotten Chamber** — crumbling pillars, dust-covered floor, eerie silence
- **Collapsed Tunnel** — rubble, broken supports, narrow passage

Display the room theme and a short description when the player enters a new room or uses `look`.

### 5. Scaling Enemy Difficulty

Enemy stats should scale with floor depth. Suggested formula:

```
enemy_max_hp = 30 + (floor_number - 1) * 10
enemy_damage_min = 5 + (floor_number - 1) * 2
enemy_damage_max = 15 + (floor_number - 1) * 3
```

Enemy names should also reflect depth — for example:
- Floor 1: Goblin, Rat, Skeleton
- Floor 3+: Orc, Shadow Wraith, Stone Golem
- Floor 5+: Troll, Undead Knight, Dungeon Horror

### 6. Floor Progression

- The staircase room contains a visible staircase when the player enters.
- The player uses the command `descend` to go to the next floor.
- On descending, a new floor is generated. The player starts at a random room (not the staircase).
- Display the current floor number in the status header after every action.

### 7. Commands to Add or Update

| Command | Behaviour |
|---|---|
| `move [direction]` | Move to an adjacent room if a door exists that way |
| `look` | Describe the current room, exits, and enemy (if present) |
| `descend` | Use the staircase to go to the next floor (staircase room only) |
| `map` | Show a simple ASCII map of visited rooms on the current floor |

### 8. ASCII Map (Simple)

The `map` command displays a minimal ASCII grid of discovered rooms. Example:

```
[ ] - [ ] - [S]
              |
[*] - [ ] - [ ]
```

Legend:
- `[*]` = current room
- `[ ]` = visited room
- `[S]` = staircase room
- `[E]` = room with a living enemy
- `-` / `|` = connected doors

Only show rooms the player has visited. Unvisited rooms are hidden.

---

## What Phase 2 Does NOT Include

Do not build any of the following. These are planned for later phases.

- Inventory system or items
- Player levelling or stat upgrades
- Boss enemies
- Save and load
- Sound or visual interface

---

## Player Stats Carry Over

The player's current HP carries over between rooms and floors. Full health recovery still applies after defeating each enemy, as established in Phase 1.

---

## Brief for Claude Code

> Build Phase 2 of the text-based dungeon crawler. Phase 1 is already complete and handles: single room, one enemy, turn-based combat, commands (attack, move, health, look), and full HP recovery after each fight.
>
> Phase 2 adds:
> - Randomly generated floors with room counts that scale with depth (±2 RNG variance)
> - Rooms connected by N/S/E/W doors; player backtracks freely
> - Room types: enemy rooms (60%), empty rooms (30%), one guaranteed staircase room per floor
> - Four room themes with short descriptions (damp cave, torchlit corridor, forgotten chamber, collapsed tunnel)
> - Enemy stats scale with floor depth using: HP = 30 + (floor-1)*10, damage min = 5 + (floor-1)*2, damage max = 15 + (floor-1)*3
> - Enemy names vary by depth (goblins early, trolls deep)
> - `descend` command at the staircase to go deeper; new floor generates, player spawns in a random non-staircase room
> - `map` command shows a simple ASCII grid of visited rooms on the current floor
> - Current floor number shown in the status header after every action
>
> Do not add inventory, levelling, boss enemies, or save/load yet.
