from dataclasses import dataclass, field
from typing import Optional
import sys
import random

from constants import DIRECTIONS, ABBREVS, xp_threshold, REST_FLAVOUR
from items import HealthPotion, Scroll, Weapon, Armour
from upgrades import draw_upgrades
from renderer import say, hp_bar


# ── CommandResult ─────────────────────────────────────────────────────────────

@dataclass
class CommandResult:
    turn_used: bool = False
    messages:  list = field(default_factory=list)
    new_room:  Optional[object] = None
    descended: bool = False
    action:    str  = ''   # 'map' | 'save' | 'load' | ''


# ── normalize ─────────────────────────────────────────────────────────────────

def normalize(raw: str) -> str:
    """Expand abbreviations; return lowercased full command string."""
    tokens = raw.strip().lower().split()
    if not tokens:
        return ''
    verb, rest = tokens[0], ' '.join(tokens[1:])
    if verb == 'u':
        return ('use ' + rest).strip()
    if verb == 'eq':
        return ('equip ' + rest).strip()
    if verb in ABBREVS:
        expanded = ABBREVS[verb]
        return (expanded + ' ' + rest).strip() if rest else expanded
    return raw.strip().lower()


# ── _pick ─────────────────────────────────────────────────────────────────────

def _pick(prompt, lo, hi):
    """Ask the player for an integer in [lo, hi]. Returns int."""
    while True:
        try:
            raw = input(f"  {prompt} ").strip()
        except (EOFError, KeyboardInterrupt):
            return lo
        if raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        say(f"Please enter a number between {lo} and {hi}.")


# ── do_upgrade_draft ──────────────────────────────────────────────────────────

def do_upgrade_draft(player, new_level):
    print()
    say(f"★  LEVEL UP!  You are now Level {new_level}!  ★")
    print()
    upgrades = draw_upgrades(player)
    say("Choose an upgrade:")
    for i, upg in enumerate(upgrades, 1):
        say(f"  {i}. {upg.label} — {upg.desc}")
    choice = _pick("Your choice (1-3):", 1, len(upgrades))
    chosen = upgrades[choice - 1]
    chosen.apply(player)
    say(f"→ {chosen.label} applied!")
    print()


# ── offer_item sub-functions ──────────────────────────────────────────────────

def offer_consumable(player, item, source=''):
    """Handle HealthPotion or Scroll offer. Returns True if taken."""
    label = f"{item.name} ({item.desc})"
    if source:
        say(f"You found: {label}.")
    if len(player.consumables) < 3:
        player.consumables.append(item)
        say(f"{item.name} added to consumables ({len(player.consumables)}/3).")
        return True
    say("Consumable slots are full (3/3).")
    say("Consumables:")
    for i, c in enumerate(player.consumables, 1):
        say(f"  {i}. {c.name}")
    say(f"  4. Leave {item.name}")
    choice = _pick("Discard which? (1-4):", 1, 4)
    if choice == 4:
        say(f"You leave the {item.name}.")
        return False
    old = player.consumables[choice - 1]
    player.consumables[choice - 1] = item
    say(f"Discarded {old.name}. Picked up {item.name}.")
    return True


def offer_weapon(player, item, source=''):
    """Handle Weapon offer. Returns True if taken."""
    if source:
        say(f"You found: {item.name} ({item.desc}).")
    if player.weapon is None:
        player.weapon    = item
        player.atk_bonus += item.bonus
        say(f"Equipped {item.name} (+{item.bonus} ATK).")
        return True
    say(f"You already have {player.weapon.name} (+{player.weapon.bonus} ATK).")
    say(f"Equip {item.name} (+{item.bonus} ATK) instead? (1=Yes, 2=No)")
    if _pick("Choice:", 1, 2) == 1:
        player.atk_bonus -= player.weapon.bonus
        player.weapon     = item
        player.atk_bonus += item.bonus
        say(f"Equipped {item.name}.")
        return True
    say(f"You leave the {item.name}.")
    return False


