import random


class _Upgrade:
    def __init__(self, cat, label, desc):
        self.cat   = cat
        self.label = label
        self.desc  = desc

    def apply(self, player):
        pass


class _HPUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('hp', f'+{amount} Max HP', f'Maximum health increases by {amount}.')
        self.amount = amount

    def apply(self, player):
        player.max_hp += self.amount
        player.hp = min(player.hp + self.amount, player.max_hp)


class _AtkUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('atk', f'+{amount} Attack', f'Attacks deal {amount} more damage.')
        self.amount = amount

    def apply(self, player):
        player.atk_bonus += self.amount


class _DefUpgrade(_Upgrade):
    def __init__(self, amount):
        super().__init__('def', f'+{amount} Defense', f'Incoming damage reduced by {amount}.')
        self.amount = amount

    def apply(self, player):
        player.defense += self.amount


class _HSUpgrade(_Upgrade):
    def __init__(self, is_unlock):
        if is_unlock:
            super().__init__('hs', 'Unlock Heavy Strike',
                             'Learn a devastating heavy attack (3-turn cooldown).')
        else:
            super().__init__('hs', 'Improve Heavy Strike',
                             'Heavy Strike cooldown reduced by 1 turn.')
        self.is_unlock = is_unlock

    def apply(self, player):
        if self.is_unlock:
            player.hs_unlocked = True
        else:
            player.hs_max_cd = max(1, player.hs_max_cd - 1)


def draw_upgrades(player, count=3):
    """Return `count` upgrades ensuring category variety."""
    cats = {
        'hp':  [_HPUpgrade(20), _HPUpgrade(30)],
        'atk': [_AtkUpgrade(5), _AtkUpgrade(8)],
        'def': [_DefUpgrade(2), _DefUpgrade(3)],
    }
    if not player.hs_unlocked:
        cats['hs'] = [_HSUpgrade(True)]
    elif player.hs_max_cd > 1:
        cats['hs'] = [_HSUpgrade(False)]

    keys = list(cats.keys())
    random.shuffle(keys)
    chosen = []
    for cat in keys:
        if len(chosen) >= count:
            break
        chosen.append(random.choice(cats[cat]))
    # Fill any remaining slots
    while len(chosen) < count:
        cat = random.choice(list(cats.keys()))
        chosen.append(random.choice(cats[cat]))
    random.shuffle(chosen)
    return chosen[:count]
