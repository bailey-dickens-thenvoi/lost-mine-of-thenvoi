"""Combat system for D&D 5e.

This module provides simplified D&D 5e combat mechanics:
- Initiative rolling and turn order management
- Attack resolution against AC
- Damage application and death handling
- Combat end condition checking

Designed for hackathon scope - no special abilities, simplified death rules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.game.models import EnemyState
from src.tools.dice import roll_dice, roll_initiative, check_hit
from src.tools.world_state import WorldStateManager

logger = logging.getLogger(__name__)


# Weapon definitions for attack/damage resolution
WEAPONS: dict[str, dict[str, Any]] = {
    "longsword": {"damage": "1d8", "ability": "str", "damage_type": "slashing"},
    "shortsword": {"damage": "1d6", "ability": "dex", "damage_type": "piercing"},
    "shortbow": {"damage": "1d6", "ability": "dex", "damage_type": "piercing"},
    "mace": {"damage": "1d6", "ability": "str", "damage_type": "bludgeoning"},
    "scimitar": {"damage": "1d6", "ability": "dex", "damage_type": "slashing"},
    "dagger": {"damage": "1d4", "ability": "dex", "damage_type": "piercing"},
    "handaxe": {"damage": "1d6", "ability": "str", "damage_type": "slashing"},
    "sacred_flame": {"damage": "1d8", "ability": "wis", "damage_type": "radiant", "save": "dex"},
}

# Enemy stat blocks
ENEMY_STATS: dict[str, dict[str, Any]] = {
    "goblin": {
        "name": "Goblin",
        "hp": 7,
        "ac": 15,
        "attack_bonus": 4,
        "damage": "1d6+2",
        "damage_type": "slashing",
    },
    "bugbear": {
        "name": "Bugbear",
        "hp": 27,
        "ac": 16,
        "attack_bonus": 4,
        "damage": "2d8+2",
        "damage_type": "bludgeoning",
    },
    "wolf": {
        "name": "Wolf",
        "hp": 11,
        "ac": 13,
        "attack_bonus": 4,
        "damage": "2d4+2",
        "damage_type": "piercing",
    },
}


@dataclass
class CombatantInfo:
    """Information about a combatant in the current fight."""

    id: str
    name: str
    initiative: int
    hp: int
    max_hp: int
    ac: int
    is_enemy: bool
    conditions: list[str] = field(default_factory=list)

    @property
    def is_alive(self) -> bool:
        """Check if combatant is alive and able to act."""
        return self.hp > 0 and "dead" not in self.conditions


@dataclass
class CombatStartResult:
    """Result of starting combat."""

    success: bool
    turn_order: list[CombatantInfo]
    announcement: str
    error: str | None = None


@dataclass
class TurnAdvanceResult:
    """Result of advancing to the next turn."""

    combatant_id: str
    combatant_name: str
    round_number: int
    is_new_round: bool
    announcement: str


@dataclass
class AttackResult:
    """Result of an attack action."""

    attacker: str
    target: str
    attack_roll: int
    attack_total: int
    target_ac: int
    hit: bool
    critical: bool
    fumble: bool
    damage: int
    damage_type: str
    target_hp_before: int
    target_hp_after: int
    target_defeated: bool
    narrative: str


@dataclass
class CombatEndResult:
    """Result of combat ending."""

    reason: str  # "enemies_defeated", "party_defeated", "fled", "story"
    narrative: str


def get_combatant_info(
    entity_id: str,
    initiative: int,
    state_manager: WorldStateManager,
    is_enemy: bool = False,
) -> CombatantInfo | None:
    """Build CombatantInfo from world state.

    Args:
        entity_id: The entity identifier
        initiative: Initiative roll result
        state_manager: WorldStateManager instance
        is_enemy: Whether this is an enemy

    Returns:
        CombatantInfo or None if entity not found
    """
    if is_enemy:
        enemy = state_manager.get_enemy(entity_id)
        if enemy:
            return CombatantInfo(
                id=entity_id,
                name=enemy.name,
                initiative=initiative,
                hp=enemy.hp,
                max_hp=enemy.max_hp,
                ac=enemy.ac,
                is_enemy=True,
                conditions=[],
            )
    else:
        char = state_manager.get_character(entity_id)
        if char:
            return CombatantInfo(
                id=entity_id,
                name=char.name,
                initiative=initiative,
                hp=char.hp,
                max_hp=char.max_hp,
                ac=char.ac,
                is_enemy=False,
                conditions=list(char.conditions),
            )

    return None


def start_combat(
    party: list[str],
    enemies: list[str],
    state_manager: WorldStateManager,
    enemy_type: str = "goblin",
) -> CombatStartResult:
    """Initialize combat encounter.

    Args:
        party: List of party member IDs
        enemies: List of enemy IDs to create
        state_manager: WorldStateManager instance
        enemy_type: Type of enemy from ENEMY_STATS

    Returns:
        CombatStartResult with turn order and announcement
    """
    combatants: list[CombatantInfo] = []

    # Get enemy stats template
    enemy_template = ENEMY_STATS.get(enemy_type, ENEMY_STATS["goblin"])

    # Create enemies in world state and roll initiative
    for enemy_id in enemies:
        # Create the enemy in world state
        enemy = EnemyState(
            name=f"{enemy_template['name']} ({enemy_id.split('_')[-1]})",
            hp=enemy_template["hp"],
            max_hp=enemy_template["hp"],
            ac=enemy_template["ac"],
            state="alive",
        )
        state_manager.add_enemy(enemy_id, enemy)

        # Roll initiative (assume DEX +2 for goblins)
        init_result = roll_initiative(enemy_id, dex_modifier=2)
        init_value = init_result["total"]

        info = get_combatant_info(enemy_id, init_value, state_manager, is_enemy=True)
        if info:
            combatants.append(info)
            logger.info(f"Added enemy {enemy_id} with initiative {init_value}")

    # Roll initiative for party members
    for char_id in party:
        char = state_manager.get_character(char_id)
        if not char:
            logger.warning(f"Character {char_id} not found")
            continue

        # Get DEX modifier
        dex_mod = char.stats.get_modifier("dex")
        init_result = roll_initiative(char_id, dex_modifier=dex_mod)
        init_value = init_result["total"]

        info = get_combatant_info(char_id, init_value, state_manager, is_enemy=False)
        if info:
            combatants.append(info)
            logger.info(f"Added character {char_id} with initiative {init_value}")

    if not combatants:
        return CombatStartResult(
            success=False,
            turn_order=[],
            announcement="",
            error="No valid combatants found",
        )

    # Sort by initiative (highest first), using name as tiebreaker
    combatants.sort(key=lambda c: (-c.initiative, c.name))

    # Update combat state
    state_manager.set("combat.active", True)
    state_manager.set("combat.round", 1)
    state_manager.set("combat.turn_order", [c.id for c in combatants])
    state_manager.set("combat.current_turn_index", 0)

    # Store combatant info in combat state
    combatant_data = {
        c.id: {
            "initiative": c.initiative,
            "hp": c.hp,
            "max_hp": c.max_hp,
            "ac": c.ac,
            "is_enemy": c.is_enemy,
            "conditions": c.conditions,
        }
        for c in combatants
    }
    state_manager.set("combat.combatants", combatant_data)

    # Build announcement
    turn_order_text = "\n".join(
        f"  {i+1}. {c.name} (Initiative: {c.initiative})"
        for i, c in enumerate(combatants)
    )

    announcement = f"""=== COMBAT BEGINS ===

