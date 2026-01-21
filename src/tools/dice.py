"""Dice rolling system for D&D 5e.

This module provides dice rolling functionality with support for:
- Standard D&D notation (1d20, 2d6+3, etc.)
- Advantage and disadvantage
- Critical hit and fumble detection
- Formatted output for chat display

The DM agent uses this tool to roll all dice on behalf of players,
as human players cannot use tools on the Thenvoi platform.
"""

import logging
import random
import re
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)

# Type alias for random function (allows mocking in tests)
RandomFunc = Callable[[int, int], int]


@dataclass
class DiceRollResult:
    """Result of a dice roll."""

    rolls: list[int]  # Individual die results
    modifier: int  # Applied modifier
    total: int  # Final result
    purpose: str  # What the roll was for
    roller: str  # Who made the roll
    advantage_used: bool  # Was advantage applied
    disadvantage_used: bool  # Was disadvantage applied
    critical: bool  # Natural 20 on d20
    fumble: bool  # Natural 1 on d20
    notation: str  # Original dice notation
    kept_roll: int | None = None  # Which roll was kept (for advantage/disadvantage)

    def to_dict(self) -> dict:
        """Convert to dictionary for tool output."""
        return {
            "rolls": self.rolls,
            "modifier": self.modifier,
            "total": self.total,
            "purpose": self.purpose,
            "roller": self.roller,
            "advantage_used": self.advantage_used,
            "disadvantage_used": self.disadvantage_used,
            "critical": self.critical,
            "fumble": self.fumble,
            "notation": self.notation,
            "kept_roll": self.kept_roll,
        }


def parse_dice_notation(notation: str) -> tuple[int, int, int]:
    """Parse dice notation into (num_dice, die_size, modifier).

    Args:
        notation: Standard D&D dice notation like "1d20", "2d6+3", "1d8-1"

    Returns:
        Tuple of (number_of_dice, die_size, modifier)

    Raises:
        ValueError: If notation is invalid

    Examples:
        >>> parse_dice_notation("1d20")
        (1, 20, 0)
        >>> parse_dice_notation("2d6+3")
        (2, 6, 3)
        >>> parse_dice_notation("1d8-1")
        (1, 8, -1)
    """
    # Pattern: NdM or NdM+X or NdM-X
    pattern = r"^(\d+)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, notation.lower().strip())

    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num_dice < 1:
        raise ValueError(f"Number of dice must be at least 1: {notation}")
    if die_size < 1:
        raise ValueError(f"Die size must be at least 1: {notation}")

    return num_dice, die_size, modifier


def roll_single_die(die_size: int, rand_func: RandomFunc | None = None) -> int:
    """Roll a single die.

    Args:
        die_size: Number of sides on the die
        rand_func: Optional custom random function for testing

    Returns:
        The roll result (1 to die_size inclusive)
    """
    if rand_func:
        return rand_func(1, die_size)
    return random.randint(1, die_size)