def offer_armour(player, item, source=''):
    """Handle Armour offer. Returns True if taken."""
    if source:
        say(f"You found: {item.name} ({item.desc}).")
    if player.armour is None:
        player.armour    = item
        player.defense  += item.bonus
        say(f"Equipped {item.name} (+{item.bonus} DEF).")
        return True
    say(f"You already have {player.armour.name} (+{player.armour.bonus} DEF).")
    say(f"Equip {item.name} (+{item.bonus} DEF) instead? (1=Yes, 2=No)")
    if _pick("Choice:", 1, 2) == 1:
        player.defense  -= player.armour.bonus
        player.armour    = item
        player.defense  += item.bonus
        say(f"Equipped {item.name}.")
        return True
    say(f"You leave the {item.name}.")
    return False


def offer_item(player, item, source=''):
    """Dispatch to the right offer sub-function. Returns True if item was taken."""
    if isinstance(item, (HealthPotion, Scroll)):
        return offer_consumable(player, item, source)
    elif isinstance(item, Weapon):
        return offer_weapon(player, item, source)
    elif isinstance(item, Armour):
        return offer_armour(player, item, source)
    return False


# ── do_merchant ───────────────────────────────────────────────────────────────

def do_merchant(room, player, floor_num):
    """Display merchant wares. Purchasing is handled by cmd_buy / cmd_reroll."""
    print()
    say("A hooded merchant eyes you from the shadows.")
    if not room.merchant_items:
        say("'I have nothing left to sell.'")
        print()
        return
    say(f"'Browse my wares. You have {player.gold} gold.'")
    print()
    for i, (item, price) in enumerate(zip(room.merchant_items, room.merchant_prices), 1):
        say(f"  {i}. {item.name} — {item.desc}  [{price} gold]")
    reroll_note = " (used)" if room.merchant_rerolled else ""
    say(f"  buy [1-{len(room.merchant_items)}] to purchase  |  reroll for 10 gold{reroll_note}")
    print()


# ── Individual command handlers ───────────────────────────────────────────────

def cmd_attack(tokens, player, room, floor_num, boss_room):
    enemy = room.enemy
    if not enemy or not enemy.alive:
        return CommandResult(messages=['There is nothing to attack.'])
    dmg = player.roll_attack()
    enemy.take_damage(dmg)
    msgs = [f"You strike the {enemy.name} for {dmg} damage!"]
    if not enemy.alive:
        msgs.append(f"The {enemy._name} crumples to the ground. Victory!")
    else:
        msgs.append(f"The {enemy.name} staggers — {enemy.hp}/{enemy.max_hp} HP.")
    return CommandResult(turn_used=True, messages=msgs)


def cmd_heavy_strike(tokens, player, room, floor_num, boss_room):
    if not player.hs_unlocked:
        return CommandResult(messages=['Heavy Strike is not unlocked. Level up to learn it.'])
    if player.hs_cooldown > 0:
        return CommandResult(messages=[f"Heavy Strike is on cooldown ({player.hs_cooldown} turn(s) remaining)."])
    enemy = room.enemy
    if not enemy or not enemy.alive:
        return CommandResult(messages=['There is nothing to attack.'])
    dmg = player.roll_heavy()
    enemy.take_damage(dmg)
    player.hs_cooldown = player.hs_max_cd
    msgs = [f"HEAVY STRIKE! You slam the {enemy.name} for {dmg} damage!"]
    if not enemy.alive:
        msgs.append(f"The {enemy._name} is obliterated. Victory!")
    else:
        msgs.append(f"The {enemy.name} reels — {enemy.hp}/{enemy.max_hp} HP.")
    return CommandResult(turn_used=True, messages=msgs)


