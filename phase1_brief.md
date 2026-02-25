# DUNGEON CRAWLER
## Master Project Plan
*Text-Based Turn-Based Adventure Game*

---

## Project Overview

Build a text-based, turn-based dungeon crawler game from the ground up. The game runs in a terminal/command line, accepts typed commands from the player, and displays the game state after each action. The project is structured in phases — start lean, then expand.

---

## Phase 1 — The Skeleton (Build This First)

Phase 1 is the minimum viable game. Nothing extra. Get this working before touching anything else.

### The Room
- Single room only — no multiple rooms yet
- Player starts in the center of the room
- Four exits: North, South, East, West (doors present but do nothing in Phase 1)
- Room state is displayed after every action

### The Enemy
- One enemy appears at the start of each round
- Enemy has a health value (e.g. 30 HP)
- Enemy attacks the player each turn if alive
- No enemy variety in Phase 1 — just one generic enemy type

### The Player
- Player has health points (e.g. 100 HP)
- Player can attack the enemy each turn
- Player can check their health at any time
- After defeating the enemy, player rests and fully recovers to 100 HP

### Commands (Phase 1)
- `attack` — attack the current enemy
- `move north` / `move south` / `move east` / `move west` — move toward a door (placeholder, no effect yet)
- `health` — display current HP
- `look` — describe the current room state

### Win / Lose Conditions
- **Win:** Enemy health reaches 0 → player rests → next enemy appears → loop
- **Lose:** Player health reaches 0 → game over message → option to restart

### What Phase 1 Does NOT Include
Do not build any of these yet. They come in later phases.

- No inventory system
- No multiple rooms or map
- No procedural generation
- No enemy variety
- No leveling or progression system
- No save/load

---

## Phase 2 — Expand the World (Plan Ahead, Build Later)

Phase 2 ideas are rough notes only. Do not build until Phase 1 is complete and working.

- Multiple rooms connected by doors — North/South/East/West actually navigate to new rooms
- Scaling enemy difficulty — enemies get stronger as you progress deeper
- Basic inventory — find items in rooms, pick them up, use them
- Simple map display — show which rooms have been visited

---

## Phase 3 — Polish (Far Future)

These are stretch goals. Don't think about these until Phase 2 is solid.

- Player leveling and stat upgrades
- Boss enemies at milestone rooms
- Save and load game state
- Randomly generated dungeon layouts

---

## Brief for Claude — How to Start Phase 1

When you're ready to build, paste this into a new conversation with Claude:

> Build me a text-based, turn-based dungeon crawler in Python. Phase 1 only. Single room. Player starts centered. One enemy appears with 30 HP. Combat is turn-based — each turn the player picks attack or a move direction, and the enemy attacks back. Damage is a random number in a range (e.g. 5–15 per hit). Player starts with 100 HP. After defeating the enemy, player fully recovers to 100 HP and a new enemy appears. Game ends when player HP hits 0. Commands: attack, move north, move south, move east, move west, health, look. Display room state and HP after every action. No inventory, no multiple rooms, no procedural generation yet.

---

*Start lean. Build Phase 1. Then expand.*
