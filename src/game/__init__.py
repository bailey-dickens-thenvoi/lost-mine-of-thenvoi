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
from src.game.npcs import (
    format_npc_prompt,
    format_npc_prompt_custom,
    get_alive_npcs,
    get_npc,
    get_npc_names,
    get_npcs_at_location,
    load_npc_data,
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
    # NPCs
    "format_npc_prompt",
    "format_npc_prompt_custom",
    "get_alive_npcs",
    "get_npc",
    "get_npc_names",
    "get_npcs_at_location",
    "load_npc_data",
]
