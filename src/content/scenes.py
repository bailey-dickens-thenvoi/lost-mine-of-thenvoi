"""Scene management utilities for the D&D campaign.

This module provides utilities for working with scene definitions:
- Scene loading and validation
- Trigger resolution
- DM context generation
- Scene transition management
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.tools.world_state import WorldStateManager


class SceneManager:
    """Manages scene navigation and context for the DM.

    The SceneManager provides:
    - Access to scene definitions
    - Trigger resolution with skill checks
    - DM context generation with current state
    - Scene transition handling
    """

    def __init__(
        self,
        scenes: dict[str, dict[str, Any]],
        state_manager: "WorldStateManager",
    ):
        """Initialize the SceneManager.

        Args:
            scenes: Dictionary of scene definitions
            state_manager: WorldStateManager for state access
        """
        self.scenes = scenes
        self.state_manager = state_manager

    def get_current_scene(self) -> dict[str, Any] | None:
        """Get the current scene definition.

        Returns:
            Scene definition or None if not found
        """
        scene_id = self.state_manager.get("current_scene")
        if scene_id:
            return self.scenes.get(scene_id)
        return None

    def get_current_scene_id(self) -> str:
        """Get the current scene ID.

        Returns:
            Scene ID string
        """
        return self.state_manager.get("current_scene") or "intro"

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        """Get a scene by ID.

        Args:
            scene_id: The scene identifier

        Returns:
            Scene definition or None
        """
        return self.scenes.get(scene_id)

    def transition_to_scene(self, scene_id: str) -> bool:
        """Transition to a new scene.

        Args:
            scene_id: The target scene ID

        Returns:
            True if transition succeeded, False if scene not found
        """
        if scene_id not in self.scenes:
            return False

        self.state_manager.set("current_scene", scene_id)
        return True

    def get_available_triggers(self) -> dict[str, dict[str, Any]]:
        """Get available triggers for the current scene.

        Returns:
            Dictionary of trigger definitions
        """
        scene = self.get_current_scene()
        if scene:
            return scene.get("triggers", {})
        return {}

    def get_trigger(self, trigger_name: str) -> dict[str, Any] | None:
        """Get a specific trigger from the current scene.

        Args:
            trigger_name: Name of the trigger

        Returns:
            Trigger definition or None
        """
        triggers = self.get_available_triggers()
        return triggers.get(trigger_name)

    def is_combat_scene(self) -> bool:
        """Check if the current scene is a combat encounter.

        Returns:
            True if current scene has combat
        """
        scene = self.get_current_scene()
        if scene:
            return scene.get("combat", False)
        return False

    def get_scene_enemies(self) -> list[str]:
        """Get enemy IDs for the current scene.

        Returns:
            List of enemy IDs
        """
        scene = self.get_current_scene()
        if scene:
            return scene.get("enemies", [])
        return []

    def get_dm_context(self, include_dm_notes: bool = True) -> str:
        """Generate DM context for the current scene.

        Args:
            include_dm_notes: Whether to include private DM notes

        Returns:
            Formatted context string for the DM
        """
        scene = self.get_current_scene()
        if not scene:
            return "No current scene found."

        lines = [
            f"## Current Scene: {scene.get('name', 'Unknown')}",
            f"Chapter: {scene.get('chapter', 1)}",
            "",
        ]

        # Scene description
        if scene.get("description"):
            lines.append("### Read to Players")
            lines.append(scene["description"])
            lines.append("")

        # Available triggers
        triggers = scene.get("triggers", {})
        if triggers:
            lines.append("### Available Skill Checks")
            for name, trigger in triggers.items():
                skill = trigger.get("skill", "any").upper()
                dc = trigger.get("dc", 10)
                lines.append(f"- **{name}**: {skill} DC {dc}")
            lines.append("")

        # Combat info
        if scene.get("combat"):
            lines.append("### Combat Encounter")
            enemies = scene.get("enemies", [])
            lines.append(f"Enemies: {', '.join(enemies) if enemies else 'None'}")
            if scene.get("goblin_tactics"):
                lines.append(f"Tactics: {scene['goblin_tactics']}")
            lines.append("")

        # Current state
        lines.append("### Current State")
        lines.append(self._format_state_summary())
        lines.append("")

        # DM notes
        if include_dm_notes and scene.get("dm_notes"):
            lines.append("### DM Notes (private)")
            lines.append(scene["dm_notes"])
            lines.append("")

        return "\n".join(lines)

    def _format_state_summary(self) -> str:
        """Format a summary of the current game state.

        Returns:
            Formatted state summary
        """
        lines = []

        # Party status
        party_status = self.state_manager.get_party_status()
        if party_status:
            for char_id, info in party_status.items():
                status = "alive" if info["is_alive"] else "unconscious"
                lines.append(f"- {info['name']}: {info['hp']}/{info['max_hp']} HP ({status})")

        # Combat status
        combat_active = self.state_manager.get("combat.active")
        if combat_active:
            combat_round = self.state_manager.get("combat.round") or 1
            lines.append(f"\nCombat: Round {combat_round}")

            # Living enemies
            enemies = self.state_manager.get_all_living_enemies()
            if enemies:
                lines.append(f"Living Enemies: {', '.join(enemies)}")

        # Progress flags
        progress = self.state_manager.state.narrative_progress
        flags = []
        if progress.ambush_triggered:
            flags.append("ambush_triggered")
        if progress.goblins_defeated:
            flags.append("goblins_defeated")
        if progress.goblin_trail_found:
            flags.append("trail_found")
        if progress.sildar_rescued:
            flags.append("sildar_rescued")

        if flags:
            lines.append(f"\nProgress: {', '.join(flags)}")

        return "\n".join(lines) if lines else "No state data"

    def check_scene_completion(self) -> tuple[bool, str | None]:
        """Check if the current scene is complete and should transition.

        Returns:
            Tuple of (is_complete, next_scene_id)
        """
        scene = self.get_current_scene()
        if not scene:
            return False, None

        # Check for combat victory
        if scene.get("combat"):
            enemies = self.state_manager.get_all_living_enemies()
            if not enemies:  # All enemies dead
                self.state_manager.set_progress_flag("goblins_defeated")
                return True, scene.get("victory_scene")

        # Check for specific progress flags
        progress_flags = scene.get("progress_flags", [])
        for flag in progress_flags:
            if not self.state_manager.get_progress_flag(flag):
                # Set the flag if we're in this scene
                self.state_manager.set_progress_flag(flag)

        return False, None


def create_trigger_result(
    trigger: dict[str, Any],
    roll_total: int,
) -> dict[str, Any]:
    """Create a result from a trigger check.

    Args:
        trigger: Trigger definition
        roll_total: The total of the skill check roll

    Returns:
        Result dictionary with success status and text
    """
    dc = trigger.get("dc", 10)
    success = roll_total >= dc

    if success:
        text = trigger.get("success_text", "Success!")
    else:
        text = trigger.get("fail_text", "You fail to find anything.")

    return {
        "success": success,
        "dc": dc,
        "roll": roll_total,
        "text": text,
        "skill": trigger.get("skill", ""),
    }


def format_trigger_for_dm(trigger_name: str, trigger: dict[str, Any]) -> str:
    """Format a trigger for DM display.

    Args:
        trigger_name: Name of the trigger
        trigger: Trigger definition

    Returns:
        Formatted trigger string
    """
    skill = trigger.get("skill", "any")
    dc = trigger.get("dc", 10)
    return f"{trigger_name}: {skill.upper()} DC {dc}"


def get_skill_modifier(char_stats: dict[str, int], skill: str) -> int:
    """Get the modifier for a skill check.

    This is a simplified mapping - in full D&D, skill proficiency
    and expertise would also apply.

    Args:
        char_stats: Character ability scores
        skill: Skill name

    Returns:
        Ability modifier for the skill
    """
    # Skill to ability mapping (simplified)
    SKILL_ABILITIES = {
        "athletics": "strength",
        "acrobatics": "dexterity",
        "sleight_of_hand": "dexterity",
        "stealth": "dexterity",
        "arcana": "intelligence",
        "history": "intelligence",
        "investigation": "intelligence",
        "nature": "intelligence",
        "religion": "intelligence",
        "animal_handling": "wisdom",
        "insight": "wisdom",
        "medicine": "wisdom",
        "perception": "wisdom",
        "survival": "wisdom",
        "deception": "charisma",
        "intimidation": "charisma",
        "performance": "charisma",
        "persuasion": "charisma",
    }

    ability = SKILL_ABILITIES.get(skill.lower(), "wisdom")

    # Get ability score
    ability_short = {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "wis",
        "charisma": "cha",
    }.get(ability, ability[:3])

    score = char_stats.get(ability_short, 10)
    return (score - 10) // 2
