import random


def run_enemy_turn(enemy, player, msgs):
    if enemy.stunned:
        enemy.stunned = False
        msgs.append(f"The {enemy.name} is stunned and cannot attack!")
        return
    dmg_raw  = enemy.roll_damage()
    dmg_took = player.take_damage(dmg_raw)
    msgs.append(f"The {enemy.name} strikes back for {dmg_took} damage!")


def run_boss_turn(boss, player, msgs):
    if boss.stunned:
        boss.stunned     = False
        boss.telegraphing = False   # stun cancels wind-up
        msgs.append(f"{boss._name} is stunned and cannot attack!")
        return

    if boss.telegraphing:
        dmg_raw  = boss.dmg_max * 3
        dmg_took = player.take_damage(dmg_raw)
        msgs.append(f"{boss._name}'s DEVASTATING BLOW strikes you for {dmg_took} damage!")
        boss.telegraphing = False
        return

    # Normal attack; phase 2 = twice
    attacks = 2 if boss.phase == 2 else 1
    for _ in range(attacks):
        dmg_raw  = boss.roll_damage()
        dmg_took = player.take_damage(dmg_raw)
        msgs.append(f"{boss._name} strikes you for {dmg_took} damage!")
        if not player.alive:
            return

    # Maybe wind up a telegraphed attack (boss 2+)
    if boss.boss_num >= 2 and not boss.telegraphing and random.random() < 0.3:
        boss.telegraphing = True
        msgs.append(f"{boss._name} winds up for a devastating blow... BRACE YOURSELF!")