def cmd_move(tokens, player, room, floor_num, boss_room):
    if len(tokens) < 2 or tokens[1] not in DIRECTIONS:
        return CommandResult(messages=[f"Move where? ({', '.join(DIRECTIONS)})"])
    direction = tokens[1]
    if direction not in room.exits:
        return CommandResult(messages=[f"There is no door to the {direction}."])
    if room.enemy and room.enemy.alive:
        return CommandResult(messages=[f"You can't leave — {room.enemy.name} blocks the way!"])
    return CommandResult(messages=[f"You move {direction}."], new_room=room.exits[direction])


def cmd_look(tokens, player, room, floor_num, boss_room):
    room.exits_revealed = True  # reveal exits in Collapsed Tunnel
    if room.type == 'boss':
        msgs = ["The chamber reeks of blood. Shadows writhe on the walls."]
    else:
        msgs = [f"{room.theme_name}: {room.theme_desc}"]
        # Show active theme modifier info
        if room.theme_name == 'Damp Cave':
            msgs.append("[Damp Cave: +2 DEF while present, 3 chip damage on first entry]")
        elif room.theme_name == 'Torchlit Corridor':
            msgs.append("[Torchlit Corridor: +2 ATK while present]")
        elif room.theme_name == 'Forgotten Chamber':
            msgs.append("[Forgotten Chamber: undead variant enemies, higher item chance]")
        elif room.theme_name == 'Collapsed Tunnel':
            msgs.append("[Collapsed Tunnel: exits were hidden — now revealed]")
        if room.type == 'staircase':
            msgs.append("A stone staircase descends into the darkness below.")
            if boss_room and boss_room.enemy and boss_room.enemy.alive:
                msgs.append("The staircase is sealed — defeat the boss first.")
        elif room.type == 'rest':
            if room.rest_used:
                msgs.append("The rest spot here is depleted.")
            else:
                msgs.append("This place offers rest. (type 'rest' to recover fully)")
        elif room.type == 'merchant':
            msgs.append("A hooded merchant sits quietly in the corner.")
            if room.merchant_items:
                msgs.append("Wares:")
                for i, (item, price) in enumerate(zip(room.merchant_items, room.merchant_prices), 1):
                    msgs.append(f"  {i}. {item.name} — {item.desc}  [{price} gold]")
            else:
                msgs.append("The merchant has nothing left to sell.")
        elif room.flavour:
            msgs.append(room.flavour)
    if room.enemy and room.enemy.alive:
        msgs.append(f"{room.enemy.name} ({room.enemy.hp}/{room.enemy.max_hp} HP) faces you.")
    if room.item:
        msgs.append(f"There is a {room.item.name} on the ground.")
    exits = ', '.join(d for d in DIRECTIONS if d in room.exits) or 'none'
    msgs.append(f"Exits: {exits}")
    return CommandResult(messages=msgs)


def cmd_health(tokens, player, room, floor_num, boss_room):
    return CommandResult(messages=[f"You check yourself: {player.hp}/{player.max_hp} HP."])


def cmd_inventory(tokens, player, room, floor_num, boss_room):
    msgs = ['── Inventory ──']
    msgs.append(f"Weapon : {player.weapon.name + ' (+' + str(player.weapon.bonus) + ' ATK)' if player.weapon else 'none'}")
    msgs.append(f"Armour : {player.armour.name + ' (+' + str(player.armour.bonus) + ' DEF)' if player.armour else 'none'}")
    if player.consumables:
        for i, c in enumerate(player.consumables, 1):
            msgs.append(f"  [{i}] {c.name} — {c.desc}")
    else:
        msgs.append("  Consumables: empty")
    msgs.append(f"Gold   : {player.gold}")
    msgs.append(f"Level {player.level} | XP: {player.xp}/{xp_threshold(player.level)}")
    if player.hs_unlocked:
        cd = f"{player.hs_cooldown}t cooldown" if player.hs_cooldown else "ready"
        msgs.append(f"Heavy Strike: unlocked ({cd}, max cooldown {player.hs_max_cd}t)")
    return CommandResult(messages=msgs)


