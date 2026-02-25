#!/usr/bin/env python3
"""
DUNGEON CRAWLER — Phase 3
Leveling, bosses, inventory, merchant rooms, and save/load.
"""

import random
import sys
import json
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# ── Constants ────────────────────────────────────────────────────────────────

PLAYER_MAX_HP = 100
PLAYER_DMG    = (10, 20)
ROOM_W, ROOM_H = 36, 11
DIRECTIONS    = ('north', 'south', 'east', 'west')
OPPOSITES     = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
DIR_DELTA     = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}
SAVE_FILE     = 'dungeon_save.json'

ENEMY_TIERS = [
    (5, ['Troll', 'Undead Knight', 'Dungeon Horror']),
    (3, ['Orc', 'Shadow Wraith', 'Stone Golem']),
    (1, ['Goblin', 'Rat', 'Skeleton']),
]

BOSS_NAMES = [
    'The Bone Warden', 'Vexoth the Unmade', 'Skarreth the Deep',
    'Nulgrath, Void-touched', 'Xaedron the Ancient',
]

THEMES = [
    ('Damp Cave',         'Water drips from the ceiling. Moss coats the stone walls.'),
    ('Torchlit Corridor', 'Torches flicker on carved stone. Scattered bones crunch underfoot.'),
    ('Forgotten Chamber', 'Crumbling pillars loom in the dust. An eerie silence hangs here.'),
    ('Collapsed Tunnel',  'Rubble chokes the passage. Broken supports lean at odd angles.'),
]

EMPTY_FLAVOUR = [
    "A rat scurries across the floor and vanishes into a crack.",
    "The torchlight casts long shadows across the walls.",
    "Old carvings mark the stone — runes worn smooth by time.",
    "A cold draught passes through. You pull your cloak tighter.",
    "Nothing here but silence and settling dust.",
    "Something glitters briefly in the dark, then is gone.",
    "The smell of old smoke lingers in the air.",
]

WEAPON_POOL = [
    ("Rusty Dagger", 3), ("Short Sword", 5), ("Battle Axe", 8),
    ("Enchanted Blade", 12), ("Shadow Fang", 16), ("Void Cleaver", 20),
]

ARMOUR_POOL = [
    ("Leather Vest", 2), ("Chain Mail", 4), ("Iron Plate", 6),
    ("Enchanted Robe", 8), ("Shadow Shroud", 10), ("Void Carapace", 14),
]

SCROLL_POOL = [
    ('Stun Scroll',    'Stuns the enemy for 1 turn.',      'stun'),
    ('Healing Scroll', 'Restores you to full HP.',          'full_heal'),
    ('Fury Scroll',    'Doubles your damage for 3 turns.',  'double_dmg'),
]

