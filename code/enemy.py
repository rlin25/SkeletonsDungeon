import random

from constants import ENEMY_TIERS, BOSS_NAMES, ELITE_PREFIXES, ELITE_ABILITIES


class Enemy:
    def __init__(self, floor_num, ng_plus_cycle=0):
        ng_mult = 1 + ng_plus_cycle * 0.10
        self.max_hp  = int((30 + (floor_num - 1) * 10) * ng_mult)
        self.hp      = self.max_hp
        self.dmg_min = int((5  + (floor_num - 1) * 2) * ng_mult)
        self.dmg_max = int((15 + (floor_num - 1) * 3) * ng_mult)
        self._name   = self._pick_name(floor_num)
        self.stunned = False
        self.status_effects = {}
        self.enraged = False
        self.is_elite = False
        self.is_final_boss = False

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
            'is_elite': False,
            'is_final_boss': False,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
            'status_effects': self.status_effects,
            'enraged': self.enraged,
        }

    @staticmethod
    def from_dict(d):
        e = object.__new__(Enemy)
        e.hp = d['hp']; e.max_hp = d['max_hp']
        e.dmg_min = d['dmg_min']; e.dmg_max = d['dmg_max']
        e._name = d['name']; e.stunned = d['stunned']
        e.status_effects = d.get('status_effects', {})
        e.enraged = d.get('enraged', False)
        e.is_elite = False
        e.is_final_boss = False
        return e


class Boss(Enemy):
    def __init__(self, floor_num, boss_num, ng_plus_cycle=0):
        self.floor_num = floor_num
        self.boss_num  = boss_num
        ng_mult  = 1 + ng_plus_cycle * 0.10
        base_hp  = int((30 + (floor_num - 1) * 10) * ng_mult)
        base_min = int((5  + (floor_num - 1) * 2) * ng_mult)
        base_max = int((15 + (floor_num - 1) * 3) * ng_mult)
        self.max_hp  = int(base_hp  * 2.5)
        self.hp      = self.max_hp
        self.dmg_min = int(base_min * 2.5)
        self.dmg_max = int(base_max * 2.5)
        self._name   = BOSS_NAMES[(boss_num - 1) % len(BOSS_NAMES)]
        self.stunned = False
        self.status_effects = {}
        self.enraged = False
        self.is_elite = False
        self.is_final_boss = False
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
            'is_elite': False,
            'is_final_boss': False,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
            'status_effects': self.status_effects,
            'enraged': self.enraged,
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
        b.status_effects = d.get('status_effects', {})
        b.enraged = d.get('enraged', False)
        b.is_elite = False
        b.is_final_boss = False
        b.boss_num = d['boss_num']; b.floor_num = d['floor_num']
        b.phase = d['phase']
        b.phase2_threshold = d['phase2_threshold']
        b.telegraphing = d['telegraphing']
        return b


class EliteEnemy(Enemy):
    def __init__(self, floor_num, ng_plus_cycle=0):
        super().__init__(floor_num, ng_plus_cycle)
        self.prefix = random.choice(ELITE_PREFIXES)
        self.ability = random.choice(ELITE_ABILITIES)
        # Elite stat scaling applied ON TOP of NG+ scaling
        self.max_hp = int(self.max_hp * 1.5)
        self.hp     = self.max_hp
        self.dmg_min = round(self.dmg_min * 1.3)
        self.dmg_max = round(self.dmg_max * 1.3)
        # Ability tracking
        self.ability_used  = False   # for heal, summon, shield (one-time)
        self.shield_active = (self.ability == 'shield')
        self.attack_count  = 0       # for stun_strike (fires on 3rd attack)
        self.is_elite      = True

    @property
    def name(self):
        return f"{self.prefix} {self._name}"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'is_elite': True,
            'prefix': self.prefix,
            'ability': self.ability,
            'ability_used': self.ability_used,
            'shield_active': self.shield_active,
            'attack_count': self.attack_count,
        })
        return d

    @staticmethod
    def from_dict(d):
        e = object.__new__(EliteEnemy)
        e.hp = d['hp']; e.max_hp = d['max_hp']
        e.dmg_min = d['dmg_min']; e.dmg_max = d['dmg_max']
        e._name = d['name']; e.stunned = d['stunned']
        e.status_effects = d.get('status_effects', {})
        e.enraged = d.get('enraged', False)
        e.is_elite = True
        e.is_final_boss = False
        e.prefix = d['prefix']
        e.ability = d['ability']
        e.ability_used = d.get('ability_used', False)
        e.shield_active = d.get('shield_active', False)
        e.attack_count = d.get('attack_count', 0)
        return e


