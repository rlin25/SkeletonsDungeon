from dataclasses import dataclass, field
from typing import Optional
import sys
import random

from constants import DIRECTIONS, ABBREVS, OPPOSITES, xp_threshold, REST_FLAVOUR
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


# ── _apply_trap helper ────────────────────────────────────────────────────────

def _apply_trap(room, player, floor_num, msgs):
    """Fire the trap effect. Caller sets room.trap_triggered = True after."""
    t = room.trap_type
    if t == 'spike_pit':
        damage = 15 + floor_num * 2
        actual = player.take_damage(damage)
        player.run_stats['damage_taken'] += actual
        msgs.append(f"The spike pit deals {actual} damage!")
    elif t == 'poison_vent':
        player.apply_status('poisoned', 3)
        msgs.append("Poison gas floods the room! You are Poisoned for 3 turns.")
    elif t == 'alarm':
        room.alarm_pending = True
        msgs.append("The alarm sounds! You hear footsteps approaching nearby...")
    elif t == 'binding_snare':
        player.apply_status('stunned', 1)
        msgs.append("The snare tightens! You will be stunned at the start of your next turn.")
    elif t == 'collapse':
        actual = player.take_damage(10)
        player.run_stats['damage_taken'] += actual
        msgs.append(f"The ceiling collapses! {actual} damage taken.")
        if room.exits:
            removed = random.choice(list(room.exits.keys()))
            neighbor = room.exits.pop(removed)
            opp = OPPOSITES[removed]
            if opp in neighbor.exits and neighbor.exits[opp] is room:
                del neighbor.exits[opp]
            msgs.append(f"The {removed} exit is blocked by rubble!")


# ── Individual command handlers ───────────────────────────────────────────────

def cmd_attack(tokens, player, room, floor_num, boss_room):
    alive = [e for e in room.enemies if e.alive]
    if not alive:
        return CommandResult(messages=['There is nothing to attack.'])

    # Select target
    if len(alive) == 1:
        target = alive[0]
    else:
        if len(tokens) >= 2 and tokens[1].isdigit():
            idx = int(tokens[1]) - 1
            if 0 <= idx < len(alive):
                target = alive[idx]
            else:
                return CommandResult(messages=[f"Invalid target. Choose 1\u2013{len(alive)}."])
        else:
            msgs = ["Multiple enemies \u2014 specify target:"]
            for i, e in enumerate(alive, 1):
                fx = ' '.join(f"[{k.capitalize()}:{v}]" for k, v in e.status_effects.items())
                if getattr(e, 'enraged', False):
                    fx += ' [ENRAGED]'
                msgs.append(f"  {i}. {e.name} ({e.hp}/{e.max_hp} HP){' ' + fx if fx else ''}")
            msgs.append("Usage: attack 1, attack 2, etc.")
            return CommandResult(messages=msgs)

    msgs = []
    # Check shield (elites/final boss only)
    from combat import check_elite_shield, check_final_boss_shield, check_elite_hp_abilities, check_final_boss_hp_abilities
    if getattr(target, 'is_elite', False):
        if check_elite_shield(target, msgs):
            return CommandResult(turn_used=True, messages=msgs)
    elif getattr(target, 'is_final_boss', False):
        if check_final_boss_shield(target, msgs):
            return CommandResult(turn_used=True, messages=msgs)

    dmg = player.roll_attack()
    target.take_damage(dmg)
    player.run_stats['damage_dealt'] += dmg
    msgs.append(f"You strike the {target.name} for {dmg} damage!")

    # Check HP-triggered abilities (elite/final boss) after taking damage
    if getattr(target, 'is_elite', False):
        check_elite_hp_abilities(target, msgs)
    elif getattr(target, 'is_final_boss', False):
        check_final_boss_hp_abilities(target, msgs)

    if not target.alive:
        msgs.append(f"The {target._name} crumples to the ground. Victory!")
    else:
        fx = ' '.join(f"[{k.capitalize()}:{v}]" for k, v in target.status_effects.items())
        if getattr(target, 'enraged', False):
            fx += ' [ENRAGED]'
        fx_str = f" {fx}" if fx else ''
        msgs.append(f"The {target.name} staggers \u2014 {target.hp}/{target.max_hp} HP.{fx_str}")
    return CommandResult(turn_used=True, messages=msgs)


