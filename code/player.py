import random
import time

from constants import PLAYER_MAX_HP, PLAYER_DMG, xp_threshold
from items import item_from_dict


class Player:
    def __init__(self):
        self.hp          = PLAYER_MAX_HP
        self.max_hp      = PLAYER_MAX_HP
        self.level       = 1
        self.xp          = 0
        self.defense     = 0
        self.atk_bonus   = 0
        self.dex         = 5
        self.hs_unlocked = False
        self.hs_cooldown = 0       # turns until usable
        self.hs_max_cd   = 3
        self.double_dmg  = 0       # turns of double damage remaining
        self.weapon      = None    # Weapon or None
        self.armour      = None    # Armour or None
        self.consumables = []      # max 3
        self.gold        = 0
        self.temp_atk    = 0       # temporary ATK bonus from room theme (not saved)
        self.temp_def    = 0       # temporary DEF bonus from room theme (not saved)
        self.status_effects = {}   # keys: 'poisoned'/'burned'/'stunned', values = turns remaining
        self.ng_plus_cycle  = 0
        self.run_stats = {
            'floors_cleared':   0,
            'enemies_killed':   0,
            'elites_killed':    0,
            'bosses_defeated':  0,
            'total_gold_earned': 0,
            'damage_dealt':     0,
            'damage_taken':     0,
            'times_rested':     0,
            'items_used':       0,
            'traps_disarmed':   0,
            'traps_triggered':  0,
            'turns_taken':      0,
            'start_time':       time.time(),
        }

    @property
    def alive(self):
        return self.hp > 0

    def dodge_chance(self) -> float:
        """Return dodge chance as a percentage."""
        return self.dex / (self.dex + 40) * 100

    def disarm_chance(self) -> float:
        """Return trap disarm chance as a percentage."""
        return self.dex / (self.dex + 20) * 100

    def take_damage(self, raw_amount) -> int:
        """Apply defense reduction and deal damage. Used for chip/DoT damage. No dodge check."""
        actual = max(0, raw_amount - self.defense)
        self.hp = max(0, self.hp - actual)
        return actual

    def attempt_damage(self, raw_amount) -> tuple:
        """
        Check dodge via dodge_chance(). If dodged, return (0, True) without modifying HP.
        Otherwise apply DEF reduction and return (actual_damage, False).
        """
        roll = random.uniform(0, 100)
        if roll < self.dodge_chance():
            return (0, True)
        actual = max(0, raw_amount - self.defense)
        self.hp = max(0, self.hp - actual)
        return (actual, False)

    def tick_status_effects(self, floor_num) -> list:
        """
        Process active status effects for one turn.
        - poisoned/burned: deal tick damage via take_damage, decrement counter.
        - stunned: decrement counter only (turn-skipping is handled externally in game.py).
        Returns a list of message strings describing what happened.
        """
        messages = []
        to_remove = []

        for effect, turns in list(self.status_effects.items()):
            if effect == 'poisoned':
                dmg = take_damage = self.take_damage(floor_num + 2)
                messages.append(f'Poison deals {dmg} damage! ({turns - 1} turns remaining)')
            elif effect == 'burned':
                dmg = self.take_damage(floor_num + 4)
                messages.append(f'Burn deals {dmg} damage! ({turns - 1} turns remaining)')
            elif effect == 'stunned':
                messages.append(f'You are stunned! ({turns - 1} turns remaining)')

            self.status_effects[effect] = turns - 1
            if self.status_effects[effect] <= 0:
                to_remove.append(effect)

        for effect in to_remove:
            del self.status_effects[effect]
            if effect == 'poisoned':
                messages.append('The poison has worn off.')
            elif effect == 'burned':
                messages.append('The burn has faded.')
            elif effect == 'stunned':
                messages.append('You are no longer stunned.')

        return messages

    def apply_status(self, effect: str, turns: int):
        """
        Apply a status effect for `turns` turns.
        Re-applying resets duration except for 'stunned', which cannot stack:
        if already stunned, the re-apply is ignored.
        """
        if effect == 'stunned' and 'stunned' in self.status_effects:
            return
        self.status_effects[effect] = turns

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
            'dex': self.dex,
            'hs_unlocked': self.hs_unlocked,
            'hs_cooldown': self.hs_cooldown, 'hs_max_cd': self.hs_max_cd,
            'double_dmg': self.double_dmg,
            'weapon':      self.weapon.to_dict() if self.weapon else None,
            'armour':      self.armour.to_dict() if self.armour else None,
            'consumables': [c.to_dict() for c in self.consumables],
            'gold': self.gold,
            'status_effects': self.status_effects,
            'ng_plus_cycle': self.ng_plus_cycle,
        }
        return d

    @staticmethod
    def from_dict(d):
        p = Player()
        p.hp = d['hp']; p.max_hp = d['max_hp']
        p.level = d['level']; p.xp = d['xp']
        p.defense = d['defense']; p.atk_bonus = d['atk_bonus']
        p.dex = d.get('dex', 5)
        p.hs_unlocked = d['hs_unlocked']
        p.hs_cooldown = d['hs_cooldown']; p.hs_max_cd = d['hs_max_cd']
        p.double_dmg  = d['double_dmg']
        p.weapon      = item_from_dict(d['weapon'])
        p.armour      = item_from_dict(d['armour'])
        p.consumables = [item_from_dict(c) for c in d['consumables']]
        p.gold = d.get('gold', 0)
        p.status_effects = d.get('status_effects', {})
        p.ng_plus_cycle  = d.get('ng_plus_cycle', 0)
        return p
