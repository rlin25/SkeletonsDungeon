import random


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_ability(entity, name):
    """Return True if entity has the named ability.

    Works for both EliteEnemy (entity.ability == name) and
    FinalBoss (name in entity.abilities list).
    """
    if hasattr(entity, 'abilities'):   # FinalBoss
        return name in entity.abilities
    return getattr(entity, 'ability', None) == name


# ---------------------------------------------------------------------------
# Status-effect tick (called at the start of every enemy/elite/boss turn)
# ---------------------------------------------------------------------------

def tick_enemy_status(enemy, floor_num, msgs):
    """Tick poison, burn, and stunned countdown on an enemy at turn start."""
    if 'poisoned' in enemy.status_effects:
        dmg = 3 + floor_num
        enemy.take_damage(dmg)
        enemy.status_effects['poisoned'] -= 1
        if enemy.status_effects['poisoned'] <= 0:
            del enemy.status_effects['poisoned']
            msgs.append(f"The {enemy.name}'s poison wears off.")
        else:
            msgs.append(
                f"[Poisoned] {enemy.name} takes {dmg} damage! "
                f"({enemy.status_effects['poisoned']} turns remaining)"
            )
    if 'burned' in enemy.status_effects:
        dmg = 5 + floor_num
        enemy.take_damage(dmg)
        enemy.status_effects['burned'] -= 1
        if enemy.status_effects['burned'] <= 0:
            del enemy.status_effects['burned']
            msgs.append(f"The {enemy.name}'s burns fade.")
        else:
            msgs.append(
                f"[Burned] {enemy.name} takes {dmg} damage! "
                f"({enemy.status_effects['burned']} turns remaining)"
            )
    if 'stunned' in enemy.status_effects:
        enemy.status_effects['stunned'] -= 1
        if enemy.status_effects['stunned'] <= 0:
            del enemy.status_effects['stunned']


# ---------------------------------------------------------------------------
# Regular enemy turn
# ---------------------------------------------------------------------------

def run_enemy_turn(enemy, player, msgs, floor_num=1):
    """Execute a normal enemy's turn: status ticks, stun check, then attack."""
    tick_enemy_status(enemy, floor_num, msgs)
    if not enemy.alive:
        return  # DoT killed it

    # Legacy stun (set by Stun Scroll via enemy.stunned bool)
    if enemy.stunned:
        enemy.stunned = False
        msgs.append(f"The {enemy.name} is stunned and cannot attack!")
        return

    # Status-effects stun (set by abilities, decremented in tick_enemy_status)
    if enemy.status_effects.get('stunned', 0) > 0:
        # tick_enemy_status already decremented; if still present, skip turn
        if 'stunned' in enemy.status_effects:
            msgs.append(f"The {enemy.name} is stunned and cannot attack!")
            return

    dmg_raw = enemy.roll_damage()
    actual, dodged = player.attempt_damage(dmg_raw)
    if dodged:
        msgs.append("You sidestep the blow.")
    else:
        msgs.append(f"The {enemy.name} strikes back for {actual} damage!")


# ---------------------------------------------------------------------------
# Boss turn (Boss class — floor bosses with telegraphing)
# ---------------------------------------------------------------------------

def run_boss_turn(boss, player, msgs, floor_num=1):
    """Execute a floor Boss's turn: status ticks, stun/telegraph logic, attack."""
    tick_enemy_status(boss, floor_num, msgs)
    if not boss.alive:
        return  # DoT killed it

    if boss.stunned:
        boss.stunned = False
        boss.telegraphing = False   # stun cancels wind-up
        msgs.append(f"{boss._name} is stunned and cannot attack!")
        return

    if boss.telegraphing:
        dmg_raw = boss.dmg_max * 3
        actual, dodged = player.attempt_damage(dmg_raw)
        if dodged:
            msgs.append("You sidestep the devastating blow!")
        else:
            msgs.append(f"{boss._name}'s DEVASTATING BLOW strikes you for {actual} damage!")
        boss.telegraphing = False
        return

    # Normal attack; phase 2 = twice
    attacks = 2 if boss.phase == 2 else 1
    for _ in range(attacks):
        dmg_raw = boss.roll_damage()
        actual, dodged = player.attempt_damage(dmg_raw)
        if dodged:
            msgs.append("You sidestep the blow.")
        else:
            msgs.append(f"{boss._name} strikes you for {actual} damage!")
        if not player.alive:
            return

    # Maybe wind up a telegraphed attack (boss 2+)
    if boss.boss_num >= 2 and not boss.telegraphing and random.random() < 0.3:
        boss.telegraphing = True
        msgs.append(f"{boss._name} winds up for a devastating blow... BRACE YOURSELF!")