class FinalBoss:
    def __init__(self, ng_plus_cycle=0):
        self.ng_plus_cycle = ng_plus_cycle
        self.max_hp   = 400 + ng_plus_cycle * 40
        self.hp       = self.max_hp
        self.dmg_min  = 20 + ng_plus_cycle * 3
        self.dmg_max  = 35 + ng_plus_cycle * 3
        self._name    = 'The Dungeon Architect'
        self.stunned  = False
        self.status_effects = {}
        self.enraged  = False
        self.phase    = 1
        self.phase2_threshold = self.max_hp // 2
        # Phase 1: pick 2 random abilities
        _all = ['heal', 'enrage', 'summon', 'shield', 'poison_strike', 'stun_strike']
        self.abilities       = random.sample(_all, 2)
        self.ability_used    = False    # heal/summon (one-time state)
        self.shield_active   = 'shield' in self.abilities
        self.attack_count    = 0        # for stun_strike
        self.is_elite        = False
        self.is_final_boss   = True

    @property
    def alive(self):
        return self.hp > 0

    @property
    def name(self):
        phase_tag = ' [Phase 2]' if self.phase == 2 else ''
        return f"{self._name}{phase_tag}"

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def roll_damage(self):
        return random.randint(self.dmg_min, self.dmg_max)

    def xp_value(self, floor_num):
        return 200 + floor_num * 30

    def check_phase_transition(self):
        """Returns True if boss just dropped to phase 2 (triggers revive)."""
        if self.phase == 1 and self.hp <= self.phase2_threshold:
            self.phase = 2
            self.hp = self.max_hp   # revive to full
            self.dmg_min = 30 + self.ng_plus_cycle * 3
            self.dmg_max = 50 + self.ng_plus_cycle * 3
            # All six abilities become active
            self.abilities = ['heal', 'enrage', 'summon', 'shield', 'poison_strike', 'stun_strike']
            self.shield_active = True   # re-activate shield in phase 2
            self.ability_used  = False  # reset one-time abilities for phase 2
            self.attack_count  = 0
            return True
        return False

    def to_dict(self):
        return {
            'is_boss': False, 'is_elite': False, 'is_final_boss': True,
            'hp': self.hp, 'max_hp': self.max_hp,
            'dmg_min': self.dmg_min, 'dmg_max': self.dmg_max,
            'name': self._name, 'stunned': self.stunned,
            'status_effects': self.status_effects,
            'enraged': self.enraged,
            'ng_plus_cycle': self.ng_plus_cycle,
            'phase': self.phase,
            'phase2_threshold': self.phase2_threshold,
            'abilities': self.abilities,
            'ability_used': self.ability_used,
            'shield_active': self.shield_active,
            'attack_count': self.attack_count,
        }

    @staticmethod
    def from_dict(d):
        fb = object.__new__(FinalBoss)
        fb.hp = d['hp']; fb.max_hp = d['max_hp']
        fb.dmg_min = d['dmg_min']; fb.dmg_max = d['dmg_max']
        fb._name = d['name']; fb.stunned = d['stunned']
        fb.status_effects = d.get('status_effects', {})
        fb.enraged = d.get('enraged', False)
        fb.ng_plus_cycle = d.get('ng_plus_cycle', 0)
        fb.phase = d.get('phase', 1)
        fb.phase2_threshold = d.get('phase2_threshold', fb.max_hp // 2)
        fb.abilities = d.get('abilities', [])
        fb.ability_used = d.get('ability_used', False)
        fb.shield_active = d.get('shield_active', False)
        fb.attack_count = d.get('attack_count', 0)
        fb.is_elite = False; fb.is_final_boss = True
        return fb


def enemy_from_dict(d):
    """Reconstruct Enemy, Boss, EliteEnemy, or FinalBoss from dict. Returns None if d is None."""
    if d is None:
        return None
    if d.get('is_final_boss'):
        return FinalBoss.from_dict(d)
    if d.get('is_elite'):
        return EliteEnemy.from_dict(d)
    if d.get('is_boss'):
        return Boss.from_dict(d)
    return Enemy.from_dict(d)
