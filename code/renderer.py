import sys

from constants import RULE, DIRECTIONS, ROOM_W, ROOM_H, xp_threshold
from enemy import Boss


def say(text: str):
    print(f"  {text}")


def rule():
    print(RULE)


def hp_bar(current, maximum, width=20):
    filled = round((current / maximum) * width)
    return '█' * filled + '░' * (width - filled)


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