def cmd_heavy_strike(tokens, player, room, floor_num, boss_room):
    if not player.hs_unlocked:
        return CommandResult(messages=['Heavy Strike is not unlocked. Level up to learn it.'])
    if player.hs_cooldown > 0:
        return CommandResult(messages=[f"Heavy Strike is on cooldown ({player.hs_cooldown} turn(s) remaining)."])

    alive = [e for e in room.enemies if e.alive]
    if not alive:
        return CommandResult(messages=['There is nothing to attack.'])

    # Select target — note: after normalize, 'hs 2' becomes tokens=['heavy','strike','2']
    # so the target number is at tokens[2] (index 2), not tokens[1]
    if len(alive) == 1:
        target = alive[0]
    else:
        # Check tokens[2] for target number (tokens[1] == 'strike' after expansion)
        target_token = tokens[2] if len(tokens) >= 3 else None
        if target_token and target_token.isdigit():
            idx = int(target_token) - 1
            if 0 <= idx < len(alive):
                target = alive[idx]
            else:
                return CommandResult(messages=[f"Invalid target. Choose 1\u2013{len(alive)}."])
        else:
            msgs = ["Multiple enemies \u2014 specify target:"]
            for i, e in enumerate(alive, 1):
                fx = ' '.join(f"[{k.capitalize()}:{v}]" for k, v in e.status_effects.items())
                if getattr(e, 'enraged', False):
                    fx += ' [ENRAGED]'
                msgs.append(f"  {i}. {e.name} ({e.hp}/{e.max_hp} HP){' ' + fx if fx else ''}")
            msgs.append("Usage: heavy strike 1, heavy strike 2, etc.  (or: hs 1, hs 2)")
            return CommandResult(messages=msgs)

    msgs = []
    # Check shield (elites/final boss only)
    from combat import check_elite_shield, check_final_boss_shield, check_elite_hp_abilities, check_final_boss_hp_abilities
    if getattr(target, 'is_elite', False):
        if check_elite_shield(target, msgs):
            player.hs_cooldown = player.hs_max_cd
            return CommandResult(turn_used=True, messages=msgs)
    elif getattr(target, 'is_final_boss', False):
        if check_final_boss_shield(target, msgs):
            player.hs_cooldown = player.hs_max_cd
            return CommandResult(turn_used=True, messages=msgs)

    dmg = player.roll_heavy()
    target.take_damage(dmg)
    player.run_stats['damage_dealt'] += dmg
    player.hs_cooldown = player.hs_max_cd
    msgs.append(f"HEAVY STRIKE! You slam the {target.name} for {dmg} damage!")

    # Check HP-triggered abilities (elite/final boss) after taking damage
    if getattr(target, 'is_elite', False):
        check_elite_hp_abilities(target, msgs)
    elif getattr(target, 'is_final_boss', False):
        check_final_boss_hp_abilities(target, msgs)

    if not target.alive:
        msgs.append(f"The {target._name} is obliterated. Victory!")
    else:
        fx = ' '.join(f"[{k.capitalize()}:{v}]" for k, v in target.status_effects.items())
        if getattr(target, 'enraged', False):
            fx += ' [ENRAGED]'
        fx_str = f" {fx}" if fx else ''
        msgs.append(f"The {target.name} reels \u2014 {target.hp}/{target.max_hp} HP.{fx_str}")
    return CommandResult(turn_used=True, messages=msgs)


def cmd_move(tokens, player, room, floor_num, boss_room):
    if len(tokens) < 2 or tokens[1] not in DIRECTIONS:
        return CommandResult(messages=[f"Move where? ({', '.join(DIRECTIONS)})"])
    direction = tokens[1]
    if direction not in room.exits:
        return CommandResult(messages=[f"There is no door to the {direction}."])
    alive = [e for e in room.enemies if e.alive]
    if alive:
        return CommandResult(messages=[f"You can't leave \u2014 {alive[0].name} blocks the way!"])
    return CommandResult(messages=[f"You move {direction}."], new_room=room.exits[direction])


