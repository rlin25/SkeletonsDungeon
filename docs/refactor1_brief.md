# Dungeon Crawler — Refactor Plan
## Pre-Phase 4 Code Restructure

---

## Overview

The Phase 3 codebase is a single file of ~1,350 lines. It is well-written and largely coherent, but several structural problems will compound badly when Phase 4 adds persistent minimaps, room theme modifiers, a gold economy, and rest rooms — all of which reach into nearly every existing system. This document defines a targeted refactor to address those problems before Phase 4 begins.

**The goal is not a rewrite.** The logic is mostly sound. The goal is separation of concerns, elimination of the most dangerous coupling patterns, and laying groundwork for the two Phase 4 features that will touch the most code: the persistent minimap panel and room theme gameplay effects.

---

## Current State Assessment

### What is working well
- Item classes (`HealthPotion`, `Weapon`, `Armour`, `Scroll`) are clean, self-contained, and serializable.
- `Player` is a well-formed class with proper `to_dict` / `from_dict` support.
- `Enemy` and `Boss` are reasonably clean, with `Boss` correctly extending `Enemy`.
- The upgrade system (`_Upgrade` subclasses, `draw_upgrades`) is nicely isolated.
- Constants and data tables at the top of the file are easy to find and edit.

### What needs fixing

**1. `handle()` is a 190-line monolithic function (lines 955–1144)**
Every command — attack, move, look, inventory, use, equip, descend, save, load, help — is handled by sequential `if verb ==` branches in a single function. It returns a 4-tuple `(turn_used, messages, new_room, descended)` with sentinel string values (`'__map__'`, `'__save__'`, `'__load__'`) to signal special behaviour to the caller. This is a code smell: the caller (`run_game`) has to inspect message content to know what happened. Phase 4 adds `rest`, `buy`, and `reroll` commands — adding them here makes this function even harder to follow.

**2. `run_game()` is doing too much (lines 1208–1337)**
The main game loop handles: input reading, command dispatch, boss phase transitions, enemy retaliation, cooldown ticking, XP and level-up, item drops, room transitions, floor descent, and redrawing. It is ~130 lines of tightly coupled sequential logic. Phase 4's theme modifiers (temporary ATK/DEF bonuses that must apply on entry and unapply on exit) need clean hooks into room transition logic — this loop has no such hooks.

**3. `save_game()` and `load_game()` use `object.__new__()` to bypass constructors (lines 908, 921, 931)**
Room and Enemy objects are reconstructed by directly setting attributes on raw instances, bypassing `__init__`. This works now, but it means any new attribute added to `Room`, `Enemy`, or `Boss` in Phase 4 must be manually added in three places: the constructor, `save_game`, and `load_game`. Rest room depletion state and merchant reroll state (both required by Phase 4) will need to be tracked this way unless `Room` gets proper serialization methods.

**4. `Room` has no `to_dict` / `from_dict` (line 368)**
Unlike `Player` and all item classes, `Room` lacks serialization methods. Its save/load logic is written inline inside `save_game()` and `load_game()`, which are already long functions. Phase 4 adds two new per-room state fields (`rest_used`, `merchant_rerolled`) that will need to be serialized.

**5. `draw_room()` and `status_line()` are pure output functions mixed in with game logic (lines 633–692)**
Phase 4 requires the minimap to render alongside every output, and the status header to annotate temporary theme modifiers with `*`. These concerns are currently scattered. There is no renderer layer — output logic lives alongside game logic in the same file with no separation.

**6. `offer_item()` is a 67-line interactive function with branching isinstance checks (lines 765–831)**
It handles three item types with substantially different flows, uses `_pick()` for inline user input, and is called from multiple sites. Phase 4 doesn't change this directly but adding item types or changing slot rules will require editing a function that is already hard to follow.

---

## Recommended File Structure

Split the single file into focused modules. Python's `import` system makes this straightforward — no framework needed.

```
dungeon/
├── main.py            # Entry point — calls run_game()
├── constants.py       # All constants, data tables, pools
├── items.py           # Item classes + item_from_dict + random_item
├── player.py          # Player class
├── enemy.py           # Enemy + Boss classes
├── room.py            # Room class with to_dict / from_dict
├── floor.py           # generate_floor() + _floor_room_count()
├── upgrades.py        # _Upgrade subclasses + draw_upgrades()
├── combat.py          # run_enemy_turn() + run_boss_turn()
├── commands.py        # Command handler — replaces handle()
├── renderer.py        # draw_room(), draw_map(), status_line(), hp_bar()
├── persistence.py     # save_game() + load_game()
└── game.py            # run_game() main loop
```

