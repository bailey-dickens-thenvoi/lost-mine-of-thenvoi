"""Custom tools for the D&D campaign agents."""

from src.tools.dice import (
    DiceRollResult,
    check_hit,
    check_success,
    dice_tool,
    format_roll_result,
    parse_dice_notation,
    roll_ability_check,
    roll_attack,
    roll_damage,
    roll_dice,
    roll_initiative,
    roll_saving_throw,
)
from src.tools.world_state import (
    WorldStateManager,
    get_world_state_manager,
    reset_world_state_manager,
    world_state_tool,
)

__all__ = [
    # Dice rolling
    "DiceRollResult",
    "check_hit",
    "check_success",
    "dice_tool",
    "format_roll_result",
    "parse_dice_notation",
    "roll_ability_check",
    "roll_attack",
    "roll_damage",
    "roll_dice",
    "roll_initiative",
    "roll_saving_throw",
    # World state
    "WorldStateManager",
    "get_world_state_manager",
    "reset_world_state_manager",
    "world_state_tool",
]
