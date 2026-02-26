import random

from constants import ENEMY_TIERS, BOSS_NAMES


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

    def to_dict(self):
        return {
            'is_boss': False,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
        }

    @staticmethod
    def from_dict(d):
        e = object.__new__(Enemy)
        e.hp = d['hp']; e.max_hp = d['max_hp']
        e.dmg_min = d['dmg_min']; e.dmg_max = d['dmg_max']
        e._name = d['name']; e.stunned = d['stunned']
        return e


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

    def to_dict(self):
        d = {
            'is_boss': True,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
            'boss_num': self.boss_num, 'floor_num': self.floor_num,
            'phase': self.phase, 'phase2_threshold': self.phase2_threshold,
            'telegraphing': self.telegraphing,
        }
        return d

    @staticmethod
    def from_dict(d):
        b = object.__new__(Boss)
        b.hp = d['hp']; b.max_hp = d['max_hp']
        b.dmg_min = d['dmg_min']; b.dmg_max = d['dmg_max']
        b._name = d['name']; b.stunned = d['stunned']
        b.boss_num = d['boss_num']; b.floor_num = d['floor_num']
        b.phase = d['phase']
        b.phase2_threshold = d['phase2_threshold']
        b.telegraphing = d['telegraphing']
        return b


def enemy_from_dict(d):
    """Reconstruct Enemy or Boss from dict. Returns None if d is None."""
    if d is None:
        return None
    if d['is_boss']:
        return Boss.from_dict(d)
    return Enemy.from_dict(d)
