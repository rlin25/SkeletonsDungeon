import random

from constants import WEAPON_POOL, ARMOUR_POOL, SCROLL_POOL


class HealthPotion:
    name = 'Health Potion'
    desc = 'Restores 40 HP'

    def to_dict(self):
        return {'type': 'potion'}

    @staticmethod
    def from_dict(_):
        return HealthPotion()


class Weapon:
    def __init__(self, name, bonus):
        self.name  = name
        self.bonus = bonus
        self.desc  = f'+{bonus} attack'

    def to_dict(self):
        return {'type': 'weapon', 'name': self.name, 'bonus': self.bonus}

    @staticmethod
    def from_dict(d):
        return Weapon(d['name'], d['bonus'])


class Armour:
    def __init__(self, name, bonus):
        self.name  = name
        self.bonus = bonus
        self.desc  = f'+{bonus} defense'

    def to_dict(self):
        return {'type': 'armour', 'name': self.name, 'bonus': self.bonus}

    @staticmethod
    def from_dict(d):
        return Armour(d['name'], d['bonus'])


class Scroll:
    def __init__(self, name, desc, effect):
        self.name   = name
        self.desc   = desc
        self.effect = effect

    def to_dict(self):
        return {'type': 'scroll', 'name': self.name,
                'desc': self.desc, 'effect': self.effect}

    @staticmethod
    def from_dict(d):
        return Scroll(d['name'], d['desc'], d['effect'])


def item_from_dict(d):
    if d is None:
        return None
    t = d['type']
    if t == 'potion': return HealthPotion.from_dict(d)
    if t == 'weapon': return Weapon.from_dict(d)
    if t == 'armour': return Armour.from_dict(d)
    if t == 'scroll': return Scroll.from_dict(d)
    return None


def random_item(floor_num=1):
    """Generate a random item scaled loosely to floor depth."""
    roll = random.random()
    if roll < 0.35:
        return HealthPotion()
    elif roll < 0.55:
        idx  = min(floor_num - 1, len(WEAPON_POOL) - 1)
        name, bonus = random.choice(WEAPON_POOL[:idx + 1])
        return Weapon(name, bonus)
    elif roll < 0.75:
        idx  = min(floor_num - 1, len(ARMOUR_POOL) - 1)
        name, bonus = random.choice(ARMOUR_POOL[:idx + 1])
        return Armour(name, bonus)
    else:
        name, desc, effect = random.choice(SCROLL_POOL)
        return Scroll(name, desc, effect)
