import sys
import random
import time

from constants import DIRECTIONS
from floor import generate_floor
from player import Player
from combat import (run_enemy_turn, run_boss_turn, run_elite_turn,
                    run_final_boss_turn, tick_enemy_status)
from commands import dispatch, do_upgrade_draft, offer_item, do_merchant, normalize
from renderer import (draw_room, draw_map, status_line, announce_room,
                      intro_screen, game_over_screen, ask_restart, rule, say,
                      win_screen)
from persistence import save_game, load_game
from enemy import Boss, EliteEnemy, FinalBoss
from items import random_item


def on_room_enter(player, room):
    """Apply entry effects for the room's theme."""
    if room.theme_name == 'Torchlit Corridor':
        player.atk_bonus += 2
        player.temp_atk   = 2
        say("[Torchlit Corridor: +2 ATK while in this room]")
    elif room.theme_name == 'Damp Cave':
        player.defense += 2
        player.temp_def  = 2
        say("[Damp Cave: +2 DEF while in this room]")
        if not room.chip_dealt:
            room.chip_dealt = True
            actual = player.take_damage(3)
            player.run_stats['damage_taken'] += actual
            if actual > 0:
                say(f"The slippery stone underfoot trips you — {actual} chip damage!")
            else:
                say("The slippery stone underfoot is treacherous, but your armour absorbs it.")

    # Auto-collect room gold
    if room.gold > 0:
        gold = room.gold
        player.gold += gold
        player.run_stats['total_gold_earned'] += gold
        room.gold = 0
        say(f"You find {gold} gold coins.")


def on_room_exit(player, room):
    """Remove temporary theme effects when leaving a room."""
    player.atk_bonus -= player.temp_atk
    player.defense   -= player.temp_def
    player.temp_atk   = 0
    player.temp_def   = 0


def _start_ng_plus(player):
    """Prepare player for NG+ run: carry stats, reset economy/gear."""
    player.ng_plus_cycle += 1
    player.hp = player.max_hp  # full heal
    # Remove weapon bonus before clearing weapon
    if player.weapon:
        player.atk_bonus -= player.weapon.bonus
        player.weapon = None
    # Remove armour bonus before clearing armour
    if player.armour:
        player.defense -= player.armour.bonus
        player.armour = None
    player.consumables = []
    player.gold = 0
    player.xp = 0
    player.hs_cooldown = 0
    player.double_dmg = 0
    player.status_effects = {}
    player.temp_atk = 0
    player.temp_def = 0
    player.run_stats = {
        'floors_cleared':    0,
        'enemies_killed':    0,
        'elites_killed':     0,
        'bosses_defeated':   0,
        'total_gold_earned': 0,
        'damage_dealt':      0,
        'damage_taken':      0,
        'times_rested':      0,
        'items_used':        0,
        'traps_disarmed':    0,
        'traps_triggered':   0,
        'turns_taken':       0,
        'start_time':        time.time(),
    }