def cmd_use(tokens, player, room, floor_num, boss_room):
    if len(tokens) < 2:
        return CommandResult(messages=['Use what? (e.g. use potion, use 1)'])
    target = tokens[1]
    if not player.consumables:
        return CommandResult(messages=['You have no consumables.'])
    item = idx = None
    if target.isdigit():
        i = int(target) - 1
        if 0 <= i < len(player.consumables):
            item, idx = player.consumables[i], i
    else:
        for i, c in enumerate(player.consumables):
            if target in c.name.lower():
                item, idx = c, i
                break
    if item is None:
        return CommandResult(messages=[f"No item matching '{target}'. Check 'inventory'."])
    msgs = []
    enemy = room.enemy
    if isinstance(item, HealthPotion):
        before = player.hp
        player.heal(40)
        msgs.append(f"You drink the {item.name}, restoring {player.hp - before} HP.")
    elif isinstance(item, Scroll):
        if item.effect == 'full_heal':
            player.full_heal()
            msgs.append("The Healing Scroll washes over you. HP fully restored!")
        elif item.effect == 'stun':
            if not enemy or not enemy.alive:
                return CommandResult(messages=['There is no enemy to stun.'])  # item NOT consumed
            enemy.stunned = True
            msgs.append(f"The Stun Scroll crackles! {enemy.name} is stunned for 1 turn.")
        elif item.effect == 'double_dmg':
            player.double_dmg = 3
            msgs.append("The Fury Scroll ignites your veins — double damage for 3 turns!")
    player.consumables.pop(idx)
    return CommandResult(messages=msgs)


def cmd_equip(tokens, player, room, floor_num, boss_room):
    if not room.item:
        return CommandResult(messages=['There is nothing on the ground to equip.'])
    if not isinstance(room.item, (Weapon, Armour)):
        return CommandResult(messages=[f"You cannot equip {room.item.name}."])
    taken = offer_item(player, room.item)
    if taken:
        room.item = None
    return CommandResult()


def cmd_descend(tokens, player, room, floor_num, boss_room):
    if room.type != 'staircase':
        return CommandResult(messages=['There is no staircase here.'])
    if room.enemy and room.enemy.alive:
        return CommandResult(messages=[f"You can't descend — {room.enemy.name} blocks the staircase!"])
    if boss_room and boss_room.enemy and boss_room.enemy.alive:
        return CommandResult(messages=['The staircase is sealed. Defeat the boss first!'])
    return CommandResult(messages=['You descend the staircase into deeper darkness...'], descended=True)


def cmd_map(tokens, player, room, floor_num, boss_room):
    return CommandResult(action='map')


def cmd_save(tokens, player, room, floor_num, boss_room):
    can = (room.type in ('empty', 'rest') or
           (room.type == 'boss' and room.enemy and not room.enemy.alive))
    if not can:
        return CommandResult(messages=['You can only save in empty rooms, rest rooms, or after defeating a boss.'])
    return CommandResult(action='save')


def cmd_load(tokens, player, room, floor_num, boss_room):
    return CommandResult(action='load')


def cmd_rest(tokens, player, room, floor_num, boss_room):
    if room.type != 'rest':
        return CommandResult(messages=["There is no place to rest here."])
    if room.enemy and room.enemy.alive:
        return CommandResult(messages=[f"You can't rest with {room.enemy.name} threatening you!"])
    if room.rest_used:
        return CommandResult(messages=["This rest spot is depleted. There is nothing more to gain here."])
    room.rest_used = True
    player.full_heal()
    flavour = REST_FLAVOUR.get(room.theme_name, "You rest and recover fully.")
    return CommandResult(messages=[flavour, f"HP fully restored! ({player.hp}/{player.max_hp})"])