TURN ORDER:
{turn_order_text}

Round 1 - {combatants[0].name}'s turn!"""

    return CombatStartResult(
        success=True,
        turn_order=combatants,
        announcement=announcement,
    )


def get_current_combatant(state_manager: WorldStateManager) -> str | None:
    """Get the ID of the combatant whose turn it is.

    Args:
        state_manager: WorldStateManager instance

    Returns:
        Combatant ID or None if not in combat
    """
    if not state_manager.get("combat.active"):
        return None

    turn_order = state_manager.get("combat.turn_order") or []
    current_index = state_manager.get("combat.current_turn_index") or 0

    if not turn_order:
        return None

    return turn_order[current_index % len(turn_order)]


def advance_turn(state_manager: WorldStateManager) -> TurnAdvanceResult | None:
    """Advance to the next combatant's turn.

    Skips dead/unconscious combatants. Handles round rollover.

    Args:
        state_manager: WorldStateManager instance

    Returns:
        TurnAdvanceResult or None if not in combat
    """
    if not state_manager.get("combat.active"):
        return None

    turn_order = state_manager.get("combat.turn_order") or []
    if not turn_order:
        return None

    current_index = state_manager.get("combat.current_turn_index") or 0
    current_round = state_manager.get("combat.round") or 1
    combatants = state_manager.get("combat.combatants") or {}

    # Find next living combatant
    attempts = 0
    next_index = (current_index + 1) % len(turn_order)
    is_new_round = False

    while attempts < len(turn_order):
        combatant_id = turn_order[next_index]

        # Check for round rollover BEFORE processing this combatant
        if next_index == 0 and (current_index != 0 or attempts > 0):
            current_round += 1
            is_new_round = True

        # Check if combatant is alive - ALWAYS check actual entity state
        is_alive = False
        enemy = state_manager.get_enemy(combatant_id)
        if enemy:
            is_alive = enemy.is_alive
        else:
            char = state_manager.get_character(combatant_id)
            if char:
                is_alive = char.is_alive

        if is_alive:
            break

        next_index = (next_index + 1) % len(turn_order)
        attempts += 1

    if attempts >= len(turn_order):
        # Everyone is dead - this shouldn't happen normally
        return None

    # Update state
    state_manager.set("combat.current_turn_index", next_index)
    state_manager.set("combat.round", current_round)

    # Get combatant name
    combatant_id = turn_order[next_index]
    combatant_name = combatant_id

    enemy = state_manager.get_enemy(combatant_id)
    if enemy:
        combatant_name = enemy.name
    else:
        char = state_manager.get_character(combatant_id)
        if char:
            combatant_name = char.name

    # Build announcement
    if is_new_round:
        announcement = f"=== ROUND {current_round} ===\n\n{combatant_name}'s turn!"
    else:
        announcement = f"{combatant_name}'s turn!"

    return TurnAdvanceResult(
        combatant_id=combatant_id,
        combatant_name=combatant_name,
        round_number=current_round,
        is_new_round=is_new_round,
        announcement=announcement,
    )


