import sys
import random

from constants import DIRECTIONS
from floor import generate_floor
from player import Player
from combat import run_enemy_turn, run_boss_turn
from commands import dispatch, do_upgrade_draft, offer_item, do_merchant, normalize
from renderer import (draw_room, draw_map, status_line, announce_room,
                      intro_screen, game_over_screen, ask_restart, rule, say)
from persistence import save_game, load_game
from enemy import Boss
from items import random_item


def on_room_enter(player, room):
    """Called whenever the player enters a room. Apply entry effects here in Phase 4."""
    pass


def on_room_exit(player, room):
    """Called whenever the player leaves a room. Remove temporary effects here in Phase 4."""
    pass


def run_game():
    player    = Player()
    floor_num = 1
    rooms, current_room, boss_room = generate_floor(floor_num)
    current_room.visited = True

    intro_screen()
    rule()
    say(f"Floor {floor_num}. You enter the dungeon.")
    announce_room(current_room, boss_room)
    on_room_enter(player, current_room)
    print()
    rule()
    draw_room(player, current_room, floor_num)
    rule()

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Interrupted. Farewell.\n")
            sys.exit(0)

        raw = normalize(raw)

        enemy_was_alive = bool(current_room.enemy and current_room.enemy.alive)
        result = dispatch(raw, player, current_room, floor_num, boss_room)

        # Boss phase check (before retaliation so phase 2 attacks twice now)
        if (result.turn_used and current_room.enemy
                and isinstance(current_room.enemy, Boss)
                and current_room.enemy.alive
                and current_room.enemy.check_phase_transition()):
            result.messages.append(
                f"*** {current_room.enemy._name} ENTERS PHASE 2 — it attacks twice per turn! ***"
            )

        # Enemy / boss retaliation
        if result.turn_used and current_room.enemy and current_room.enemy.alive:
            if isinstance(current_room.enemy, Boss):
                run_boss_turn(current_room.enemy, player, result.messages)
            else:
                run_enemy_turn(current_room.enemy, player, result.messages)
            if not player.alive:
                result.messages.append("Everything goes dark...")

        # Tick cooldowns
        if result.turn_used:
            player.tick()

        # Enemy killed this turn
        xp_gained    = 0
        dropped_item = None
        if enemy_was_alive and current_room.enemy and not current_room.enemy.alive:
            player.full_heal()
            xp_gained = current_room.enemy.xp_value(floor_num)
            if isinstance(current_room.enemy, Boss):
                dropped_item = random_item(floor_num)
                result.messages.append(f"The boss drops: {dropped_item.name}!")
            elif random.random() < 0.2:
                dropped_item = random_item(floor_num)
                result.messages.append(f"The {current_room.enemy._name} drops: {dropped_item.name}.")

        print()

        # Output / special actions
        if result.action == 'map':
            draw_map(rooms, current_room, player, floor_num)
        elif result.action == 'save':
            save_game(player, rooms, current_room, floor_num, boss_room)
            say("Game saved.")
        elif result.action == 'load':
            loaded = load_game()
            if loaded:
                player, rooms, current_room, floor_num, boss_room = loaded
                say("Game loaded.")
            else:
                say("No save file found.")
        else:
            for m in result.messages:
                say(m)

        # XP & level-up
        if xp_gained:
            say(f"+{xp_gained} XP")
            for lvl in player.add_xp(xp_gained):
                do_upgrade_draft(player, lvl)

        # Item drop
        if dropped_item:
            offer_item(player, dropped_item, source='drop')

        # Room navigation
        if result.new_room:
            on_room_exit(player, current_room)
            current_room = result.new_room
            current_room.visited = True
            print()
            announce_room(current_room, boss_room)
            on_room_enter(player, current_room)
            if current_room.type == 'merchant':
                do_merchant(current_room, player, floor_num)
            elif current_room.item:
                taken = offer_item(player, current_room.item, source='room')
                if taken:
                    current_room.item = None

        # Floor descent
        if result.descended:
            on_room_exit(player, current_room)
            floor_num += 1
            rooms, _, boss_room = generate_floor(floor_num)
            non_stair    = [r for r in rooms if r.type != 'staircase']
            current_room = random.choice(non_stair)
            current_room.visited = True
            print()
            say(f"Floor {floor_num}. The air grows cold and heavy.")
            announce_room(current_room, boss_room)
            on_room_enter(player, current_room)
            if current_room.type == 'merchant':
                do_merchant(current_room, player, floor_num)
            elif current_room.item:
                offer_item(player, current_room.item, source='room')
                current_room.item = None

        # Redraw
        print()
        rule()
        draw_room(player, current_room, floor_num)

        if not player.alive:
            rule()
            game_over_screen(floor_num)
            return ask_restart()

        rule()
