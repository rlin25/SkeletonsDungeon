import random

from constants import THEMES, DIR_DELTA, OPPOSITES
from items import random_item
from enemy import Boss
from room import Room


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