This is not mandatory to do all at once. The sections below identify which splits deliver the most value and should be prioritised.

---

## Refactor Tasks — Prioritised

### Priority 1 — Must do before Phase 4

#### 1a. Add `to_dict` / `from_dict` to `Room`

The most impactful single change. Move the room serialization logic out of `save_game` and `load_game` and into the `Room` class itself. Add the two Phase 4 fields at the same time so they are never forgotten.

```python
class Room:
    def to_dict(self):
        return {
            'col': self.col, 'row': self.row,
            'type': self.type,
            'theme_name': self.theme_name, 'theme_desc': self.theme_desc,
            'visited': self.visited, 'flavour': self.flavour,
            'exits': {d: [r.col, r.row] for d, r in self.exits.items()},
            'item': self.item.to_dict() if self.item else None,
            'merchant_items': [i.to_dict() for i in self.merchant_items],
            'merchant_done': self.merchant_done,
            'rest_used': self.rest_used,             # Phase 4 field — add now
            'merchant_rerolled': self.merchant_rerolled,  # Phase 4 field — add now
            'enemy': self.enemy.to_dict() if self.enemy else None,
        }

    @staticmethod
    def from_dict(d):
        r = object.__new__(Room)
        # ... populate fields from d ...
        return r
```

`save_game` and `load_game` then become straightforward loops over `room.to_dict()` and `Room.from_dict()`.

#### 1b. Add `to_dict` / `from_dict` to `Enemy` and `Boss`

Same pattern as above, same motivation. Currently both are reconstructed inline in `load_game` using `object.__new__` with raw attribute assignment. Move this logic into the classes.

```python
class Enemy:
    def to_dict(self):
        return {
            'is_boss': False,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
        }

    @staticmethod
    def from_dict(d):
        e = object.__new__(Enemy)
        e.hp = d['hp']
        # ... etc ...
        return e

class Boss(Enemy):
    def to_dict(self):
        d = super().to_dict()
        d.update({'is_boss': True, 'boss_num': self.boss_num, ...})
        return d

    @staticmethod
    def from_dict(d):
        # ...
```

#### 1c. Break `handle()` into a command dispatcher

Replace the monolithic `handle()` with a dispatcher that routes to small, focused handler functions. The sentinel string pattern (`'__map__'`, `'__save__'`) should be eliminated — use a result object or named return instead.

Suggested approach — a `CommandResult` dataclass:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CommandResult:
    turn_used: bool = False
    messages: list = field(default_factory=list)
    new_room: Optional[object] = None
    descended: bool = False
    action: str = ''   # 'map' | 'save' | 'load' | '' — replaces sentinel strings
```

Then the dispatcher becomes a clean routing table:

```python
COMMAND_HANDLERS = {
    'attack':    cmd_attack,
    'heavy':     cmd_heavy_strike,
    'move':      cmd_move,
    'look':      cmd_look,
    'health':    cmd_health,
    'inventory': cmd_inventory,
    'use':       cmd_use,
    'equip':     cmd_equip,
    'descend':   cmd_descend,
    'map':       cmd_map,
    'save':      cmd_save,
    'load':      cmd_load,
    'rest':      cmd_rest,     # Phase 4
    'buy':       cmd_buy,      # Phase 4
    'reroll':    cmd_reroll,   # Phase 4
    'help':      cmd_help,
    'quit':      cmd_quit,
}

def dispatch(raw, player, room, floor_num, boss_room):
    tokens = raw.strip().lower().split()
    if not tokens:
        return CommandResult(messages=['(nothing)'])
    handler = COMMAND_HANDLERS.get(tokens[0])
    if handler is None:
        return CommandResult(messages=[f"Unknown command '{raw}'. Type 'help' for options."])
    return handler(tokens, player, room, floor_num, boss_room)
```

Each handler is a small function with a single responsibility. Adding Phase 4 commands means adding a function and a line in the table — not editing a 190-line monolith.

#### 1d. Add room transition hooks to `run_game()`

Phase 4's theme modifiers require code to run when the player enters or leaves a room. Currently room transitions happen in two inline blocks in `run_game()` (lines 1298–1325). Extract these into a `on_room_enter(player, room)` function so Phase 4 can add modifier logic in one place.

```python
def on_room_enter(player, room):
    """Called whenever the player enters a room. Apply entry effects."""
    # Phase 4: apply theme modifiers here
    announce_room(room)

