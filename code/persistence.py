import json
import os

from constants import SAVE_FILE
from items import item_from_dict
from player import Player
from room import Room
from enemy import enemy_from_dict


def save_game(player, rooms, current_room, floor_num, boss_room):
    data = {
        'floor_num': floor_num,
        'ng_plus_cycle': player.ng_plus_cycle,
        'current_room': [current_room.col, current_room.row],
        'boss_room': [boss_room.col, boss_room.row] if boss_room else None,
        'player': player.to_dict(),
        'rooms': [r.to_dict() for r in rooms],
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_game():
    """Returns (player, rooms, current_room, floor_num, boss_room) or None."""
    if not os.path.exists(SAVE_FILE):
        return None
    with open(SAVE_FILE) as f:
        data = json.load(f)

    # First pass: build room objects (no exits yet)
    rooms_by_pos = {}
    for rd in data['rooms']:
        r = Room.from_dict(rd)
        rooms_by_pos[(r.col, r.row)] = r

    # Second pass: link exits
    for rd in data['rooms']:
        r = rooms_by_pos[(rd['col'], rd['row'])]
        for d, (nc, nr) in rd['exits'].items():
            r.exits[d] = rooms_by_pos[(nc, nr)]

    rooms        = list(rooms_by_pos.values())
    current_room = rooms_by_pos[tuple(data['current_room'])]
    boss_room    = (rooms_by_pos[tuple(data['boss_room'])]
                    if data['boss_room'] else None)
    player       = Player.from_dict(data['player'])
    floor_num    = data['floor_num']
    return player, rooms, current_room, floor_num, boss_room