def get_attack_bonus(
    attacker_id: str,
    weapon: str,
    state_manager: WorldStateManager,
) -> int:
    """Calculate attack bonus for an attacker.

    Args:
        attacker_id: The attacker's ID
        weapon: Weapon name
        state_manager: WorldStateManager instance

    Returns:
        Attack bonus (ability mod + proficiency)
    """
    # Check if attacker is an enemy (use predefined attack bonus)
    enemy = state_manager.get_enemy(attacker_id)
    if enemy:
        # Look up enemy type attack bonus
        for enemy_type, stats in ENEMY_STATS.items():
            if enemy_type in attacker_id.lower():
                return stats.get("attack_bonus", 4)
        return 4  # Default enemy attack bonus

    # Character - calculate from stats
    char = state_manager.get_character(attacker_id)
    if not char:
        return 0

    weapon_info = WEAPONS.get(weapon, {"ability": "str"})
    ability = weapon_info["ability"]
    ability_mod = char.stats.get_modifier(ability)
    proficiency = char.proficiency_bonus

    return ability_mod + proficiency


def get_damage_dice(
    attacker_id: str,
    weapon: str,
    state_manager: WorldStateManager,
) -> tuple[str, str]:
    """Get damage dice and type for an attack.

    Args:
        attacker_id: The attacker's ID
        weapon: Weapon name
        state_manager: WorldStateManager instance

    Returns:
        Tuple of (damage_notation, damage_type)
    """
    # Check if attacker is an enemy
    enemy = state_manager.get_enemy(attacker_id)
    if enemy:
        for enemy_type, stats in ENEMY_STATS.items():
            if enemy_type in attacker_id.lower():
                return stats["damage"], stats["damage_type"]
        return "1d6+2", "slashing"  # Default

    # Character - get weapon damage + ability mod
    char = state_manager.get_character(attacker_id)
    if not char:
        return "1d6", "slashing"

    weapon_info = WEAPONS.get(weapon, {"damage": "1d6", "ability": "str", "damage_type": "slashing"})
    ability = weapon_info["ability"]
    ability_mod = char.stats.get_modifier(ability)

    base_dice = weapon_info["damage"]
    if ability_mod >= 0:
        damage_notation = f"{base_dice}+{ability_mod}"
    else:
        damage_notation = f"{base_dice}{ability_mod}"

    return damage_notation, weapon_info["damage_type"]