def cmd_look(tokens, player, room, floor_num, boss_room):
    room.exits_revealed = True  # reveal exits in Collapsed Tunnel
    if room.type == 'final_boss':
        msgs = [
            "The air crackles with ancient power. Runes glow malevolently across the walls.",
            "This is the lair of The Dungeon Architect \u2014 the force that shaped this nightmare.",
        ]
    elif room.type == 'boss':
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
            msgs.append("[Collapsed Tunnel: exits were hidden \u2014 now revealed]")
        if room.type == 'staircase':
            msgs.append("A stone staircase descends into the darkness below.")
            if boss_room and any(e.alive for e in boss_room.enemies):
                msgs.append("The staircase is sealed \u2014 defeat the boss first.")
        elif room.type == 'trap':
            if room.trap_disarmed:
                msgs.append(f"A disarmed {room.trap_type.replace('_', ' ')} trap sits harmlessly here.")
            elif room.trap_triggered:
                msgs.append(f"A spent {room.trap_type.replace('_', ' ')} trap is here — the danger has passed.")
            else:
                msgs.append(f"You sense danger here. There is a {room.trap_type.replace('_', ' ')} trap!")
                msgs.append("Type 'disarm' to attempt disarming it, or 'proceed' to push through.")
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

    # Display all alive enemies
    alive_enemies = [e for e in room.enemies if e.alive]
    for e in alive_enemies:
        fx = ' '.join(f"[{k.capitalize()}:{v}]" for k, v in e.status_effects.items())
        if getattr(e, 'enraged', False):
            fx += ' [ENRAGED]'
        elite_tag = ' [ELITE]' if getattr(e, 'is_elite', False) else ''
        boss_tag = ' [FINAL BOSS]' if getattr(e, 'is_final_boss', False) else ''
        fx_str = f"  {fx}" if fx else ''
        msgs.append(f"{e.name}{elite_tag}{boss_tag} ({e.hp}/{e.max_hp} HP){fx_str} faces you.")

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
    # Get first alive enemy for scroll effects that target enemies
    enemy = None
    for e in room.enemies:
        if e.alive:
            enemy = e
            break
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
        elif item.effect == 'poison_enemy':
            if not enemy or not enemy.alive:
                return CommandResult(messages=['There is no enemy to poison.'])  # item NOT consumed
            enemy.status_effects['poisoned'] = 3
            msgs.append(f"The Poison Scroll dissolves! {enemy.name} is Poisoned for 3 turns.")
        elif item.effect == 'burn_enemy':
            if not enemy or not enemy.alive:
                return CommandResult(messages=['There is no enemy to burn.'])  # item NOT consumed
            enemy.status_effects['burned'] = 3
            msgs.append(f"The Burn Scroll ignites! {enemy.name} is Burned for 3 turns.")
    player.run_stats['items_used'] += 1
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
    alive = [e for e in room.enemies if e.alive]
    if alive:
        return CommandResult(messages=[f"You can't descend \u2014 {alive[0].name} blocks the staircase!"])
    if boss_room and any(e.alive for e in boss_room.enemies):
        return CommandResult(messages=['The staircase is sealed. Defeat the boss first!'])
    return CommandResult(messages=['You descend the staircase into deeper darkness...'], descended=True)


def cmd_map(tokens, player, room, floor_num, boss_room):
    return CommandResult(action='map')


def cmd_save(tokens, player, room, floor_num, boss_room):
    if room.type == 'trap':
        return CommandResult(messages=['Trap rooms are not valid save locations.'])
    can = (room.type in ('empty', 'rest') or
           (room.type in ('boss', 'final_boss') and not any(e.alive for e in room.enemies)))
    if not can:
        return CommandResult(messages=['You can only save in empty rooms, rest rooms, or after defeating a boss.'])
    return CommandResult(action='save')


def cmd_load(tokens, player, room, floor_num, boss_room):
    return CommandResult(action='load')


def cmd_rest(tokens, player, room, floor_num, boss_room):
    if room.type != 'rest':
        return CommandResult(messages=["There is no place to rest here."])
    alive = [e for e in room.enemies if e.alive]
    if alive:
        return CommandResult(messages=[f"You can't rest with {alive[0].name} threatening you!"])
    if room.rest_used:
        return CommandResult(messages=["This rest spot is depleted. There is nothing more to gain here."])
    room.rest_used = True
    player.full_heal()
    player.run_stats['times_rested'] += 1
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


def cmd_disarm(tokens, player, room, floor_num, boss_room):
    if room.type != 'trap':
        return CommandResult(messages=["There is no trap to disarm here."])
    if room.trap_triggered or room.trap_disarmed:
        return CommandResult(messages=["The trap has already been resolved."])
    chance = player.disarm_chance()
    success = random.random() * 100 < chance
    if success:
        room.trap_disarmed = True
        player.run_stats['traps_disarmed'] += 1
        trap_name = room.trap_type.replace('_', ' ').title()
        return CommandResult(messages=[
            f"Disarm chance: {chance:.0f}% \u2014 Success! The {trap_name} is neutralised.",
            "The room is now safe."
        ])
    else:
        msgs = [f"Disarm chance: {chance:.0f}% \u2014 Failed! The trap triggers!"]
        _apply_trap(room, player, floor_num, msgs)
        room.trap_triggered = True
        player.run_stats['traps_triggered'] += 1
        return CommandResult(turn_used=True, messages=msgs)


def cmd_proceed(tokens, player, room, floor_num, boss_room):
    if room.type != 'trap':
        return CommandResult(messages=["There is no trap here to proceed through."])
    if room.trap_triggered or room.trap_disarmed:
        return CommandResult(messages=["The trap has already been resolved."])
    msgs = ["You push forward through the trap..."]
    _apply_trap(room, player, floor_num, msgs)
    room.trap_triggered = True
    player.run_stats['traps_triggered'] += 1
    return CommandResult(turn_used=True, messages=msgs)


def cmd_help(tokens, player, room, floor_num, boss_room):
    say("Commands: attack (a) [n] | heavy strike (hs) [n] | move <dir> (mn/ms/me/mw)")
    say("          look (l) | health (h) | inventory (i) | use <item> (u)")
    say("          equip | descend (d) | map (m) | save (sv) | load (ld) | quit")
    say("          rest (r) | buy [n] (b [n]) | reroll (rr)")
    say("          disarm (da) | proceed (pr)")
    say("  [n] = optional enemy number when multiple enemies are present")
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
    'disarm':    cmd_disarm,
    'proceed':   cmd_proceed,
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
