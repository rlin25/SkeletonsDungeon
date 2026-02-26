import random

from constants import EMPTY_FLAVOUR
from items import item_from_dict
from enemy import Enemy, enemy_from_dict


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
        self.rest_used = False          # Phase 4: rest rooms deplete after use
        self.merchant_rerolled = False  # Phase 4: one reroll per merchant visit

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
            'rest_used': self.rest_used,
            'merchant_rerolled': self.merchant_rerolled,
            'enemy': self.enemy.to_dict() if self.enemy else None,
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
        r.rest_used = d.get('rest_used', False)
        r.merchant_rerolled = d.get('merchant_rerolled', False)
        r.enemy = enemy_from_dict(d['enemy'])
        return r
