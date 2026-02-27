import random

from constants import THEMES, DIR_DELTA, OPPOSITES, FINAL_BOSS_FLOOR
from items import random_item, HealthPotion, Weapon, Armour, Scroll
from enemy import Boss, EliteEnemy, FinalBoss, Enemy
from room import Room


# ── Helpers ───────────────────────────────────────────────────────────────────

def _undead_name(floor_num):
    if floor_num <= 2:   return 'Skeleton'
    elif floor_num <= 4: return 'Shadow Wraith'
    else:                return 'Undead Knight'


def _merchant_price(item):
    if isinstance(item, HealthPotion):
        return random.randint(8, 15)
    elif isinstance(item, (Weapon, Armour)):
        return random.randint(20, 40)
    elif isinstance(item, Scroll):
        return random.randint(12, 25)
    return 10


def generate_merchant_stock(floor_num):
    """Generate 3 merchant items with randomised prices."""
    items  = [random_item(floor_num) for _ in range(3)]
    prices = [_merchant_price(item) for item in items]
    return items, prices


# ── Floor Generator ───────────────────────────────────────────────────────────

TRAP_TYPES = ['spike_pit', 'poison_vent', 'alarm', 'binding_snare', 'collapse']


def _floor_room_count(floor_num):
    if floor_num == 1:   base = 6
    elif floor_num == 2: base = 8
    elif floor_num <= 4: base = 10 + (floor_num - 3) * 2
    else:                base = min(14 + (floor_num - 5) * 2, 18)
    return max(4, base + random.randint(-2, 2))


def generate_floor(floor_num, ng_plus_cycle=0):
    """
    Generate a connected floor.
    Returns (rooms_list, start_room, boss_room).
    boss_room is None on non-boss floors and on floor 15 (final boss floor).
    On floor 15, the final boss room has type == 'final_boss'.
    """
    is_boss_floor = (floor_num % 3 == 0) and (floor_num != FINAL_BOSS_FLOOR)
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

    # Staircase on normal floors; final_boss room on floor 15
    if floor_num == FINAL_BOSS_FLOOR:
        type_map = {(0, 0): 'empty', stair_pos: 'final_boss'}
    else:
        type_map = {(0, 0): 'empty', stair_pos: 'staircase'}

    if boss_pos:
        type_map[boss_pos] = 'boss'

    # Distribution: merchant 5%, rest 12%, trap 10%, enemy 50%, empty 23%
    for pos in non_start:
        if pos not in type_map:
            roll = random.random()
            if roll < 0.05:
                type_map[pos] = 'merchant'
            elif roll < 0.17:
                type_map[pos] = 'rest'
            elif roll < 0.27:
                type_map[pos] = 'trap'
            elif roll < 0.77:
                type_map[pos] = 'enemy'
            else:
                type_map[pos] = 'empty'

    # Build Room objects
    gold_scale = 1 + (floor_num - 1) * 0.1
    rooms_by_pos = {}
    for col, row in positions:
        theme_name, theme_desc = random.choice(THEMES)
        rtype = type_map[(col, row)]
        room  = Room(col, row, rtype, theme_name, theme_desc, floor_num)

        if rtype == 'boss':
            room.enemies = [Boss(floor_num, boss_num, ng_plus_cycle)]

        if rtype == 'final_boss':
            room.enemies = [FinalBoss(ng_plus_cycle)]

        if rtype == 'trap':
            room.trap_type = random.choice(TRAP_TYPES)

        if rtype == 'merchant':
            items, prices = generate_merchant_stock(floor_num)
            room.merchant_items  = items
            room.merchant_prices = prices

        if rtype == 'enemy':
            # Multi-enemy spawning based on floor depth
            count_enemies = 1
            if floor_num >= 12:
                if random.random() < 0.50:
                    count_enemies = 2
                if count_enemies == 2 and random.random() < 0.20:
                    count_enemies = 3
            elif floor_num >= 8:
                if random.random() < 0.40:
                    count_enemies = 2
                if count_enemies == 2 and random.random() < 0.10:
                    count_enemies = 3
            elif floor_num >= 4:
                if random.random() < 0.25:
                    count_enemies = 2
            # else: count_enemies = 1 (floors 1-3)

            # First enemy already in room.enemies from Room constructor
            for _ in range(count_enemies - 1):
                room.enemies.append(Enemy(floor_num, ng_plus_cycle))

            # Elite enemy spawning on floor 3+
            if floor_num >= 3 and random.random() < 0.20:
                elite = EliteEnemy(floor_num, ng_plus_cycle)
                if room.enemies:
                    elite._name = room.enemies[0]._name
                room.enemies[0] = elite

            # Undead/Forgotten Chamber flavour override
            if theme_name == 'Forgotten Chamber' and random.random() < 0.30:
                room.enemies[0]._name = _undead_name(floor_num)

        if rtype == 'empty':
            # Forgotten Chamber boosts item spawn chance to 40%
            item_chance = 0.40 if theme_name == 'Forgotten Chamber' else 0.30
            if random.random() < item_chance:
                room.item = random_item(floor_num)
            # 25% chance for floor gold
            if random.random() < 0.25:
                room.gold = round(random.randint(3, 8) * gold_scale)

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