def resolve_attack(
    attacker_id: str,
    target_id: str,
    weapon: str,
    state_manager: WorldStateManager,
    advantage: bool = False,
    disadvantage: bool = False,
) -> AttackResult:
    """Resolve an attack action.

    Args:
        attacker_id: The attacker's ID
        target_id: The target's ID
        weapon: Weapon used
        state_manager: WorldStateManager instance
        advantage: Roll with advantage
        disadvantage: Roll with disadvantage

    Returns:
        AttackResult with full resolution details
    """
    # Get attacker name
    attacker_name = attacker_id
    attacker_char = state_manager.get_character(attacker_id)
    attacker_enemy = state_manager.get_enemy(attacker_id)
    if attacker_char:
        attacker_name = attacker_char.name
    elif attacker_enemy:
        attacker_name = attacker_enemy.name

    # Get target name and AC
    target_name = target_id
    target_ac = 10
    target_hp_before = 0

    target_char = state_manager.get_character(target_id)
    target_enemy = state_manager.get_enemy(target_id)

    if target_char:
        target_name = target_char.name
        target_ac = target_char.ac
        target_hp_before = target_char.hp
    elif target_enemy:
        target_name = target_enemy.name
        target_ac = target_enemy.ac
        target_hp_before = target_enemy.hp

    # Roll attack
    attack_bonus = get_attack_bonus(attacker_id, weapon, state_manager)
    attack_notation = f"1d20+{attack_bonus}" if attack_bonus >= 0 else f"1d20{attack_bonus}"

    attack_result = roll_dice(
        notation=attack_notation,
        purpose="Attack Roll",
        roller=attacker_name,
        advantage=advantage,
        disadvantage=disadvantage,
    )

    attack_roll = attack_result["rolls"][0] if not (advantage or disadvantage) else attack_result["kept_roll"]
    attack_total = attack_result["total"]
    critical = attack_result["critical"]
    fumble = attack_result["fumble"]

    # Check hit
    hit = check_hit(attack_total, target_ac, is_critical=critical)

    # Initialize damage values
    damage = 0
    damage_type = "slashing"
    target_hp_after = target_hp_before
    target_defeated = False

    # Roll damage if hit
    if hit:
        damage_notation, damage_type = get_damage_dice(attacker_id, weapon, state_manager)

        # Critical hit doubles dice
        damage_result = roll_dice(
            notation=damage_notation,
            purpose=f"{damage_type.capitalize()} Damage",
            roller=attacker_name,
        )

        damage = damage_result["total"]

        # Double damage on critical
        if critical:
            # Re-roll dice portion only
            damage_dice_result = roll_dice(
                notation=damage_notation.split("+")[0].split("-")[0],
                purpose="Critical Bonus",
                roller=attacker_name,
            )
            damage += damage_dice_result["total"]

        # Apply damage
        target_hp_after = state_manager.update_hp(target_id, -damage)
        target_defeated = target_hp_after == 0

    # Build narrative
    if fumble:
        narrative = f"{attacker_name} swings wildly and misses! (Fumble: {attack_roll})"
    elif critical:
        if target_defeated:
            narrative = f"CRITICAL HIT! {attacker_name} strikes {target_name} for {damage} {damage_type} damage! {target_name} falls!"
        else:
            narrative = f"CRITICAL HIT! {attacker_name} strikes {target_name} for {damage} {damage_type} damage! ({target_hp_after}/{target_hp_before} HP)"
    elif hit:
        if target_defeated:
            narrative = f"{attacker_name} hits {target_name} ({attack_total} vs AC {target_ac}) for {damage} {damage_type} damage! {target_name} goes down!"
        else:
            narrative = f"{attacker_name} hits {target_name} ({attack_total} vs AC {target_ac}) for {damage} {damage_type} damage. ({target_hp_after} HP remaining)"
    else:
        narrative = f"{attacker_name} attacks {target_name} but misses ({attack_total} vs AC {target_ac})."

    return AttackResult(
        attacker=attacker_id,
        target=target_id,
        attack_roll=attack_roll,
        attack_total=attack_total,
        target_ac=target_ac,
        hit=hit,
        critical=critical,
        fumble=fumble,
        damage=damage,
        damage_type=damage_type,
        target_hp_before=target_hp_before,
        target_hp_after=target_hp_after,
        target_defeated=target_defeated,
        narrative=narrative,
    )