def cmd_buy(tokens, player, room, floor_num, boss_room):
    if room.type != 'merchant':
        return CommandResult(messages=["There is no merchant here."])
    if not room.merchant_items:
        return CommandResult(messages=["The merchant has nothing left to sell."])
    if len(tokens) < 2 or not tokens[1].isdigit():
        return CommandResult(messages=["Buy what? (e.g. buy 1, buy 2)"])
    idx = int(tokens[1]) - 1
    if idx < 0 or idx >= len(room.merchant_items):
        return CommandResult(messages=[f"No item {tokens[1]}. There are {len(room.merchant_items)} item(s)."])
    price = room.merchant_prices[idx]
    item  = room.merchant_items[idx]
    if player.gold < price:
        return CommandResult(messages=[
            f"You can't afford {item.name} ({price} gold). You have {player.gold} gold."
        ])
    player.gold -= price
    room.merchant_items.pop(idx)
    room.merchant_prices.pop(idx)
    msgs = [f"You spend {price} gold. Gold remaining: {player.gold}."]
    offer_item(player, item)
    if room.merchant_items:
        msgs.append("Remaining wares:")
        for i, (it, pr) in enumerate(zip(room.merchant_items, room.merchant_prices), 1):
            msgs.append(f"  {i}. {it.name} — {it.desc}  [{pr} gold]")
    else:
        msgs.append("The merchant's stock is exhausted.")
    return CommandResult(messages=msgs)


def cmd_reroll(tokens, player, room, floor_num, boss_room):
    if room.type != 'merchant':
        return CommandResult(messages=["There is no merchant here."])
    if room.merchant_rerolled:
        return CommandResult(messages=["You have already rerolled this merchant's stock."])
    REROLL_COST = 10
    if player.gold < REROLL_COST:
        return CommandResult(messages=[
            f"Rerolling costs {REROLL_COST} gold. You have {player.gold} gold."
        ])
    player.gold -= REROLL_COST
    room.merchant_rerolled = True
    from floor import generate_merchant_stock
    items, prices = generate_merchant_stock(floor_num)
    room.merchant_items  = items
    room.merchant_prices = prices
    msgs = [f"The merchant reshuffles their wares. ({REROLL_COST} gold spent)  Gold: {player.gold}"]
    msgs.append("New stock:")
    for i, (item, price) in enumerate(zip(room.merchant_items, room.merchant_prices), 1):
        msgs.append(f"  {i}. {item.name} — {item.desc}  [{price} gold]")
    return CommandResult(messages=msgs)


def cmd_help(tokens, player, room, floor_num, boss_room):
    say("Commands: attack (a) | heavy strike (hs) | move <dir> (mn/ms/me/mw)")
    say("          look (l) | health (h) | inventory (i) | use <item> (u)")
    say("          equip | descend (d) | map (m) | save (sv) | load (ld) | quit")
    say("          rest (r) | buy [n] (b [n]) | reroll (rr)")
    return CommandResult()


def cmd_quit(tokens, player, room, floor_num, boss_room):
    print("\n  You retreat into the darkness. Farewell.\n")
    sys.exit(0)


# ── Command routing table and dispatcher ─────────────────────────────────────

COMMAND_HANDLERS = {
    'attack':    cmd_attack,
    'heavy':     cmd_heavy_strike,
    'move':      cmd_move,
    'look':      cmd_look,
    'health':    cmd_health,
    'inventory': cmd_inventory,
    'use':       cmd_use,
    'equip':     cmd_equip,
    'descend':   cmd_descend,
    'map':       cmd_map,
    'save':      cmd_save,
    'load':      cmd_load,
    'rest':      cmd_rest,
    'buy':       cmd_buy,
    'reroll':    cmd_reroll,
    'help':      cmd_help,
    '?':         cmd_help,
    'quit':      cmd_quit,
    'exit':      cmd_quit,
    'q':         cmd_quit,
}


def dispatch(raw, player, room, floor_num, boss_room):
    tokens = raw.strip().lower().split()
    if not tokens:
        return CommandResult(messages=['(nothing)'])
    handler = COMMAND_HANDLERS.get(tokens[0])
    if handler is None:
        return CommandResult(messages=[f"Unknown command '{raw}'. Type 'help' for options."])
    return handler(tokens, player, room, floor_num, boss_room)