def on_room_exit(player, room):
    """Called whenever the player leaves a room. Remove temporary effects."""
    # Phase 4: unapply theme modifiers here
    pass
```

This is a small change that prevents significant pain later. Without it, theme modifier application will be copy-pasted into two places in the main loop (room navigation and floor descent), which will inevitably diverge.

---

### Priority 2 — High value, do alongside Priority 1

#### 2a. Extract a `Renderer` module

Move all output functions into a dedicated module: `draw_room()`, `draw_map()`, `status_line()`, `hp_bar()`, `announce_room()`, `intro_screen()`, `game_over_screen()`. Phase 4's persistent minimap means `draw_room()` needs to render a minimap panel beside the room view — this is much cleaner to implement if the renderer is a self-contained module with a clear interface.

#### 2b. Extract `combat.py`

Move `run_enemy_turn()` and `run_boss_turn()` to a dedicated module. These are already well-written — this is purely a housekeeping split that makes Phase 4's combat-adjacent changes (theme ATK/DEF bonuses affecting damage rolls) easier to locate and modify.

#### 2c. Simplify `offer_item()`

Break the three `isinstance` branches into separate functions: `offer_consumable()`, `offer_weapon()`, `offer_armour()`. Call from a thin `offer_item()` dispatcher. This makes each flow independently readable and easier to test.

---

### Priority 3 — Nice to have, can defer to after Phase 4

#### 3a. Split into the full module structure

Once Priorities 1 and 2 are done, the remaining splits (`constants.py`, `items.py`, `player.py`, `enemy.py`, `floor.py`, `upgrades.py`, `persistence.py`) are low-risk mechanical work. Do this after Phase 4 if the codebase has grown unwieldy, or before if the single-file size is already causing friction.

#### 3b. Replace raw `_pick()` calls with a proper input layer

`_pick()` is called from `do_upgrade_draft()`, `offer_item()`, and `do_merchant()`. An input abstraction layer would make these flows easier to test and would support a future TUI or web interface. Not urgent — defer until after Phase 4.

---

## What NOT to change

- The item class hierarchy (`HealthPotion`, `Weapon`, `Armour`, `Scroll`) is clean — leave it alone.
- `Player` is well-structured — only add Phase 4 fields (`gold`) during the refactor, don't restructure.
- The upgrade system (`_Upgrade` subclasses, `draw_upgrades()`) is well-isolated — move it to its own file but don't rewrite it.
- The floor generator (`generate_floor()`) works correctly — move it but don't touch the algorithm.
- `normalize()` and `ABBREVS` are clean — just add Phase 4 abbreviations (`r`, `b`, `rr`).

---

## Phase 4 Readiness Checklist

After completing Priority 1 and 2 items above, verify these are true before starting Phase 4:

- [ ] `Room.to_dict()` and `Room.from_dict()` exist and include `rest_used` and `merchant_rerolled` fields
- [ ] `Enemy.to_dict()` and `Boss.to_dict()` exist; `load_game()` no longer uses `object.__new__` with raw attribute assignment
- [ ] `handle()` / `dispatch()` uses a result object — no sentinel strings in message lists
- [ ] `on_room_enter(player, room)` and `on_room_exit(player, room)` hooks exist and are called from both transition sites in `run_game()`
- [ ] All output functions live in a renderer module separate from game logic
- [ ] `Player` has a `gold` field initialised to `0`, included in `to_dict` / `from_dict`
- [ ] `Room` has `rest_used = False` and `merchant_rerolled = False` in `__init__`
- [ ] Phase 4 command stubs (`rest`, `buy`, `reroll`) are registered in the dispatcher even if not yet implemented

---

## Estimated Scope

| Task | Effort |
|---|---|
| Room / Enemy / Boss serialization (1a, 1b) | Small — mechanical, low risk |
| Command dispatcher refactor (1c) | Medium — logic stays the same, structure changes |
| Room transition hooks (1d) | Small — two-line extraction, high leverage |
| Renderer extraction (2a) | Small — move functions, no logic changes |
| Combat module extraction (2b) | Trivial — move two functions |
| `offer_item()` split (2c) | Small — extract three branches |
| Full module split (3a) | Medium — mechanical, can be done incrementally |

Priority 1 items can realistically be completed in a single focused session. The entire refactor (Priorities 1 and 2) should not require more than two sessions and should leave all existing game behaviour unchanged.