# Single-token command abbreviations
ABBREVS = {
    'a':  'attack',
    'mn': 'move north', 'ms': 'move south',
    'me': 'move east',  'mw': 'move west',
    'm':  'map',
    'l':  'look',
    'h':  'health',
    'd':  'descend',
    'hs': 'heavy strike',
    'i':  'inventory',
    'sv': 'save',
    'ld': 'load',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def hp_bar(current, maximum, width=20):
    filled = round((current / maximum) * width)
    return '█' * filled + '░' * (width - filled)

RULE = '─' * 44

def rule():
    print(RULE)

def say(text: str):
    print(f"  {text}")

def xp_threshold(level: int) -> int:
    return level * 100

def normalize(raw: str) -> str:
    """Expand abbreviations; return lowercased full command string."""
    tokens = raw.strip().lower().split()
    if not tokens:
        return ''
    verb, rest = tokens[0], ' '.join(tokens[1:])
    if verb == 'u':
        return ('use ' + rest).strip()
    if verb == 'eq':
        return ('equip ' + rest).strip()
    if verb in ABBREVS:
        expanded = ABBREVS[verb]
        return (expanded + ' ' + rest).strip() if rest else expanded
    return raw.strip().lower()


# ── Items ─────────────────────────────────────────────────────────────────────

class HealthPotion:
    name = 'Health Potion'
    desc = 'Restores 40 HP'

    def to_dict(self):
        return {'type': 'potion'}

    @staticmethod
    def from_dict(_):
        return HealthPotion()


class Weapon:
    def __init__(self, name, bonus):
        self.name  = name
        self.bonus = bonus
        self.desc  = f'+{bonus} attack'

    def to_dict(self):
        return {'type': 'weapon', 'name': self.name, 'bonus': self.bonus}

    @staticmethod
    def from_dict(d):
        return Weapon(d['name'], d['bonus'])


class Armour:
    def __init__(self, name, bonus):
        self.name  = name
        self.bonus = bonus
        self.desc  = f'+{bonus} defense'

    def to_dict(self):
        return {'type': 'armour', 'name': self.name, 'bonus': self.bonus}

    @staticmethod
    def from_dict(d):
        return Armour(d['name'], d['bonus'])


class Scroll:
    def __init__(self, name, desc, effect):
        self.name   = name
        self.desc   = desc
        self.effect = effect

    def to_dict(self):
        return {'type': 'scroll', 'name': self.name,
                'desc': self.desc, 'effect': self.effect}

    @staticmethod
    def from_dict(d):
        return Scroll(d['name'], d['desc'], d['effect'])


def item_from_dict(d):
    if d is None:
        return None
    t = d['type']
    if t == 'potion': return HealthPotion.from_dict(d)
    if t == 'weapon': return Weapon.from_dict(d)
    if t == 'armour': return Armour.from_dict(d)
    if t == 'scroll': return Scroll.from_dict(d)
    return None


def random_item(floor_num=1):
    """Generate a random item scaled loosely to floor depth."""
    roll = random.random()
    if roll < 0.35:
        return HealthPotion()
    elif roll < 0.55:
        idx  = min(floor_num - 1, len(WEAPON_POOL) - 1)
        name, bonus = random.choice(WEAPON_POOL[:idx + 1])
        return Weapon(name, bonus)
    elif roll < 0.75:
        idx  = min(floor_num - 1, len(ARMOUR_POOL) - 1)
        name, bonus = random.choice(ARMOUR_POOL[:idx + 1])
        return Armour(name, bonus)
    else:
        name, desc, effect = random.choice(SCROLL_POOL)
        return Scroll(name, desc, effect)


# ── Player ────────────────────────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.hp         = PLAYER_MAX_HP
        self.max_hp     = PLAYER_MAX_HP
        self.level      = 1
        self.xp         = 0
        self.defense    = 0
        self.atk_bonus  = 0
        self.hs_unlocked = False
        self.hs_cooldown = 0       # turns until usable
        self.hs_max_cd   = 3
        self.double_dmg  = 0       # turns of double damage remaining
        self.weapon      = None    # Weapon or None
        self.armour      = None    # Armour or None
        self.consumables = []      # max 3

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, raw_amount):
        """Apply defense reduction, return actual damage taken."""
        actual = max(0, raw_amount - self.defense)
        self.hp = max(0, self.hp - actual)
        return actual

    def full_heal(self):
        self.hp = self.max_hp

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def roll_attack(self):
        dmg = random.randint(PLAYER_DMG[0] + self.atk_bonus,
                             PLAYER_DMG[1] + self.atk_bonus)
        return dmg * 2 if self.double_dmg > 0 else dmg

    def roll_heavy(self):
        lo = (PLAYER_DMG[0] + self.atk_bonus) * 2
        hi = (PLAYER_DMG[1] + self.atk_bonus) * 3
        dmg = random.randint(lo, hi)
        return dmg * 2 if self.double_dmg > 0 else dmg

    def tick(self):
        """Decrement per-turn cooldowns."""
        if self.hs_cooldown > 0:
            self.hs_cooldown -= 1
        if self.double_dmg > 0:
            self.double_dmg -= 1

    def add_xp(self, amount):
        """Award XP, return list of new levels reached."""
        self.xp += amount
        gained = []
        while self.xp >= xp_threshold(self.level):
            self.xp -= xp_threshold(self.level)
            self.level += 1
            gained.append(self.level)
        return gained

    def to_dict(self):
        return {
            'hp': self.hp, 'max_hp': self.max_hp,
            'level': self.level, 'xp': self.xp,
            'defense': self.defense, 'atk_bonus': self.atk_bonus,
            'hs_unlocked': self.hs_unlocked,
            'hs_cooldown': self.hs_cooldown, 'hs_max_cd': self.hs_max_cd,
            'double_dmg': self.double_dmg,
            'weapon':      self.weapon.to_dict() if self.weapon else None,
            'armour':      self.armour.to_dict() if self.armour else None,
            'consumables': [c.to_dict() for c in self.consumables],
        }

    @staticmethod
    def from_dict(d):
        p = Player()
        p.hp = d['hp']; p.max_hp = d['max_hp']
        p.level = d['level']; p.xp = d['xp']
        p.defense = d['defense']; p.atk_bonus = d['atk_bonus']
        p.hs_unlocked = d['hs_unlocked']
        p.hs_cooldown = d['hs_cooldown']; p.hs_max_cd = d['hs_max_cd']
        p.double_dmg  = d['double_dmg']
        p.weapon      = item_from_dict(d['weapon'])
        p.armour      = item_from_dict(d['armour'])
        p.consumables = [item_from_dict(c) for c in d['consumables']]
        return p


# ── Enemy ─────────────────────────────────────────────────────────────────────

class Enemy:
    def __init__(self, floor_num):
        self.max_hp  = 30 + (floor_num - 1) * 10
        self.hp      = self.max_hp
        self.dmg_min = 5  + (floor_num - 1) * 2
        self.dmg_max = 15 + (floor_num - 1) * 3
        self._name   = self._pick_name(floor_num)
        self.stunned = False

    @staticmethod
    def _pick_name(floor_num):
        for threshold, names in ENEMY_TIERS:
            if floor_num >= threshold:
                return random.choice(names)
        return 'Goblin'

    @property
    def name(self):
        return self._name

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def roll_damage(self):
        return random.randint(self.dmg_min, self.dmg_max)

    def xp_value(self, floor_num):
        return 10 + floor_num * 5


# ── Boss ──────────────────────────────────────────────────────────────────────

class Boss(Enemy):
    def __init__(self, floor_num, boss_num):
        self.floor_num = floor_num
        self.boss_num  = boss_num
        base_hp  = 30 + (floor_num - 1) * 10
        base_min = 5  + (floor_num - 1) * 2
        base_max = 15 + (floor_num - 1) * 3
        self.max_hp  = int(base_hp  * 2.5)
        self.hp      = self.max_hp
        self.dmg_min = int(base_min * 2.5)
        self.dmg_max = int(base_max * 2.5)
        self._name   = BOSS_NAMES[(boss_num - 1) % len(BOSS_NAMES)]
        self.stunned = False
        self.phase   = 1
        self.phase2_threshold = self.max_hp // 2
        self.telegraphing     = False   # winding up for a big hit

    @property
    def name(self):
        phase_tag = ' [Phase 2]' if self.phase == 2 else ''
        return f"{self._name}{phase_tag}"

    def check_phase_transition(self):
        """Returns True if boss just dropped into phase 2."""
        if self.phase == 1 and self.hp <= self.phase2_threshold:
            self.phase = 2
            return True
        return False

    def xp_value(self, floor_num):
        return 50 + floor_num * 20


# ── Room ──────────────────────────────────────────────────────────────────────

class Room:
    def __init__(self, col, row, room_type, theme_name, theme_desc, floor_num):
        self.col        = col
        self.row        = row
        self.type       = room_type   # enemy|empty|staircase|boss|merchant
        self.theme_name = theme_name
        self.theme_desc = theme_desc
        self.exits      = {}
        self.visited    = False
        self.item       = None        # ground item (empty rooms, drops)
        self.merchant_items = []
        self.merchant_done  = False
        self.flavour    = (random.choice(EMPTY_FLAVOUR)
                           if room_type in ('empty', 'staircase') else None)
        if room_type == 'enemy':
            self.enemy = Enemy(floor_num)
        else:
            self.enemy = None   # Boss is set after construction