# ---------------------------------------------------------------------------
# Elite enemy helpers
# ---------------------------------------------------------------------------

def _run_elite_ability_turn(elite, player, room, floor_num, msgs):
    """Check and fire elite abilities that trigger at the start of the elite's turn.

    Returns True if a summon happened (caller may wish to know).
    """
    summoned = False
    # Summon: at start of turn 3 (attack_count == 2 before this attack)
    if elite.ability == 'summon' and not elite.ability_used and elite.attack_count == 2:
        elite.ability_used = True
        from enemy import Enemy
        new_enemy = Enemy(floor_num)
        room.enemies.append(new_enemy)
        msgs.append(f"The {elite.name} calls forth a companion from the shadows!")
        summoned = True
    return summoned


def _run_elite_after_attack(elite, player, floor_num, msgs, dmg_raw):
    """Handle post-attack ability triggers for an EliteEnemy."""
    elite.attack_count += 1
    # Stun Strike: on 3rd attack, once per fight
    if elite.ability == 'stun_strike' and not elite.ability_used and elite.attack_count == 3:
        elite.ability_used = True
        player.apply_status('stunned', 1)
        msgs.append(f"The {elite.name}'s blow leaves you reeling!")
    # Poison Strike: 40% chance per attack
    if elite.ability == 'poison_strike' and random.random() < 0.40:
        player.apply_status('poisoned', 3)
        # No announcement — status display handles feedback


def check_elite_hp_abilities(elite, msgs):
    """Check Heal and Enrage abilities triggered by HP thresholds.

    Call this AFTER player deals damage to the elite.
    """
    if not elite.alive:
        return
    # Heal: when HP drops below 40%, once per fight
    if elite.ability == 'heal' and not elite.ability_used and elite.hp < elite.max_hp * 0.40:
        elite.ability_used = True
        heal_amount = elite.max_hp // 4
        elite.hp = min(elite.max_hp, elite.hp + heal_amount)
        msgs.append(f"The {elite.name} binds its wounds! (+{heal_amount} HP)")
    # Enrage: when HP drops below 50%
    if elite.ability == 'enrage' and not elite.enraged and elite.hp < elite.max_hp * 0.50:
        elite.enraged = True
        msgs.append(f"The {elite.name} enters a blood rage!")


def check_elite_shield(elite, msgs):
    """Return True if the elite's shield absorbed the hit (deal 0 damage).

    Call this BEFORE player attack damage is applied to the elite.
    """
    if elite.ability == 'shield' and elite.shield_active:
        elite.shield_active = False
        msgs.append(f"Your attack glances off the {elite.name}'s barrier!")
        return True
    return False


# ---------------------------------------------------------------------------
# Elite enemy full turn
# ---------------------------------------------------------------------------

