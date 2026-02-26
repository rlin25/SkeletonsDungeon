import random

from constants import PLAYER_MAX_HP, PLAYER_DMG, xp_threshold
from items import item_from_dict


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
        self.gold = 0   # Phase 4: gold economy

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
        d = {
            'hp': self.hp, 'max_hp': self.max_hp,
            'level': self.level, 'xp': self.xp,
            'defense': self.defense, 'atk_bonus': self.atk_bonus,
            'hs_unlocked': self.hs_unlocked,
            'hs_cooldown': self.hs_cooldown, 'hs_max_cd': self.hs_max_cd,
            'double_dmg': self.double_dmg,
            'weapon':      self.weapon.to_dict() if self.weapon else None,
            'armour':      self.armour.to_dict() if self.armour else None,
            'consumables': [c.to_dict() for c in self.consumables],
            'gold': self.gold,  # Phase 4 field
        }
        return d

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
        p.gold = d.get('gold', 0)  # Phase 4 field, default 0 for old saves
        return p