# ── Upgrade System ────────────────────────────────────────────────────────────

class _Upgrade:
    def __init__(self, cat, label, desc):
        self.cat   = cat
        self.label = label
        self.desc  = desc

    def apply(self, player):
        pass


class _HPUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('hp', f'+{amount} Max HP', f'Maximum health increases by {amount}.')
        self.amount = amount

    def apply(self, player):
        player.max_hp += self.amount
        player.hp = min(player.hp + self.amount, player.max_hp)


class _AtkUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('atk', f'+{amount} Attack', f'Attacks deal {amount} more damage.')
        self.amount = amount

    def apply(self, player):
        player.atk_bonus += self.amount


class _DefUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('def', f'+{amount} Defense', f'Incoming damage reduced by {amount}.')
        self.amount = amount

    def apply(self, player):
        player.defense += self.amount


class _HSUpgrade(_Upgrade):
    def __init__(self, is_unlock):
        if is_unlock:
            super().__init__('hs', 'Unlock Heavy Strike',
                             'Learn a devastating heavy attack (3-turn cooldown).')
        else:
            super().__init__('hs', 'Improve Heavy Strike',
                             'Heavy Strike cooldown reduced by 1 turn.')
        self.is_unlock = is_unlock

    def apply(self, player):
        if self.is_unlock:
            player.hs_unlocked = True
        else:
            player.hs_max_cd = max(1, player.hs_max_cd - 1)


def draw_upgrades(player, count=3):
    """Return `count` upgrades ensuring category variety."""
    cats = {
        'hp':  [_HPUpgrade(20), _HPUpgrade(30)],
        'atk': [_AtkUpgrade(5), _AtkUpgrade(8)],
        'def': [_DefUpgrade(2), _DefUpgrade(3)],
    }
    if not player.hs_unlocked:
        cats['hs'] = [_HSUpgrade(True)]
    elif player.hs_max_cd > 1:
        cats['hs'] = [_HSUpgrade(False)]

    keys = list(cats.keys())
    random.shuffle(keys)
    chosen = []
    for cat in keys:
        if len(chosen) >= count:
            break
        chosen.append(random.choice(cats[cat]))
    # Fill any remaining slots
    while len(chosen) < count:
        cat = random.choice(list(cats.keys()))
        chosen.append(random.choice(cats[cat]))
    random.shuffle(chosen)
    return chosen[:count]


# ── Floor Generator ───────────────────────────────────────────────────────────

def _floor_room_count(floor_num):
    if floor_num == 1:   base = 6
    elif floor_num == 2: base = 8
    elif floor_num <= 4: base = 10 + (floor_num - 3) * 2
    else:                base = min(14 + (floor_num - 5) * 2, 18)
    return max(4, base + random.randint(-2, 2))


def generate_floor(floor_num):
    """
    Generate a connected floor.
    Returns (rooms_list, start_room, boss_room).
    boss_room is None on non-boss floors.
    """
    is_boss_floor = (floor_num % 3 == 0)
    boss_num      = floor_num // 3
    count         = _floor_room_count(floor_num)

    # Random walk to place positions
    positions = [(0, 0)]
    pos_set   = {(0, 0)}
    while len(positions) < count:
        col, row = random.choice(positions)
        deltas   = list(DIR_DELTA.values())
        random.shuffle(deltas)
        for dc, dr in deltas:
            npos = (col + dc, row + dr)
            if npos not in pos_set:
                pos_set.add(npos)
                positions.append(npos)
                break

    # Assign types
    non_start = positions[1:]
    stair_pos = random.choice(non_start)
    boss_pos  = None
    if is_boss_floor:
        candidates = [p for p in non_start if p != stair_pos]
        if candidates:
            boss_pos = random.choice(candidates)

    type_map = {(0, 0): 'empty', stair_pos: 'staircase'}
    if boss_pos:
        type_map[boss_pos] = 'boss'
    for pos in non_start:
        if pos not in type_map:
            roll = random.random()
            if roll < 0.05:
                type_map[pos] = 'merchant'
            elif roll < 0.65:
                type_map[pos] = 'enemy'
            else:
                type_map[pos] = 'empty'

    # Build Room objects
    rooms_by_pos = {}
    for col, row in positions:
        theme_name, theme_desc = random.choice(THEMES)
        rtype = type_map[(col, row)]
        room  = Room(col, row, rtype, theme_name, theme_desc, floor_num)
        if rtype == 'boss':
            room.enemy = Boss(floor_num, boss_num)
        if rtype == 'merchant':
            room.merchant_items = [random_item(floor_num)
                                   for _ in range(random.randint(2, 3))]
        if rtype == 'empty' and random.random() < 0.3:
            room.item = random_item(floor_num)
        rooms_by_pos[(col, row)] = room

    # BFS spanning tree
    visited_bfs = {(0, 0)}
    queue       = [(0, 0)]
    while queue:
        pos      = queue.pop(0)
        col, row = pos
        dirs     = list(DIR_DELTA.items())
        random.shuffle(dirs)
        for d, (dc, dr) in dirs:
            npos = (col + dc, row + dr)
            if npos in rooms_by_pos and npos not in visited_bfs:
                visited_bfs.add(npos)
                queue.append(npos)
                r1, r2 = rooms_by_pos[pos], rooms_by_pos[npos]
                r1.exits[d] = r2
                r2.exits[OPPOSITES[d]] = r1

    # Extra connections
    for (col, row), room in rooms_by_pos.items():
        for d, (dc, dr) in DIR_DELTA.items():
            npos = (col + dc, row + dr)
            if npos in rooms_by_pos and d not in room.exits:
                if random.random() < 0.35:
                    nb = rooms_by_pos[npos]
                    room.exits[d] = nb
                    nb.exits[OPPOSITES[d]] = room

    rooms      = list(rooms_by_pos.values())
    start_room = rooms_by_pos[(0, 0)]
    boss_room  = rooms_by_pos.get(boss_pos) if boss_pos else None
    return rooms, start_room, boss_room