def check_combat_end(state_manager: WorldStateManager) -> CombatEndResult | None:
    """Check if combat should end.

    Args:
        state_manager: WorldStateManager instance

    Returns:
        CombatEndResult if combat should end, None otherwise
    """
    if not state_manager.get("combat.active"):
        return None

    # Check if all enemies are dead
    enemies = state_manager.state.enemies
    all_enemies_dead = all(not e.is_alive for e in enemies.values()) if enemies else True

    if all_enemies_dead and enemies:
        return CombatEndResult(
            reason="enemies_defeated",
            narrative="All enemies have been defeated! Victory!",
        )

    # Check if all party members are down
    characters = state_manager.state.characters
    all_party_down = all(not c.is_alive for c in characters.values()) if characters else False

    if all_party_down:
        return CombatEndResult(
            reason="party_defeated",
            narrative="The party has fallen...",
        )

    return None


def end_combat(state_manager: WorldStateManager, reason: str = "normal") -> str:
    """End combat and clean up state.

    Args:
        state_manager: WorldStateManager instance
        reason: Reason for ending combat

    Returns:
        Narrative text for the transition
    """
    # Clear combat state
    state_manager.set("combat.active", False)
    state_manager.set("combat.round", 0)
    state_manager.set("combat.turn_order", [])
    state_manager.set("combat.current_turn_index", 0)
    state_manager.set("combat.combatants", {})

    # Clear dead enemies from state
    dead_enemies = [
        eid for eid, enemy in state_manager.state.enemies.items()
        if not enemy.is_alive
    ]
    for eid in dead_enemies:
        state_manager.remove_enemy(eid)

    if reason == "enemies_defeated":
        return "=== COMBAT ENDS ===\n\nThe enemies lie defeated. You may search the area or continue on."
    elif reason == "party_defeated":
        return "=== COMBAT ENDS ===\n\nDarkness closes in..."
    elif reason == "fled":
        return "=== COMBAT ENDS ===\n\nYou flee from the battle."
    else:
        return "=== COMBAT ENDS ==="


def get_combat_status(state_manager: WorldStateManager) -> str:
    """Get a formatted status of the current combat.

    Args:
        state_manager: WorldStateManager instance

    Returns:
        Formatted combat status string
    """
    if not state_manager.get("combat.active"):
        return "Not in combat."

    round_num = state_manager.get("combat.round") or 1
    current_id = get_current_combatant(state_manager)

    lines = [f"=== COMBAT STATUS (Round {round_num}) ===\n"]

    # Party status
    lines.append("PARTY:")
    for char_id, char in state_manager.state.characters.items():
        status = "ALIVE" if char.is_alive else "DOWN"
        marker = ">>>" if char_id == current_id else "   "
        lines.append(f"{marker} {char.name}: {char.hp}/{char.max_hp} HP [{status}]")

    # Enemy status
    lines.append("\nENEMIES:")
    for enemy_id, enemy in state_manager.state.enemies.items():
        if enemy.is_alive:
            status = "ALIVE"
        else:
            status = "DEAD"
        marker = ">>>" if enemy_id == current_id else "   "
        lines.append(f"{marker} {enemy.name}: {enemy.hp}/{enemy.max_hp} HP [{status}]")

    if not state_manager.state.enemies:
        lines.append("   (no enemies)")

    return "\n".join(lines)
