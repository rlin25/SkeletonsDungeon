import random

from constants import EMPTY_FLAVOUR
from items import item_from_dict
from enemy import Enemy, enemy_from_dict


# ── Room ──────────────────────────────────────────────────────────────────────

class Room:
    def __init__(self, col, row, room_type, theme_name, theme_desc, floor_num):
        self.col        = col
        self.row        = row
        self.type       = room_type   # enemy|empty|staircase|boss|merchant|trap|final_boss
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
            self.enemies = [Enemy(floor_num)]
        else:
            self.enemies = []         # Boss/FinalBoss set after construction in floor.py
        self.rest_used = False          # Phase 4: rest rooms deplete after use
        self.merchant_rerolled = False  # Phase 4: one reroll per merchant visit
        self.merchant_prices = []       # Phase 4: randomised prices for merchant stock
        self.gold = 0                   # Phase 4: room gold (auto-collected on entry)
        self.exits_revealed = (theme_name != 'Collapsed Tunnel')  # Phase 4: Collapsed Tunnel hides exits
        self.chip_dealt = False         # Phase 4: Damp Cave chip damage dealt once
        # Phase 5: trap fields
        self.trap_type      = None      # 'spike_pit'|'poison_vent'|'alarm'|'binding_snare'|'collapse'
        self.trap_triggered = False
        self.trap_disarmed  = False
        self.alarm_pending  = False     # Alarm trap: True means next enemy room gets extra enemy
        # Phase 5: extra enemy pending from alarm trap
        self.extra_enemy_pending = False

    @property
    def enemy(self):
        for e in self.enemies:
            if e.alive:
                return e
        return None

    @enemy.setter
    def enemy(self, val):
        if val is None:
            self.enemies = []
        else:
            self.enemies = [val]

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
            'merchant_prices': self.merchant_prices,
            'gold': self.gold,
            'rest_used': self.rest_used,
            'merchant_rerolled': self.merchant_rerolled,
            'exits_revealed': self.exits_revealed,
            'chip_dealt': self.chip_dealt,
            'enemies': [e.to_dict() for e in self.enemies],
            'trap_type': self.trap_type,
            'trap_triggered': self.trap_triggered,
            'trap_disarmed': self.trap_disarmed,
            'alarm_pending': self.alarm_pending,
            'extra_enemy_pending': self.extra_enemy_pending,
        }

    @staticmethod
    def from_dict(d):
        r = object.__new__(Room)
        r.col = d['col']; r.row = d['row']
        r.type = d['type']
        r.theme_name = d['theme_name']; r.theme_desc = d['theme_desc']
        r.visited = d['visited']; r.flavour = d['flavour']
        r.exits = {}  # filled in second pass by persistence.py
        r.item = item_from_dict(d['item'])
        r.merchant_items = [item_from_dict(i) for i in d['merchant_items']]
        r.merchant_done = d['merchant_done']
        r.merchant_prices = d.get('merchant_prices', [])
        r.gold = d.get('gold', 0)
        r.rest_used = d.get('rest_used', False)
        r.merchant_rerolled = d.get('merchant_rerolled', False)
        r.exits_revealed = d.get('exits_revealed', True)
        r.chip_dealt = d.get('chip_dealt', False)
        # Restore enemies list — support both old 'enemy' key and new 'enemies' key
        if 'enemies' in d:
            r.enemies = [enemy_from_dict(e) for e in d['enemies']]
        elif 'enemy' in d:
            r.enemies = [enemy_from_dict(d['enemy'])] if d['enemy'] else []
        else:
            r.enemies = []
        # Phase 5: trap fields with defaults for backward compat
        r.trap_type = d.get('trap_type', None)
        r.trap_triggered = d.get('trap_triggered', False)
        r.trap_disarmed = d.get('trap_disarmed', False)
        r.alarm_pending = d.get('alarm_pending', False)
        r.extra_enemy_pending = d.get('extra_enemy_pending', False)
        return r