# ── ASCII Map ─────────────────────────────────────────────────────────────────

def draw_map(rooms, current_room, player, floor_num):
    visited = [r for r in rooms if r.visited]
    if not visited:
        say("(No rooms explored yet.)")
        return

    min_col = min(r.col for r in visited)
    max_col = max(r.col for r in visited)
    min_row = min(r.row for r in visited)
    max_row = max(r.row for r in visited)
    room_at = {(r.col, r.row): r for r in visited}

    def sym(r):
        if r is current_room:
            return '[*]'
        if r.type == 'staircase':
            return '[S]'
        if r.type == 'boss':
            return '[B]' if (r.enemy and r.enemy.alive) else '[ ]'
        if r.type == 'merchant':
            return '[M]'
        if r.type == 'enemy' and r.enemy and r.enemy.alive:
            return '[E]'
        return '[ ]'

    print()
    say(f"Floor {floor_num} — Level {player.level}")
    print()
    for row in range(min_row, max_row + 1):
        room_line = ''
        conn_line = ''
        for col in range(min_col, max_col + 1):
            r = room_at.get((col, row))
            if r is None:
                room_line += '      '
                conn_line += '      '
            else:
                s      = sym(r)
                east_r = room_at.get((col + 1, row))
                e_conn = ' - ' if east_r is not None and 'east' in r.exits else '   '
                room_line += s + e_conn
                south_r = room_at.get((col, row + 1))
                s_conn  = ' | ' if south_r is not None and 'south' in r.exits else '   '
                conn_line += s_conn + '   '
        print('  ' + room_line.rstrip())
        if row < max_row:
            print('  ' + conn_line.rstrip())

    print()
    say("Legend: [*]=You  [ ]=Visited  [S]=Staircase  [E]=Enemy  [B]=Boss  [M]=Merchant")
    print()


# ── Status Line ───────────────────────────────────────────────────────────────

def status_line(player, floor_num):
    thresh = xp_threshold(player.level)
    parts  = [
        f"Floor {floor_num}",
        f"Lv {player.level}",
        f"HP: {player.hp}/{player.max_hp}",
        f"XP: {player.xp}/{thresh}",
    ]
    if player.defense  > 0:           parts.append(f"DEF: {player.defense}")
    if player.atk_bonus > 0:          parts.append(f"ATK: +{player.atk_bonus}")
    if player.hs_unlocked:
        parts.append(f"HS: {'ready' if player.hs_cooldown == 0 else str(player.hs_cooldown) + 't'}")
    if player.double_dmg > 0:         parts.append(f"FURY: {player.double_dmg}t")
    return " | ".join(parts)


# ── Room Renderer ─────────────────────────────────────────────────────────────

