"""Campaign content for Lost Mines of Phandelver.

This package contains:
- chapter1: Scene definitions and content for Chapter 1 (Goblin Arrows)
- scenes: Scene management utilities
"""

from src.content.chapter1 import (
    SCENES,
    CHAPTER1_ENEMIES,
    get_scene,
    get_scene_description,
    get_scene_dm_notes,
    get_scene_triggers,
    get_enemy_stats,
    format_scene_context,
)
from src.content.scenes import (
    SceneManager,
    create_trigger_result,
    format_trigger_for_dm,
    get_skill_modifier,
)

__all__ = [
    "SCENES",
    "CHAPTER1_ENEMIES",
    "get_scene",
    "get_scene_description",
    "get_scene_dm_notes",
    "get_scene_triggers",
    "get_enemy_stats",
    "format_scene_context",
    "SceneManager",
    "create_trigger_result",
    "format_trigger_for_dm",
    "get_skill_modifier",
]