def run_game(ng_player=None):
    """Run one game session. ng_player: carry-over Player for NG+ runs."""
    player = ng_player if ng_player is not None else Player()

    ng_plus_pending = ng_player is not None  # True on first entry when NG+ player passed in

    while True:  # NG+ outer loop — restarts here when player chooses ng+
        floor_num = 1
        rooms, current_room, boss_room = generate_floor(floor_num, player.ng_plus_cycle)
        final_boss_room = next((r for r in rooms if r.type == 'final_boss'), None)
        current_room.visited = True
        alarm_active = False

        if not ng_plus_pending:
            intro_screen()
        else:
            print()
            say(f"[NG+{player.ng_plus_cycle}] — A new descent begins.")
            ng_plus_pending = False

        rule()
        say(f"Floor {floor_num}. You enter the dungeon.")
        announce_room(current_room, boss_room)
        on_room_enter(player, current_room)
        print()
        rule()
        draw_room(player, current_room, floor_num, rooms)
        rule()

        # ── Inner game loop ────────────────────────────────────────────────────
        game_over   = False
        ng_requested = False

        while True:
            try:
                raw = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Interrupted. Farewell.\n")
                sys.exit(0)

            raw = normalize(raw)

            # ── Player status ticks (stun, poison, burn) ──────────────────────
            was_stunned = player.status_effects.get('stunned', 0) > 0
            tick_msgs = player.tick_status_effects(floor_num)
            for m in tick_msgs:
                say(m)

            if was_stunned:
                say("You are stunned and cannot act this turn!")
                # Force enemy retaliation without player action
                alive_enemies = [e for e in current_room.enemies if e.alive]
                for enemy in alive_enemies:
                    if not player.alive:
                        break
                    if isinstance(enemy, FinalBoss):
                        run_final_boss_turn(enemy, player, current_room, floor_num, [])
                    elif isinstance(enemy, Boss):
                        run_boss_turn(enemy, player, [], floor_num)
                    elif isinstance(enemy, EliteEnemy):
                        run_elite_turn(enemy, player, current_room, floor_num, [])
                    else:
                        run_enemy_turn(enemy, player, [], floor_num)
                player.tick()
                player.run_stats['turns_taken'] += 1
                print()
                rule()
                draw_room(player, current_room, floor_num, rooms)
                if not player.alive:
                    rule()
                    game_over_screen(floor_num)
                    game_over = True
                    break
                rule()
                continue

            # ── Capture alive enemies BEFORE dispatch (for kill tracking) ─────
            alive_before = [e for e in current_room.enemies if e.alive]

            result = dispatch(raw, player, current_room, floor_num, boss_room)

            # ── FinalBoss phase 2 transition (BEFORE retaliation) ─────────────
            if result.turn_used:
                for enemy in current_room.enemies:
                    if isinstance(enemy, FinalBoss) and enemy.alive:
                        if enemy.check_phase_transition():
                            result.messages.append("")
                            result.messages.append("*** The Dungeon Architect SHATTERS — its form dissolving into shadow. ***")
                            result.messages.append("*** From the darkness, it rises again, larger and more terrible than before. ***")
                            result.messages.append(f"*** THE DUNGEON ARCHITECT RISES ANEW — {enemy.hp}/{enemy.max_hp} HP! ALL ABILITIES ACTIVE! ***")
                            result.messages.append("")

            # ── Boss phase 2 check for regular bosses ─────────────────────────
            if result.turn_used:
                for enemy in current_room.enemies:
                    if isinstance(enemy, Boss) and not isinstance(enemy, FinalBoss) and enemy.alive:
                        if enemy.check_phase_transition():
                            result.messages.append(
                                f"*** {enemy._name} ENTERS PHASE 2 — it attacks twice per turn! ***"
                            )

            # ── Enemy / boss retaliation ───────────────────────────────────────
            if result.turn_used:
                hp_before = player.hp
                alive_enemies = [e for e in current_room.enemies if e.alive]
                for enemy in alive_enemies:
                    if not player.alive:
                        break
                    if isinstance(enemy, FinalBoss):
                        run_final_boss_turn(enemy, player, current_room, floor_num, result.messages)
                    elif isinstance(enemy, Boss):
                        run_boss_turn(enemy, player, result.messages, floor_num)
                    elif isinstance(enemy, EliteEnemy):
                        run_elite_turn(enemy, player, current_room, floor_num, result.messages)
                    else:
                        run_enemy_turn(enemy, player, result.messages, floor_num)
                if not player.alive:
                    result.messages.append("Everything goes dark...")
                hp_after = player.hp
                player.run_stats['damage_taken'] += max(0, hp_before - hp_after)

            # ── Tick cooldowns ────────────────────────────────────────────────
            if result.turn_used:
                player.tick()
                player.run_stats['turns_taken'] += 1

            # ── Per-enemy kill tracking ────────────────────────────────────────
            won_this_turn = False
            xp_gained_total = 0
            dropped_items = []

            for enemy in alive_before:
                if not enemy.alive:
                    # This enemy was killed this turn
                    gold_scale = 1 + (floor_num - 1) * 0.1
                    xp_gained_this_enemy = enemy.xp_value(floor_num)
                    xp_gained_total += xp_gained_this_enemy
                    dropped_item = None

                    if isinstance(enemy, FinalBoss):
                        player.run_stats['bosses_defeated'] += 1
                        # Final boss guaranteed drops
                        gold_drop = 50 + random.randint(10, 30)
                        player.gold += gold_drop
                        player.run_stats['total_gold_earned'] += gold_drop
                        result.messages.append(f"The Dungeon Architect drops {gold_drop} gold!")
                        dropped_item = random_item(floor_num)
                        result.messages.append(f"The Dungeon Architect drops: {dropped_item.name}!")
                        if dropped_item:
                            offer_item(player, dropped_item, source='drop')
                        won_this_turn = True
                    elif isinstance(enemy, Boss):
                        player.run_stats['bosses_defeated'] += 1
                        gold_drop = round(random.randint(15, 30) * gold_scale)
                        player.gold += gold_drop
                        player.run_stats['total_gold_earned'] += gold_drop
                        result.messages.append(f"The boss drops {gold_drop} gold!")
                        dropped_item = random_item(floor_num)
                        result.messages.append(f"The boss drops: {dropped_item.name}!")
                    elif getattr(enemy, 'is_elite', False):
                        player.run_stats['enemies_killed'] += 1
                        player.run_stats['elites_killed'] += 1
                        # Elite guaranteed gold
                        elite_gold = (floor_num * 3) + random.randint(2, 8)
                        elite_gold = round(elite_gold * gold_scale)
                        player.gold += elite_gold
                        player.run_stats['total_gold_earned'] += elite_gold
                        result.messages.append(f"You find {elite_gold} gold (elite).")
                        if random.random() < 0.40:
                            dropped_item = random_item(floor_num)
                            result.messages.append(f"The {enemy._name} drops: {dropped_item.name}.")
                    else:
                        player.run_stats['enemies_killed'] += 1
                        gold_drop = round(random.randint(1, 5) * gold_scale)
                        player.gold += gold_drop
                        player.run_stats['total_gold_earned'] += gold_drop
                        result.messages.append(f"You find {gold_drop} gold.")
                        if random.random() < 0.2:
                            dropped_item = random_item(floor_num)
                            result.messages.append(f"The {enemy._name} drops: {dropped_item.name}.")

                    # XP
                    say(f"+{xp_gained_this_enemy} XP")
                    for lvl in player.add_xp(xp_gained_this_enemy):
                        do_upgrade_draft(player, lvl)

                    # Item drop offer (FinalBoss item already offered above)
                    if not isinstance(enemy, FinalBoss) and dropped_item:
                        dropped_items.append(dropped_item)

            # ── Win condition ─────────────────────────────────────────────────
            if won_this_turn:
                print()
                rule()
                for m in result.messages:
                    say(m)
                print()
                win_screen(player, player.run_stats, floor_num)
                # Post-win loop: only accept 'ng+' or 'quit'
                while True:
                    try:
                        raw_win = input("  > ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        return None
                    if raw_win == 'ng+':
                        _start_ng_plus(player)
                        ng_requested = True
                        break
                    elif raw_win in ('quit', 'exit', 'q'):
                        print("\n  Your legend is written. Farewell.\n")
                        sys.exit(0)
                    else:
                        say("Type 'ng+' for New Game+ or 'quit' to exit.")
                break  # break inner loop to handle ng+ in outer loop

            print()

            # ── Output / special actions ──────────────────────────────────────
            if result.action == 'map':
                draw_map(rooms, current_room, player, floor_num)
            elif result.action == 'save':
                save_game(player, rooms, current_room, floor_num, boss_room)
                say("Game saved.")
            elif result.action == 'load':
                loaded = load_game()
                if loaded:
                    player, rooms, current_room, floor_num, boss_room = loaded
                    final_boss_room = next((r for r in rooms if r.type == 'final_boss'), None)
                    say("Game loaded.")
                else:
                    say("No save file found.")
            else:
                for m in result.messages:
                    say(m)

            # ── Offer non-FinalBoss dropped items ─────────────────────────────
            for dropped_item in dropped_items:
                offer_item(player, dropped_item, source='drop')

            # ── Room navigation ───────────────────────────────────────────────
            if result.new_room:
                on_room_exit(player, current_room)
                current_room = result.new_room
                current_room.visited = True
                print()
                announce_room(current_room, boss_room)
                on_room_enter(player, current_room)

                # Handle alarm trap that fired in a previous room
                if hasattr(current_room, 'alarm_pending') and current_room.alarm_pending:
                    alarm_active = True
                    current_room.alarm_pending = False

                if alarm_active and current_room.type == 'enemy' and any(e.alive for e in current_room.enemies):
                    from enemy import Enemy
                    extra = Enemy(floor_num, player.ng_plus_cycle)
                    current_room.enemies.append(extra)
                    say("A creature emerges from the shadows in response to the alarm!")
                    alarm_active = False

                if current_room.type == 'merchant':
                    do_merchant(current_room, player, floor_num)
                elif current_room.item:
                    taken = offer_item(player, current_room.item, source='room')
                    if taken:
                        current_room.item = None

            # ── Floor descent ─────────────────────────────────────────────────
            if result.descended:
                on_room_exit(player, current_room)
                player.run_stats['floors_cleared'] += 1
                floor_num += 1
                rooms, _, boss_room = generate_floor(floor_num, player.ng_plus_cycle)
                final_boss_room = next((r for r in rooms if r.type == 'final_boss'), None)
                non_stair    = [r for r in rooms if r.type != 'staircase']
                current_room = random.choice(non_stair)
                current_room.visited = True
                alarm_active = False
                print()
                say(f"Floor {floor_num}. The air grows cold and heavy.")
                announce_room(current_room, boss_room)
                on_room_enter(player, current_room)
                if current_room.type == 'merchant':
                    do_merchant(current_room, player, floor_num)
                elif current_room.item:
                    offer_item(player, current_room.item, source='room')
                    current_room.item = None

            # ── Redraw ────────────────────────────────────────────────────────
            print()
            rule()
            draw_room(player, current_room, floor_num, rooms)

            if not player.alive:
                rule()
                game_over_screen(floor_num)
                game_over = True
                break

            rule()

        # ── End of inner loop — handle outcomes ───────────────────────────────
        if ng_requested:
            ng_plus_pending = True
            continue  # restart outer loop for NG+

        if game_over:
            return ask_restart()

        # Shouldn't normally reach here, but return False to be safe
        return False