def draw_room(player, room, floor_num):
    W, H  = ROOM_W, ROOM_H
    grid  = [[' '] * W for _ in range(H)]
    grid[H // 2][W // 2] = 'P'
    if room.enemy and room.enemy.alive:
        grid[H // 4][W // 4] = 'E'

    inner = W + 2
    mid   = inner // 2
    has   = {d: d in room.exits for d in DIRECTIONS}
    n_ch  = 'N' if has['north'] else '─'
    s_ch  = 'S' if has['south'] else '─'
    top   = '+' + '─' * (mid - 1) + n_ch + '─' * (inner - mid) + '+'
    bot   = '+' + '─' * (mid - 1) + s_ch + '─' * (inner - mid) + '+'

    print(top)
    for i, row_data in enumerate(grid):
        content = ''.join(row_data)
        if i == H // 2:
            w_ch = 'W' if has['west'] else '│'
            e_ch = 'E' if has['east'] else '│'
            print(f"{w_ch} {content} {e_ch}")
        else:
            print('│ ' + content + ' │')
    print(bot)

    print(f"\n  {status_line(player, floor_num)}")

    if room.enemy and room.enemy.alive:
        e_bar = hp_bar(room.enemy.hp, room.enemy.max_hp)
        print(f"  [E] {room.enemy.name:<24} HP: [{e_bar}] {room.enemy.hp}/{room.enemy.max_hp}")
        if isinstance(room.enemy, Boss) and room.enemy.telegraphing:
            print("      *** WINDING UP FOR A DEVASTATING BLOW — BRACE YOURSELF! ***")

    TYPE_LABELS = {
        'enemy': 'Enemy Room', 'empty': 'Empty Room', 'staircase': 'Staircase',
        'boss': 'Boss Chamber', 'merchant': 'Merchant Room',
    }
    print(f"  {room.theme_name} — {TYPE_LABELS.get(room.type, '')}")
    exits_str = ', '.join(d for d in DIRECTIONS if d in room.exits) or 'none'
    print(f"  Exits: {exits_str}")
    print()


# ── Combat Runners ────────────────────────────────────────────────────────────

def run_enemy_turn(enemy, player, msgs):
    if enemy.stunned:
        enemy.stunned = False
        msgs.append(f"The {enemy.name} is stunned and cannot attack!")
        return
    dmg_raw  = enemy.roll_damage()
    dmg_took = player.take_damage(dmg_raw)
    msgs.append(f"The {enemy.name} strikes back for {dmg_took} damage!")


def run_boss_turn(boss, player, msgs):
    if boss.stunned:
        boss.stunned     = False
        boss.telegraphing = False   # stun cancels wind-up
        msgs.append(f"{boss._name} is stunned and cannot attack!")
        return

    if boss.telegraphing:
        dmg_raw  = boss.dmg_max * 3
        dmg_took = player.take_damage(dmg_raw)
        msgs.append(f"{boss._name}'s DEVASTATING BLOW strikes you for {dmg_took} damage!")
        boss.telegraphing = False
        return

    # Normal attack; phase 2 = twice
    attacks = 2 if boss.phase == 2 else 1
    for _ in range(attacks):
        dmg_raw  = boss.roll_damage()
        dmg_took = player.take_damage(dmg_raw)
        msgs.append(f"{boss._name} strikes you for {dmg_took} damage!")
        if not player.alive:
            return

    # Maybe wind up a telegraphed attack (boss 2+)
    if boss.boss_num >= 2 and not boss.telegraphing and random.random() < 0.3:
        boss.telegraphing = True
        msgs.append(f"{boss._name} winds up for a devastating blow... BRACE YOURSELF!")


# ── Interactive Sub-flows ─────────────────────────────────────────────────────

def _pick(prompt, lo, hi):
    """Ask the player for an integer in [lo, hi]. Returns int."""
    while True:
        try:
            raw = input(f"  {prompt} ").strip()
        except (EOFError, KeyboardInterrupt):
            return lo
        if raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        say(f"Please enter a number between {lo} and {hi}.")


def do_upgrade_draft(player, new_level):
    print()
    say(f"★  LEVEL UP!  You are now Level {new_level}!  ★")
    print()
    upgrades = draw_upgrades(player)
    say("Choose an upgrade:")
    for i, upg in enumerate(upgrades, 1):
        say(f"  {i}. {upg.label} — {upg.desc}")
    choice = _pick("Your choice (1-3):", 1, len(upgrades))
    chosen = upgrades[choice - 1]
    chosen.apply(player)
    say(f"→ {chosen.label} applied!")
    print()


def offer_item(player, item, source=''):
    """
    Offer one item to the player.  Handles slot management.
    Returns True if the item was taken.
    """
    if isinstance(item, (HealthPotion, Scroll)):
        label = f"{item.name} ({item.desc})"
        if source:
            say(f"You found: {label}.")
        if len(player.consumables) < 3:
            player.consumables.append(item)
            say(f"{item.name} added to consumables ({len(player.consumables)}/3).")
            return True
        # Full — ask to discard
        say("Consumable slots are full (3/3).")
        say("Consumables:")
        for i, c in enumerate(player.consumables, 1):
            say(f"  {i}. {c.name}")
        say(f"  4. Leave {item.name}")
        choice = _pick("Discard which? (1-4):", 1, 4)
        if choice == 4:
            say(f"You leave the {item.name}.")
            return False
        old = player.consumables[choice - 1]
        player.consumables[choice - 1] = item
        say(f"Discarded {old.name}. Picked up {item.name}.")
        return True

    elif isinstance(item, Weapon):
        if source:
            say(f"You found: {item.name} ({item.desc}).")
        if player.weapon is None:
            player.weapon   = item
            player.atk_bonus += item.bonus
            say(f"Equipped {item.name} (+{item.bonus} ATK).")
            return True
        say(f"You already have {player.weapon.name} (+{player.weapon.bonus} ATK).")
        say(f"Equip {item.name} (+{item.bonus} ATK) instead? (1=Yes, 2=No)")
        if _pick("Choice:", 1, 2) == 1:
            player.atk_bonus -= player.weapon.bonus
            player.weapon     = item
            player.atk_bonus += item.bonus
            say(f"Equipped {item.name}.")
            return True
        say(f"You leave the {item.name}.")
        return False

    elif isinstance(item, Armour):
        if source:
            say(f"You found: {item.name} ({item.desc}).")
        if player.armour is None:
            player.armour    = item
            player.defense  += item.bonus
            say(f"Equipped {item.name} (+{item.bonus} DEF).")
            return True
        say(f"You already have {player.armour.name} (+{player.armour.bonus} DEF).")
        say(f"Equip {item.name} (+{item.bonus} DEF) instead? (1=Yes, 2=No)")
        if _pick("Choice:", 1, 2) == 1:
            player.defense  -= player.armour.bonus
            player.armour    = item
            player.defense  += item.bonus
            say(f"Equipped {item.name}.")
            return True
        say(f"You leave the {item.name}.")
        return False

    return False


def do_merchant(room, player, floor_num):
    if room.merchant_done:
        say("The merchant's stock is exhausted.")
        return
    print()
    say("A hooded merchant eyes you from the shadows.")
    say("'Choose one item — free of charge. I've no use for them here.'")
    print()
    for i, item in enumerate(room.merchant_items, 1):
        say(f"  {i}. {item.name} — {item.desc}")
    n = len(room.merchant_items)
    say(f"  {n + 1}. Take nothing")
    choice = _pick(f"Your choice (1-{n + 1}):", 1, n + 1)
    if choice == n + 1:
        say("You leave the merchant's wares untouched.")
    else:
        item = room.merchant_items[choice - 1]
        offer_item(player, item)
    room.merchant_done = True
    print()


# ── Save / Load ───────────────────────────────────────────────────────────────

def save_game(player, rooms, current_room, floor_num, boss_room):
    rooms_data = []
    for r in rooms:
        ed = None
        if r.enemy:
            ed = {
                'is_boss': isinstance(r.enemy, Boss),
                'hp': r.enemy.hp, 'max_hp': r.enemy.max_hp,
                'dmg_min': r.enemy.dmg_min, 'dmg_max': r.enemy.dmg_max,
                'name': r.enemy._name, 'stunned': r.enemy.stunned,
            }
            if isinstance(r.enemy, Boss):
                ed.update({
                    'boss_num': r.enemy.boss_num,
                    'floor_num': r.enemy.floor_num,
                    'phase': r.enemy.phase,
                    'phase2_threshold': r.enemy.phase2_threshold,
                    'telegraphing': r.enemy.telegraphing,
                })
        rooms_data.append({
            'col': r.col, 'row': r.row, 'type': r.type,
            'theme_name': r.theme_name, 'theme_desc': r.theme_desc,
            'visited': r.visited, 'flavour': r.flavour,
            'exits': {d: [nr.col, nr.row] for d, nr in r.exits.items()},
            'item': r.item.to_dict() if r.item else None,
            'merchant_items': [i.to_dict() for i in r.merchant_items],
            'merchant_done': r.merchant_done,
            'enemy': ed,
        })
    data = {
        'floor_num': floor_num,
        'current_room': [current_room.col, current_room.row],
        'boss_room': [boss_room.col, boss_room.row] if boss_room else None,
        'player': player.to_dict(),
        'rooms': rooms_data,
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_game():
    """Returns (player, rooms, current_room, floor_num, boss_room) or None."""
    if not os.path.exists(SAVE_FILE):
        return None
    with open(SAVE_FILE) as f:
        data = json.load(f)

    # First pass: build room objects (no exits yet)
    rooms_by_pos = {}
    for rd in data['rooms']:
        r = object.__new__(Room)
        r.col = rd['col']; r.row = rd['row']
        r.type = rd['type']
        r.theme_name = rd['theme_name']; r.theme_desc = rd['theme_desc']
        r.visited = rd['visited']; r.flavour = rd['flavour']
        r.exits = {}
        r.item  = item_from_dict(rd['item'])
        r.merchant_items = [item_from_dict(i) for i in rd['merchant_items']]
        r.merchant_done  = rd['merchant_done']
        r.enemy = None
        ed = rd['enemy']
        if ed:
            if ed['is_boss']:
                b = object.__new__(Boss)
                b.hp = ed['hp']; b.max_hp = ed['max_hp']
                b.dmg_min = ed['dmg_min']; b.dmg_max = ed['dmg_max']
                b._name = ed['name']; b.stunned = ed['stunned']
                b.boss_num = ed['boss_num']; b.floor_num = ed['floor_num']
                b.phase = ed['phase']
                b.phase2_threshold = ed['phase2_threshold']
                b.telegraphing = ed['telegraphing']
                r.enemy = b
            else:
                e = object.__new__(Enemy)
                e.hp = ed['hp']; e.max_hp = ed['max_hp']
                e.dmg_min = ed['dmg_min']; e.dmg_max = ed['dmg_max']
                e._name = ed['name']; e.stunned = ed['stunned']
                r.enemy = e
        rooms_by_pos[(r.col, r.row)] = r

    # Second pass: link exits
    for rd in data['rooms']:
        r = rooms_by_pos[(rd['col'], rd['row'])]
        for d, (nc, nr) in rd['exits'].items():
            r.exits[d] = rooms_by_pos[(nc, nr)]

    rooms        = list(rooms_by_pos.values())
    current_room = rooms_by_pos[tuple(data['current_room'])]
    boss_room    = (rooms_by_pos[tuple(data['boss_room'])]
                    if data['boss_room'] else None)
    player       = Player.from_dict(data['player'])
    floor_num    = data['floor_num']
    return player, rooms, current_room, floor_num, boss_room


# ── Command Handler ───────────────────────────────────────────────────────────

def handle(raw, player, room, floor_num, boss_room=None):
    """
    Returns (turn_used, messages, new_room, descended).
    Special sentinel messages: '__map__', '__save__', '__load__'.
    """
    tokens = raw.strip().lower().split()
    if not tokens:
        return False, ['(nothing)'], None, False
    verb = tokens[0]

    # ── attack ────────────────────────────────────────────────────────────────
    if verb == 'attack':
        enemy = room.enemy
        if not enemy or not enemy.alive:
            return False, ['There is nothing to attack.'], None, False
        dmg  = player.roll_attack()
        enemy.take_damage(dmg)
        msgs = [f"You strike the {enemy.name} for {dmg} damage!"]
        if not enemy.alive:
            msgs.append(f"The {enemy._name} crumples to the ground. Victory!")
            msgs.append("You catch your breath and recover fully.")
        else:
            msgs.append(f"The {enemy.name} staggers — {enemy.hp}/{enemy.max_hp} HP.")
        return True, msgs, None, False

    # ── heavy strike ──────────────────────────────────────────────────────────
    if verb == 'heavy' and len(tokens) >= 2 and tokens[1] == 'strike':
        if not player.hs_unlocked:
            return False, ['Heavy Strike is not unlocked. Level up to learn it.'], None, False
        if player.hs_cooldown > 0:
            return False, [f"Heavy Strike is on cooldown ({player.hs_cooldown} turn(s) remaining)."], None, False
        enemy = room.enemy
        if not enemy or not enemy.alive:
            return False, ['There is nothing to attack.'], None, False
        dmg  = player.roll_heavy()
        enemy.take_damage(dmg)
        player.hs_cooldown = player.hs_max_cd
        msgs = [f"HEAVY STRIKE! You slam the {enemy.name} for {dmg} damage!"]
        if not enemy.alive:
            msgs.append(f"The {enemy._name} is obliterated. Victory!")
            msgs.append("You catch your breath and recover fully.")
        else:
            msgs.append(f"The {enemy.name} reels — {enemy.hp}/{enemy.max_hp} HP.")
        return True, msgs, None, False

    # ── move ──────────────────────────────────────────────────────────────────
    if verb == 'move':
        if len(tokens) < 2 or tokens[1] not in DIRECTIONS:
            return False, [f"Move where? ({', '.join(DIRECTIONS)})"], None, False
        direction = tokens[1]
        if direction not in room.exits:
            return False, [f"There is no door to the {direction}."], None, False
        if room.enemy and room.enemy.alive:
            return False, [f"You can't leave — {room.enemy.name} blocks the way!"], None, False
        return False, [f"You move {direction}."], room.exits[direction], False

    # ── look ──────────────────────────────────────────────────────────────────
    if verb == 'look':
        if room.type == 'boss':
            msgs = ["The chamber reeks of blood. Shadows writhe on the walls."]
        else:
            msgs = [f"{room.theme_name}: {room.theme_desc}"]
        if room.type == 'staircase':
            msgs.append("A stone staircase descends into the darkness below.")
            if boss_room and boss_room.enemy and boss_room.enemy.alive:
                msgs.append("The staircase is sealed — defeat the boss first.")
        elif room.type == 'merchant':
            msgs.append("A hooded merchant sits quietly in the corner.")
        elif room.flavour:
            msgs.append(room.flavour)
        if room.enemy and room.enemy.alive:
            msgs.append(f"{room.enemy.name} ({room.enemy.hp}/{room.enemy.max_hp} HP) faces you.")
        if room.item:
            msgs.append(f"There is a {room.item.name} on the ground.")
        exits = ', '.join(d for d in DIRECTIONS if d in room.exits) or 'none'
        msgs.append(f"Exits: {exits}")
        return False, msgs, None, False

    # ── health ────────────────────────────────────────────────────────────────
    if verb == 'health':
        return False, [f"You check yourself: {player.hp}/{player.max_hp} HP."], None, False

    # ── inventory ─────────────────────────────────────────────────────────────
    if verb == 'inventory':
        msgs = ['── Inventory ──']
        msgs.append(f"Weapon : {player.weapon.name + ' (+' + str(player.weapon.bonus) + ' ATK)' if player.weapon else 'none'}")
        msgs.append(f"Armour : {player.armour.name + ' (+' + str(player.armour.bonus) + ' DEF)' if player.armour else 'none'}")
        if player.consumables:
            for i, c in enumerate(player.consumables, 1):
                msgs.append(f"  [{i}] {c.name} — {c.desc}")
        else:
            msgs.append("  Consumables: empty")
        msgs.append(f"Level {player.level} | XP: {player.xp}/{xp_threshold(player.level)}")
        if player.hs_unlocked:
            cd = f"{player.hs_cooldown}t cooldown" if player.hs_cooldown else "ready"
            msgs.append(f"Heavy Strike: unlocked ({cd}, max cooldown {player.hs_max_cd}t)")
        return False, msgs, None, False

    # ── use ───────────────────────────────────────────────────────────────────
    if verb == 'use':
        if len(tokens) < 2:
            return False, ['Use what? (e.g. use potion, use 1)'], None, False
        target = tokens[1]
        if not player.consumables:
            return False, ['You have no consumables.'], None, False
        # Match by slot number or name keyword
        item = idx = None
        if target.isdigit():
            i = int(target) - 1
            if 0 <= i < len(player.consumables):
                item, idx = player.consumables[i], i
        else:
            for i, c in enumerate(player.consumables):
                if target in c.name.lower():
                    item, idx = c, i
                    break
        if item is None:
            return False, [f"No item matching '{target}'. Check 'inventory'."], None, False
        msgs = []
        enemy = room.enemy
        if isinstance(item, HealthPotion):
            before = player.hp
            player.heal(40)
            msgs.append(f"You drink the {item.name}, restoring {player.hp - before} HP.")
        elif isinstance(item, Scroll):
            if item.effect == 'full_heal':
                player.full_heal()
                msgs.append("The Healing Scroll washes over you. HP fully restored!")
            elif item.effect == 'stun':
                if not enemy or not enemy.alive:
                    return False, ['There is no enemy to stun.'], None, False
                enemy.stunned = True
                msgs.append(f"The Stun Scroll crackles! {enemy.name} is stunned for 1 turn.")
            elif item.effect == 'double_dmg':
                player.double_dmg = 3
                msgs.append("The Fury Scroll ignites your veins — double damage for 3 turns!")
        player.consumables.pop(idx)
        return False, msgs, None, False

    # ── equip ─────────────────────────────────────────────────────────────────
    if verb == 'equip':
        # Equip the item on the ground in the current room (if gear)
        if not room.item:
            return False, ['There is nothing on the ground to equip.'], None, False
        if not isinstance(room.item, (Weapon, Armour)):
            return False, [f"You cannot equip {room.item.name}."], None, False
        taken = offer_item(player, room.item)
        if taken:
            room.item = None
        return False, [], None, False

    # ── descend ───────────────────────────────────────────────────────────────
    if verb == 'descend':
        if room.type != 'staircase':
            return False, ['There is no staircase here.'], None, False
        if room.enemy and room.enemy.alive:
            return False, [f"You can't descend — {room.enemy.name} blocks the staircase!"], None, False
        if boss_room and boss_room.enemy and boss_room.enemy.alive:
            return False, ['The staircase is sealed. Defeat the boss first!'], None, False
        return False, ['You descend the staircase into deeper darkness...'], None, True

    # ── map ───────────────────────────────────────────────────────────────────
    if verb == 'map':
        return False, ['__map__'], None, False

    # ── save ──────────────────────────────────────────────────────────────────
    if verb == 'save':
        can = (room.type == 'empty' or
               (room.type == 'boss' and room.enemy and not room.enemy.alive))
        if not can:
            return False, ['You can only save in empty rooms or after defeating a boss.'], None, False
        return False, ['__save__'], None, False

    # ── load ──────────────────────────────────────────────────────────────────
    if verb == 'load':
        return False, ['__load__'], None, False

    # ── quit ──────────────────────────────────────────────────────────────────
    if verb in ('quit', 'exit', 'q'):
        print("\n  You retreat into the darkness. Farewell.\n")
        sys.exit(0)

    # ── help ──────────────────────────────────────────────────────────────────
    if verb in ('help', '?'):
        say("Commands: attack (a) | heavy strike (hs) | move <dir> (mn/ms/me/mw)")
        say("          look (l) | health (h) | inventory (i) | use <item> (u)")
        say("          equip | descend (d) | map (m) | save (sv) | load (ld) | quit")
        return False, [], None, False

    return False, [f"Unknown command '{raw}'. Type 'help' for options."], None, False


# ── Screens ───────────────────────────────────────────────────────────────────

def intro_screen():
    print()
    print("  ╔════════════════════════════════════════╗")
    print("  ║     D U N G E O N   C R A W L E R     ║")
    print("  ╚════════════════════════════════════════╝")
    print()
    say("You stand at the entrance to a forsaken dungeon.")
    say("Darkness stretches ahead. Danger — and power — lie deeper.")
    print()
    say("Commands: attack (a) | heavy strike (hs) | move <dir> (mn/ms/me/mw)")
    say("          look (l) | health (h) | inventory (i) | use <item> (u)")
    say("          descend (d) | map (m) | save (sv) | load (ld) | quit")
    print()


def game_over_screen(floor_num):
    print()
    print("  ╔═══════════════════════╗")
    print("  ║    G A M E  O V E R  ║")
    print("  ╚═══════════════════════╝")
    say(f"You fell on floor {floor_num}.")
    print()


def ask_restart():
    while True:
        try:
            ans = input("  Play again? (yes / no) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if ans in ('yes', 'y'): return True
        if ans in ('no', 'n'):  return False
        say("Please type yes or no.")


def announce_room(room, boss_room=None):
    if room.type == 'boss':
        say("The air turns cold. The walls tremble with dread.")
        say(f"*** {room.enemy._name} awaits! ***")
    elif room.type == 'merchant':
        say("A faint lantern flickers. A hunched merchant sits in the corner.")
    else:
        say(f"{room.theme_name}: {room.theme_desc}")
        if room.type == 'staircase':
            locked = boss_room and boss_room.enemy and boss_room.enemy.alive
            if locked:
                say("A stone staircase — sealed until the boss is defeated.")
            else:
                say("A stone staircase descends into the darkness. (type 'descend')")
        elif room.flavour:
            say(room.flavour)
        if room.item:
            say(f"There is a {room.item.name} on the ground.")
    if room.enemy and room.enemy.alive and room.type != 'boss':
        say(f"A {room.enemy.name} snarls at you!")


# ── Game Session ──────────────────────────────────────────────────────────────

def run_game():
    player    = Player()
    floor_num = 1
    rooms, current_room, boss_room = generate_floor(floor_num)
    current_room.visited = True

    intro_screen()
    rule()
    say(f"Floor {floor_num}. You enter the dungeon.")
    announce_room(current_room, boss_room)
    print()
    rule()
    draw_room(player, current_room, floor_num)
    rule()

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Interrupted. Farewell.\n")
            sys.exit(0)

        raw = normalize(raw)

        enemy_was_alive = bool(current_room.enemy and current_room.enemy.alive)
        turn_used, msgs, new_room, descended = handle(
            raw, player, current_room, floor_num, boss_room)

        # ── Boss phase check (before retaliation so phase 2 attacks twice now) ─
        if (turn_used and current_room.enemy
                and isinstance(current_room.enemy, Boss)
                and current_room.enemy.alive
                and current_room.enemy.check_phase_transition()):
            msgs.append(f"*** {current_room.enemy._name} ENTERS PHASE 2 — it attacks twice per turn! ***")

        # ── Enemy / boss retaliation ──────────────────────────────────────────
        if turn_used and current_room.enemy and current_room.enemy.alive:
            if isinstance(current_room.enemy, Boss):
                run_boss_turn(current_room.enemy, player, msgs)
            else:
                run_enemy_turn(current_room.enemy, player, msgs)
            if not player.alive:
                msgs.append("Everything goes dark...")

        # ── Tick cooldowns ────────────────────────────────────────────────────
        if turn_used:
            player.tick()

        # ── Enemy killed this turn ────────────────────────────────────────────
        xp_gained    = 0
        dropped_item = None
        if enemy_was_alive and current_room.enemy and not current_room.enemy.alive:
            player.full_heal()
            xp_gained = current_room.enemy.xp_value(floor_num)
            if isinstance(current_room.enemy, Boss):
                dropped_item = random_item(floor_num)
                msgs.append(f"The boss drops: {dropped_item.name}!")
            elif random.random() < 0.2:
                dropped_item = random_item(floor_num)
                msgs.append(f"The {current_room.enemy._name} drops: {dropped_item.name}.")

        print()

        # ── Output ────────────────────────────────────────────────────────────
        if msgs == ['__map__']:
            draw_map(rooms, current_room, player, floor_num)
        elif msgs == ['__save__']:
            save_game(player, rooms, current_room, floor_num, boss_room)
            say("Game saved.")
        elif msgs == ['__load__']:
            result = load_game()
            if result:
                player, rooms, current_room, floor_num, boss_room = result
                say("Game loaded.")
            else:
                say("No save file found.")
        else:
            for m in msgs:
                say(m)

        # ── XP & level-up ─────────────────────────────────────────────────────
        if xp_gained:
            say(f"+{xp_gained} XP")
            for lvl in player.add_xp(xp_gained):
                do_upgrade_draft(player, lvl)

        # ── Item drop ─────────────────────────────────────────────────────────
        if dropped_item:
            offer_item(player, dropped_item, source='drop')

        # ── Room navigation ───────────────────────────────────────────────────
        if new_room:
            current_room = new_room
            current_room.visited = True
            print()
            announce_room(current_room, boss_room)
            if current_room.type == 'merchant':
                do_merchant(current_room, player, floor_num)
            elif current_room.item:
                taken = offer_item(player, current_room.item, source='room')
                if taken:
                    current_room.item = None

        # ── Floor descent ─────────────────────────────────────────────────────
        if descended:
            floor_num += 1
            rooms, _, boss_room = generate_floor(floor_num)
            non_stair    = [r for r in rooms if r.type != 'staircase']
            current_room = random.choice(non_stair)
            current_room.visited = True
            print()
            say(f"Floor {floor_num}. The air grows cold and heavy.")
            announce_room(current_room, boss_room)
            if current_room.type == 'merchant':
                do_merchant(current_room, player, floor_num)
            elif current_room.item:
                offer_item(player, current_room.item, source='room')
                current_room.item = None

        # ── Redraw ────────────────────────────────────────────────────────────
        print()
        rule()
        draw_room(player, current_room, floor_num)

        if not player.alive:
            rule()
            game_over_screen(floor_num)
            return ask_restart()

        rule()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    while run_game():
        pass


if __name__ == '__main__':
    main()