def run_elite_turn(elite, player, room, floor_num, msgs):
    """Execute an EliteEnemy's full turn."""
    tick_enemy_status(elite, floor_num, msgs)
    if not elite.alive:
        return  # DoT killed it

    # Legacy stun bool (Stun Scroll)
    if elite.stunned:
        elite.stunned = False
        msgs.append(f"The {elite.name} is stunned and cannot attack!")
        return

    # Status-effects stun
    if elite.status_effects.get('stunned', 0) > 0 and 'stunned' in elite.status_effects:
        msgs.append(f"The {elite.name} is stunned and cannot attack!")
        return

    # Pre-attack ability: Summon
    _run_elite_ability_turn(elite, player, room, floor_num, msgs)

    # Roll and apply attack
    dmg_raw = elite.roll_damage()
    if elite.enraged:
        dmg_raw = int(dmg_raw * 1.5)

    actual, dodged = player.attempt_damage(dmg_raw)
    if dodged:
        msgs.append("You sidestep the blow.")
    else:
        msgs.append(f"The {elite.name} strikes back for {actual} damage!")

    # Post-attack abilities
    _run_elite_after_attack(elite, player, floor_num, msgs, dmg_raw)


# ---------------------------------------------------------------------------
# Final Boss helpers
# ---------------------------------------------------------------------------

def check_final_boss_hp_abilities(fb, msgs):
    """Check Heal and Enrage HP-threshold abilities for the FinalBoss.

    Call this AFTER player deals damage to the final boss.
    """
    if not fb.alive:
        return
    # Heal: when HP drops below 40%, once per fight
    if _has_ability(fb, 'heal') and not fb.ability_used and fb.hp < fb.max_hp * 0.40:
        fb.ability_used = True
        heal_amount = fb.max_hp // 4
        fb.hp = min(fb.max_hp, fb.hp + heal_amount)
        msgs.append(f"{fb._name} mends its form! (+{heal_amount} HP)")
    # Enrage: when HP drops below 50%
    if _has_ability(fb, 'enrage') and not fb.enraged and fb.hp < fb.max_hp * 0.50:
        fb.enraged = True
        msgs.append(f"{fb._name} enters a terrifying rage!")


def check_final_boss_shield(fb, msgs):
    """Return True if the final boss's shield absorbed the hit.

    Call this BEFORE player attack damage is applied to the final boss.
    """
    if _has_ability(fb, 'shield') and fb.shield_active:
        fb.shield_active = False
        msgs.append(f"Your attack glances off {fb._name}'s barrier!")
        return True
    return False


# ---------------------------------------------------------------------------
# Final Boss full turn
# ---------------------------------------------------------------------------

def run_final_boss_turn(fb, player, room, floor_num, msgs):
    """Execute the FinalBoss's full turn."""
    tick_enemy_status(fb, floor_num, msgs)
    if not fb.alive:
        return  # DoT killed it

    if fb.stunned:
        fb.stunned = False
        msgs.append(f"{fb._name} is stunned and cannot attack!")
        return

    # Status-effects stun
    if fb.status_effects.get('stunned', 0) > 0 and 'stunned' in fb.status_effects:
        msgs.append(f"{fb._name} is stunned and cannot attack!")
        return

    # Pre-attack: Summon (at start of turn 3)
    if _has_ability(fb, 'summon') and not fb.ability_used and fb.attack_count == 2:
        fb.ability_used = True
        from enemy import Enemy
        new_enemy = Enemy(floor_num)
        room.enemies.append(new_enemy)
        msgs.append(f"{fb._name} calls forth a companion from the shadows!")

    # Roll and apply attack
    dmg_raw = fb.roll_damage()
    if fb.enraged:
        dmg_raw = int(dmg_raw * 1.5)

    actual, dodged = player.attempt_damage(dmg_raw)
    if dodged:
        msgs.append("You sidestep the blow.")
    else:
        msgs.append(f"{fb._name} strikes you for {actual} damage!")

    # Post-attack abilities
    fb.attack_count += 1
    if _has_ability(fb, 'stun_strike') and not fb.ability_used and fb.attack_count == 3:
        fb.ability_used = True
        player.apply_status('stunned', 1)
        msgs.append(f"{fb._name}'s blow leaves you reeling!")
    if _has_ability(fb, 'poison_strike') and random.random() < 0.40:
        player.apply_status('poisoned', 3)
        # No announcement — status display handles feedback
