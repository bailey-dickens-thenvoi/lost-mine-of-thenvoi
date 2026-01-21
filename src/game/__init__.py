"""Game mechanics and systems for D&D 5e."""

from src.game.combat import (
    ENEMY_STATS,
    WEAPONS,
    AttackResult,
    CombatantInfo,
    CombatEndResult,
    CombatStartResult,
    TurnAdvanceResult,
    advance_turn,
    check_combat_end,
    end_combat,
    get_combat_status,
    get_current_combatant,
    resolve_attack,
    start_combat,
)
from src.game.models import (
    CharacterState,
    CharacterStats,
    CombatState,
    EnemyState,
    NarrativeProgress,
    NPCState,
    WorldState,
)

__all__ = [
    # Combat
    "ENEMY_STATS",
    "WEAPONS",
    "AttackResult",
    "CombatantInfo",
    "CombatEndResult",
    "CombatStartResult",
    "TurnAdvanceResult",
    "advance_turn",
    "check_combat_end",
    "end_combat",
    "get_combat_status",
    "get_current_combatant",
    "resolve_attack",
    "start_combat",
    # Models
    "CharacterState",
    "CharacterStats",
    "CombatState",
    "EnemyState",
    "NarrativeProgress",
    "NPCState",
    "WorldState",
]