def roll_dice(
    notation: str,
    purpose: str,
    roller: str,
    advantage: bool = False,
    disadvantage: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll dice using D&D notation.

    This is the main function for all dice rolling. The DM uses this
    to roll dice on behalf of all players and NPCs.

    Args:
        notation: Dice notation (e.g., "1d20+5", "2d6+3")
        purpose: What the roll is for (e.g., "attack roll", "damage")
        roller: Who is making the roll (e.g., "human_player", "goblin_1")
        advantage: Roll d20 twice, take higher (only applies to d20 rolls)
        disadvantage: Roll d20 twice, take lower (only applies to d20 rolls)
        rand_func: Optional custom random function for testing

    Returns:
        Dictionary with roll results including:
        - rolls: list of individual die results
        - modifier: the modifier applied
        - total: final result
        - purpose: what the roll was for
        - roller: who rolled
        - critical: True if natural 20 on d20
        - fumble: True if natural 1 on d20
        - advantage_used/disadvantage_used: whether these were applied

    Examples:
        >>> roll_dice("1d20+5", "attack roll", "human_player")
        {"rolls": [15], "modifier": 5, "total": 20, ...}

        >>> roll_dice("2d6+3", "longsword damage", "fighter")
        {"rolls": [4, 6], "modifier": 3, "total": 13, ...}
    """
    num_dice, die_size, modifier = parse_dice_notation(notation)

    # Handle advantage/disadvantage for d20 rolls
    is_d20 = die_size == 20 and num_dice == 1
    actual_advantage = advantage and is_d20 and not disadvantage
    actual_disadvantage = disadvantage and is_d20 and not advantage

    # Roll the dice
    if actual_advantage or actual_disadvantage:
        # Roll twice for advantage/disadvantage
        roll1 = roll_single_die(die_size, rand_func)
        roll2 = roll_single_die(die_size, rand_func)
        rolls = [roll1, roll2]

        if actual_advantage:
            kept_roll = max(roll1, roll2)
        else:
            kept_roll = min(roll1, roll2)

        base_total = kept_roll
    else:
        # Normal roll
        rolls = [roll_single_die(die_size, rand_func) for _ in range(num_dice)]
        kept_roll = None
        base_total = sum(rolls)

    total = base_total + modifier

    # Detect criticals and fumbles (only for d20 rolls)
    critical = False
    fumble = False
    if is_d20:
        check_roll = kept_roll if kept_roll is not None else rolls[0]
        critical = check_roll == 20
        fumble = check_roll == 1

    result = DiceRollResult(
        rolls=rolls,
        modifier=modifier,
        total=total,
        purpose=purpose,
        roller=roller,
        advantage_used=actual_advantage,
        disadvantage_used=actual_disadvantage,
        critical=critical,
        fumble=fumble,
        notation=notation,
        kept_roll=kept_roll,
    )

    # Log the roll
    logger.info(f"Roll: {format_roll_result(result)}")

    return result.to_dict()


def format_roll_result(result: DiceRollResult | dict) -> str:
    """Format roll result for display in chat.

    Args:
        result: DiceRollResult object or dictionary from roll_dice()

    Returns:
        Formatted string for chat display

    Examples:
        "Attack Roll for Vex: [15] + 5 = 20"
        "Damage Roll for Thokk: [4, 6] + 3 = 13"
        "Stealth Check (advantage) for Vex: [8, 17] + 4 = 21 (took 17)"
        "Attack Roll for Vex: [20] + 5 = 25 CRITICAL HIT!"
    """
    if isinstance(result, dict):
        rolls = result["rolls"]
        modifier = result["modifier"]
        total = result["total"]
        purpose = result["purpose"]
        roller = result["roller"]
        advantage = result.get("advantage_used", False)
        disadvantage = result.get("disadvantage_used", False)
        critical = result.get("critical", False)
        fumble = result.get("fumble", False)
        kept_roll = result.get("kept_roll")
    else:
        rolls = result.rolls
        modifier = result.modifier
        total = result.total
        purpose = result.purpose
        roller = result.roller
        advantage = result.advantage_used
        disadvantage = result.disadvantage_used
        critical = result.critical
        fumble = result.fumble
        kept_roll = result.kept_roll

    # Build the roll string
    rolls_str = "[" + ", ".join(str(r) for r in rolls) + "]"

    # Build modifier string
    if modifier > 0:
        mod_str = f" + {modifier}"
    elif modifier < 0:
        mod_str = f" - {abs(modifier)}"
    else:
        mod_str = ""

    # Build advantage/disadvantage indicator
    if advantage:
        adv_str = " (advantage)"
    elif disadvantage:
        adv_str = " (disadvantage)"
    else:
        adv_str = ""

    # Build kept roll indicator
    if kept_roll is not None:
        kept_str = f" (took {kept_roll})"
    else:
        kept_str = ""

    # Build critical/fumble indicator
    if critical:
        crit_str = " CRITICAL HIT!"
    elif fumble:
        crit_str = " FUMBLE!"
    else:
        crit_str = ""

    return f"{purpose}{adv_str} for {roller}: {rolls_str}{mod_str} = {total}{kept_str}{crit_str}"


def check_hit(attack_total: int, target_ac: int, is_critical: bool = False) -> bool:
    """Check if an attack hits the target.

    Args:
        attack_total: The total attack roll result
        target_ac: The target's armor class
        is_critical: Whether the roll was a natural 20

    Returns:
        True if the attack hits, False otherwise

    Note:
        A critical hit (natural 20) always hits regardless of AC.
    """
    if is_critical:
        return True
    return attack_total >= target_ac


def check_success(roll_total: int, dc: int, is_natural_20: bool = False, is_natural_1: bool = False) -> bool:
    """Check if a saving throw or ability check succeeds.

    Args:
        roll_total: The total roll result
        dc: The difficulty class to beat
        is_natural_20: Whether the roll was a natural 20
        is_natural_1: Whether the roll was a natural 1

    Returns:
        True if the check succeeds, False otherwise

    Note:
        For saving throws, natural 20 always succeeds and natural 1 always fails.
        For ability checks, this is optional per DM ruling.
    """
    # Natural 20 always succeeds on saves
    if is_natural_20:
        return True
    # Natural 1 always fails on saves
    if is_natural_1:
        return False
    return roll_total >= dc


def roll_initiative(
    roller: str,
    dex_modifier: int,
    advantage: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll initiative for a combatant.

    Args:
        roller: Who is rolling initiative
        dex_modifier: The character's DEX modifier
        advantage: Whether to roll with advantage

    Returns:
        Roll result dictionary
    """
    notation = f"1d20+{dex_modifier}" if dex_modifier >= 0 else f"1d20{dex_modifier}"
    return roll_dice(notation, "Initiative", roller, advantage=advantage, rand_func=rand_func)


def roll_attack(
    roller: str,
    attack_bonus: int,
    advantage: bool = False,
    disadvantage: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll an attack.

    Args:
        roller: Who is attacking
        attack_bonus: The total attack bonus
        advantage: Roll with advantage
        disadvantage: Roll with disadvantage

    Returns:
        Roll result dictionary
    """
    notation = f"1d20+{attack_bonus}" if attack_bonus >= 0 else f"1d20{attack_bonus}"
    return roll_dice(
        notation, "Attack Roll", roller, advantage=advantage, disadvantage=disadvantage, rand_func=rand_func
    )


def roll_damage(
    roller: str,
    damage_dice: str,
    damage_type: str = "damage",
    is_critical: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll damage.

    Args:
        roller: Who is dealing damage
        damage_dice: Damage notation (e.g., "1d8+3")
        damage_type: Type of damage (e.g., "slashing", "fire")
        is_critical: If True, doubles the dice (not modifier)

    Returns:
        Roll result dictionary
    """
    num_dice, die_size, modifier = parse_dice_notation(damage_dice)

    # Critical hits double the number of dice
    if is_critical:
        num_dice *= 2
        notation = f"{num_dice}d{die_size}+{modifier}" if modifier >= 0 else f"{num_dice}d{die_size}{modifier}"
    else:
        notation = damage_dice

    purpose = f"{damage_type.capitalize()} Damage" if damage_type != "damage" else "Damage"
    return roll_dice(notation, purpose, roller, rand_func=rand_func)


def roll_ability_check(
    roller: str,
    ability: str,
    modifier: int,
    advantage: bool = False,
    disadvantage: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll an ability check.

    Args:
        roller: Who is making the check
        ability: The ability being checked (e.g., "Perception", "Stealth")
        modifier: The total modifier for the check
        advantage: Roll with advantage
        disadvantage: Roll with disadvantage

    Returns:
        Roll result dictionary
    """
    notation = f"1d20+{modifier}" if modifier >= 0 else f"1d20{modifier}"
    return roll_dice(
        notation, f"{ability} Check", roller, advantage=advantage, disadvantage=disadvantage, rand_func=rand_func
    )


def roll_saving_throw(
    roller: str,
    save_type: str,
    modifier: int,
    advantage: bool = False,
    disadvantage: bool = False,
    rand_func: RandomFunc | None = None,
) -> dict:
    """Roll a saving throw.

    Args:
        roller: Who is making the save
        save_type: The type of save (e.g., "DEX", "WIS")
        modifier: The total modifier for the save
        advantage: Roll with advantage
        disadvantage: Roll with disadvantage

    Returns:
        Roll result dictionary
    """
    notation = f"1d20+{modifier}" if modifier >= 0 else f"1d20{modifier}"
    return roll_dice(
        notation, f"{save_type} Save", roller, advantage=advantage, disadvantage=disadvantage, rand_func=rand_func
    )


# Tool function for agent integration
def dice_tool(
    notation: str,
    purpose: str,
    roller: str,
    advantage: bool = False,
    disadvantage: bool = False,
) -> str:
    """Tool function for rolling dice in agent context.

    This wraps roll_dice() and returns a formatted string suitable
    for chat display.

    Args:
        notation: Dice notation (e.g., "1d20+5", "2d6+3")
        purpose: What the roll is for
        roller: Who is rolling
        advantage: Roll with advantage (d20 only)
        disadvantage: Roll with disadvantage (d20 only)

    Returns:
        Formatted string describing the roll result
    """
    try:
        result = roll_dice(notation, purpose, roller, advantage, disadvantage)
        return format_roll_result(result)
    except ValueError as e:
        return f"Error rolling dice: {e}"
