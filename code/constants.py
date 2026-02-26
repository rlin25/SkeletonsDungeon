# ── Constants ─────────────────────────────────────────────────────────────────

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
    'r':  'rest',
    'b':  'buy',
    'rr': 'reroll',
}

RULE = '─' * 44


def xp_threshold(level: int) -> int:
    return level * 100
