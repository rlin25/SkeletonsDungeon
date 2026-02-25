#!/usr/bin/env python3
"""
DUNGEON CRAWLER — Phase 2
Text-based, turn-based dungeon crawler with procedurally generated floors.
"""

import random
import sys

# Force UTF-8 output on Windows (box-drawing and block characters)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# ── Constants ────────────────────────────────────────────────────────────────

PLAYER_MAX_HP = 100
PLAYER_DMG    = (10, 20)
ROOM_W        = 36   # inner grid width
ROOM_H        = 11   # inner grid height
DIRECTIONS    = ('north', 'south', 'east', 'west')
OPPOSITES     = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
DIR_DELTA     = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}

# Enemy name pools, keyed by minimum floor
ENEMY_TIERS = [
    (5, ['Troll', 'Undead Knight', 'Dungeon Horror']),
    (3, ['Orc', 'Shadow Wraith', 'Stone Golem']),
    (1, ['Goblin', 'Rat', 'Skeleton']),
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


# ── Helpers ──────────────────────────────────────────────────────────────────

def hp_bar(current, maximum, width=20):
    filled = round((current / maximum) * width)
    return '█' * filled + '░' * (width - filled)

RULE = '─' * 44

def rule():
    print(RULE)

def say(text: str):
    print(f"  {text}")


# ── Player ───────────────────────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.hp     = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def full_heal(self):
        self.hp = self.max_hp


# ── Enemy ────────────────────────────────────────────────────────────────────

class Enemy:
    def __init__(self, floor_num):
        self.max_hp  = 30 + (floor_num - 1) * 10
        self.hp      = self.max_hp
        self.dmg_min = 5  + (floor_num - 1) * 2
        self.dmg_max = 15 + (floor_num - 1) * 3
        self._name   = self._pick_name(floor_num)

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


# ── Room ─────────────────────────────────────────────────────────────────────

class Room:
    def __init__(self, col, row, room_type, theme_name, theme_desc, floor_num):
        self.col        = col
        self.row        = row
        self.type       = room_type      # 'enemy' | 'empty' | 'staircase'
        self.theme_name = theme_name
        self.theme_desc = theme_desc
        self.exits      = {}             # direction -> Room
        self.visited    = False
        self.enemy      = Enemy(floor_num) if room_type == 'enemy' else None
        self.flavour    = random.choice(EMPTY_FLAVOUR) if room_type == 'empty' else None


# ── Floor Generator ──────────────────────────────────────────────────────────

def _floor_room_count(floor_num):
    """Return room count for a floor, with ±2 variance."""
    if floor_num == 1:
        base = 6
    elif floor_num == 2:
        base = 8
    elif floor_num <= 4:
        base = 10 + (floor_num - 3) * 2
    else:
        base = min(14 + (floor_num - 5) * 2, 18)
    return max(4, base + random.randint(-2, 2))


def generate_floor(floor_num):
    """
    Procedurally generate a floor.
    Returns (rooms_list, start_room) where start_room is always at (0,0)
    and is always an empty room.
    """
    count = _floor_room_count(floor_num)

    # ── Place room positions via random walk from origin ──────────────────
    positions = [(0, 0)]
    pos_set   = {(0, 0)}
    while len(positions) < count:
        col, row = random.choice(positions)
        deltas = list(DIR_DELTA.values())
        random.shuffle(deltas)
        for dc, dr in deltas:
            npos = (col + dc, row + dr)
            if npos not in pos_set:
                pos_set.add(npos)
                positions.append(npos)
                break

    # ── Assign room types ─────────────────────────────────────────────────
    # (0,0) is always empty; one other room is the staircase
    non_start = positions[1:]
    stair_pos = random.choice(non_start)
    type_map  = {(0, 0): 'empty', stair_pos: 'staircase'}
    for pos in non_start:
        if pos not in type_map:
            type_map[pos] = 'enemy' if random.random() < 0.6 else 'empty'

    # ── Build Room objects ────────────────────────────────────────────────
    rooms_by_pos = {}
    for col, row in positions:
        theme_name, theme_desc = random.choice(THEMES)
        rtype = type_map[(col, row)]
        rooms_by_pos[(col, row)] = Room(col, row, rtype, theme_name, theme_desc, floor_num)

    # ── Connect via BFS spanning tree (guarantees full connectivity) ───────
    visited_bfs = {(0, 0)}
    queue       = [(0, 0)]
    while queue:
        pos = queue.pop(0)
        col, row = pos
        dirs = list(DIR_DELTA.items())
        random.shuffle(dirs)
        for d, (dc, dr) in dirs:
            npos = (col + dc, row + dr)
            if npos in rooms_by_pos and npos not in visited_bfs:
                visited_bfs.add(npos)
                queue.append(npos)
                r1, r2 = rooms_by_pos[pos], rooms_by_pos[npos]
                r1.exits[d] = r2
                r2.exits[OPPOSITES[d]] = r1

    # ── Add extra connections for a less linear feel ──────────────────────
    for (col, row), room in rooms_by_pos.items():
        for d, (dc, dr) in DIR_DELTA.items():
            npos = (col + dc, row + dr)
            if npos in rooms_by_pos and d not in room.exits:
                if random.random() < 0.35:
                    neighbour = rooms_by_pos[npos]
                    room.exits[d] = neighbour
                    neighbour.exits[OPPOSITES[d]] = room

    rooms      = list(rooms_by_pos.values())
    start_room = rooms_by_pos[(0, 0)]
    return rooms, start_room


# ── ASCII Map ─────────────────────────────────────────────────────────────────

def draw_map(rooms, current_room):
    """Print a minimal ASCII grid of discovered rooms on the current floor."""
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
        if r.type == 'enemy' and r.enemy and r.enemy.alive:
            return '[E]'
        return '[ ]'

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
                s = sym(r)
                # East connector — only shown if east neighbour is also visited
                east_r = room_at.get((col + 1, row))
                e_conn = ' - ' if east_r is not None and 'east' in r.exits else '   '
                room_line += s + e_conn
                # South connector — only shown if south neighbour is also visited
                south_r = room_at.get((col, row + 1))
                s_conn  = ' | ' if south_r is not None and 'south' in r.exits else '   '
                conn_line += s_conn + '   '

        print('  ' + room_line.rstrip())
        if row < max_row:
            print('  ' + conn_line.rstrip())

    print()
    say("Legend: [*]=You  [ ]=Visited  [S]=Staircase  [E]=Enemy")
    print()


# ── Room Renderer ─────────────────────────────────────────────────────────────

def draw_room(player: Player, room: Room, floor_num: int) -> None:
    W, H = ROOM_W, ROOM_H
    grid = [[' '] * W for _ in range(H)]
    grid[H // 2][W // 2] = 'P'
    if room.enemy and room.enemy.alive:
        grid[H // 4][W // 4] = 'E'

    inner = W + 2
    mid   = inner // 2
    has   = {d: d in room.exits for d in DIRECTIONS}

    n_ch = 'N' if has['north'] else '─'
    s_ch = 'S' if has['south'] else '─'
    top  = '+' + '─' * (mid - 1) + n_ch + '─' * (inner - mid) + '+'
    bot  = '+' + '─' * (mid - 1) + s_ch + '─' * (inner - mid) + '+'

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

    # Status header
    p_bar = hp_bar(player.hp, player.max_hp)
    print(f"\n  Floor {floor_num}   [P] You            HP: [{p_bar}] {player.hp}/{player.max_hp}")
    if room.enemy and room.enemy.alive:
        e_bar = hp_bar(room.enemy.hp, room.enemy.max_hp)
        print(f"          [E] {room.enemy.name:<16} HP: [{e_bar}] {room.enemy.hp}/{room.enemy.max_hp}")

    type_label = {'enemy': 'Enemy Room', 'empty': 'Empty Room', 'staircase': 'Staircase'}[room.type]
    print(f"  {room.theme_name} — {type_label}")
    exits_str = ', '.join(d for d in DIRECTIONS if d in room.exits) or 'none'
    print(f"  Exits: {exits_str}")
    print()


# ── Command Handler ───────────────────────────────────────────────────────────

def handle(raw: str, player: Player, room: Room, floor_num: int):
    """
    Parse and execute a command.
    Returns (turn_used, messages, new_room, descended).
      turn_used  — whether the enemy may retaliate
      new_room   — Room to move into, or None
      descended  — True if the player used 'descend'
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
        dmg = random.randint(*PLAYER_DMG)
        enemy.take_damage(dmg)
        msgs = [f"You strike the {enemy.name} for {dmg} damage!"]
        if not enemy.alive:
            msgs.append(f"The {enemy.name} crumples to the ground. Victory!")
            msgs.append("You catch your breath and recover fully.")
        else:
            msgs.append(f"The {enemy.name} staggers — {enemy.hp}/{enemy.max_hp} HP remaining.")
        return True, msgs, None, False

    # ── move ──────────────────────────────────────────────────────────────────
    if verb == 'move':
        if len(tokens) < 2 or tokens[1] not in DIRECTIONS:
            return False, [f"Move where? ({', '.join(DIRECTIONS)})"], None, False
        direction = tokens[1]
        if direction not in room.exits:
            return False, [f"There is no door to the {direction}."], None, False
        enemy = room.enemy
        if enemy and enemy.alive:
            return False, [f"You can't leave — {enemy.name} blocks the way!"], None, False
        return False, [f"You move {direction}."], room.exits[direction], False

    # ── look ──────────────────────────────────────────────────────────────────
    if verb == 'look':
        msgs = [f"{room.theme_name}: {room.theme_desc}"]
        if room.type == 'staircase':
            msgs.append("A stone staircase descends into the darkness below.")
        elif room.flavour:
            msgs.append(room.flavour)
        enemy = room.enemy
        if enemy and enemy.alive:
            msgs.append(f"A {enemy.name} ({enemy.hp}/{enemy.max_hp} HP) stands before you.")
        exits = ', '.join(d for d in DIRECTIONS if d in room.exits) or 'none'
        msgs.append(f"Exits: {exits}")
        return False, msgs, None, False

    # ── health ────────────────────────────────────────────────────────────────
    if verb == 'health':
        return False, [f"You check yourself: {player.hp}/{player.max_hp} HP."], None, False

    # ── descend ───────────────────────────────────────────────────────────────
    if verb == 'descend':
        if room.type != 'staircase':
            return False, ['There is no staircase here.'], None, False
        enemy = room.enemy
        if enemy and enemy.alive:
            return False, [f"You can't descend — {enemy.name} blocks the staircase!"], None, False
        return False, ['You descend the staircase into deeper darkness...'], None, True

    # ── map ───────────────────────────────────────────────────────────────────
    if verb == 'map':
        return False, ['__map__'], None, False

    # ── quit ──────────────────────────────────────────────────────────────────
    if verb in ('quit', 'exit', 'q'):
        print("\n  You retreat into the darkness. Farewell.\n")
        sys.exit(0)

    # ── help ──────────────────────────────────────────────────────────────────
    if verb in ('help', '?', 'h'):
        say("Commands: attack | move <direction> | look | health | descend | map | quit")
        return False, [], None, False

    return False, [f"Unknown command '{raw}'. Type 'help' for a list."], None, False


# ── Screens ───────────────────────────────────────────────────────────────────

def intro_screen():
    print()
    print("  ╔════════════════════════════════════════╗")
    print("  ║     D U N G E O N   C R A W L E R     ║")
    print("  ╚════════════════════════════════════════╝")
    print()
    say("You stand at the entrance to a forsaken dungeon.")
    say("Darkness stretches ahead. Danger lies deeper.")
    print()
    say("Commands: attack | move <direction> | look | health | descend | map | quit")
    print()


def game_over_screen(floor_num: int):
    print()
    print("  ╔═══════════════════════╗")
    print("  ║    G A M E  O V E R  ║")
    print("  ╚═══════════════════════╝")
    say(f"You fell on floor {floor_num}.")
    print()


def ask_restart() -> bool:
    while True:
        try:
            ans = input("  Play again? (yes / no) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if ans in ('yes', 'y'):
            return True
        if ans in ('no', 'n'):
            return False
        say("Please type yes or no.")


# ── Room entry narrative ──────────────────────────────────────────────────────

def announce_room(room: Room):
    """Print flavour text and enemy warning when entering a room."""
    say(f"{room.theme_name}: {room.theme_desc}")
    if room.type == 'staircase':
        say("A stone staircase descends into the darkness. (type 'descend' to go deeper)")
    elif room.flavour:
        say(room.flavour)
    if room.enemy and room.enemy.alive:
        say(f"A {room.enemy.name} snarls at you!")


# ── Game Session ──────────────────────────────────────────────────────────────

def run_game() -> bool:
    """Run one full session. Returns True if the player wants to restart."""
    player    = Player()
    floor_num = 1
    rooms, current_room = generate_floor(floor_num)
    current_room.visited = True

    intro_screen()
    rule()
    say(f"Floor {floor_num}. You enter the dungeon.")
    announce_room(current_room)
    print()
    rule()
    draw_room(player, current_room, floor_num)
    rule()

    while True:
        # ── Input ────────────────────────────────────────────────────────────
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Interrupted. Farewell.\n")
            sys.exit(0)

        enemy_was_alive = current_room.enemy.alive if current_room.enemy else False
        turn_used, msgs, new_room, descended = handle(raw, player, current_room, floor_num)

        # ── Enemy retaliates ─────────────────────────────────────────────────
        if turn_used and current_room.enemy and current_room.enemy.alive:
            dmg = current_room.enemy.roll_damage()
            player.take_damage(dmg)
            msgs.append(f"The {current_room.enemy.name} strikes back for {dmg} damage!")
            if not player.alive:
                msgs.append("Everything goes dark...")

        # ── Enemy killed this turn → full heal ───────────────────────────────
        if enemy_was_alive and current_room.enemy and not current_room.enemy.alive:
            player.full_heal()

        print()

        # ── Output ───────────────────────────────────────────────────────────
        if msgs == ['__map__']:
            draw_map(rooms, current_room)
        elif msgs:
            for m in msgs:
                say(m)

        # ── Room navigation ──────────────────────────────────────────────────
        if new_room:
            current_room = new_room
            current_room.visited = True
            print()
            announce_room(current_room)

        # ── Floor descent ────────────────────────────────────────────────────
        if descended:
            floor_num += 1
            rooms, _ = generate_floor(floor_num)
            # Spawn at a random non-staircase room per spec
            non_stair = [r for r in rooms if r.type != 'staircase']
            current_room = random.choice(non_stair)
            current_room.visited = True
            print()
            say(f"Floor {floor_num}. The air grows cold and heavy.")
            announce_room(current_room)

        # ── Redraw ───────────────────────────────────────────────────────────
        print()
        rule()
        draw_room(player, current_room, floor_num)

        # ── Player dead? ─────────────────────────────────────────────────────
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
