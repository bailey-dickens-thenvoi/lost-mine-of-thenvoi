"""World State Manager for persistent game state.

This module provides the WorldStateManager class for managing game state
and a tool wrapper for use in agent tool calls.
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.game.models import (
    CharacterState,
    CharacterStats,
    EnemyState,
    NarrativeProgress,
    NPCState,
    WorldState,
)

logger = logging.getLogger(__name__)


class WorldStateManager:
    """Manages persistent world state for the D&D campaign.

    The WorldStateManager provides:
    - Loading/saving state to JSON file
    - Dot-notation path access (e.g., "combat.active")
    - HP updates with death handling
    - Character and enemy lookups

    Example:
        >>> manager = WorldStateManager("data/world_state.json")
        >>> manager.set("current_scene", "goblin_ambush")
        >>> manager.get("current_scene")
        'goblin_ambush'
        >>> manager.save()
    """

    def __init__(self, state_file: str = "data/world_state.json", auto_save: bool = True):
        """Initialize the WorldStateManager.

        Args:
            state_file: Path to the JSON state file
            auto_save: If True, automatically save after state changes
        """
        self.state_file = Path(state_file)
        self.auto_save = auto_save
        self._state: WorldState | None = None

    @property
    def state(self) -> WorldState:
        """Get the current world state, loading from file if needed."""
        if self._state is None:
            logger.info(f"[STATE] First access - loading state from {self.state_file}")
            self._state = self.load()
        return self._state

    def load(self) -> WorldState:
        """Load state from JSON file, creating default if not exists.

        Returns:
            The loaded or newly created WorldState
        """
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                self._state = WorldState.model_validate(data)
                logger.info(f"Loaded world state from {self.state_file}")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error loading state file: {e}")
                logger.info("Creating new default state")
                self._state = self._create_default_state()
        else:
            logger.info(f"State file not found at {self.state_file}, creating default")
            self._state = self._create_default_state()
            # Ensure directory exists and save initial state
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.save()

        return self._state

    def save(self) -> None:
        """Save current state to JSON file."""
        if self._state is None:
            logger.warning("No state to save")
            return

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self._state.model_dump(), f, indent=2)
        logger.debug(f"Saved world state to {self.state_file}")

    def _auto_save(self) -> None:
        """Save if auto_save is enabled."""
        if self.auto_save:
            self.save()

    def get(self, path: str) -> Any:
        """Get value at dot-notation path.

        Args:
            path: Dot-separated path like "combat.active" or "characters.human_player.hp"

        Returns:
            The value at the path, or None if not found

        Example:
            >>> manager.get("combat.active")
            False
            >>> manager.get("characters.human_player.hp")
            10
        """
        parts = path.split(".")
        current: Any = self.state

        for part in parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            elif hasattr(current, "model_dump"):
                # Handle Pydantic models
                data = current.model_dump()
                current = data.get(part)
            else:
                return None

        return current

    def set(self, path: str, value: Any) -> None:
        """Set value at dot-notation path.

        Args:
            path: Dot-separated path like "combat.active" or "current_scene"
            value: The value to set

        Example:
            >>> manager.set("combat.active", True)
            >>> manager.set("current_scene", "goblin_ambush")
        """
        parts = path.split(".")

        if len(parts) == 1:
            # Top-level attribute
            if hasattr(self.state, parts[0]):
                setattr(self.state, parts[0], value)
        else:
            # Navigate to parent and set
            parent = self.state
            for part in parts[:-1]:
                if isinstance(parent, dict):
                    parent = parent.get(part)
                elif hasattr(parent, part):
                    parent = getattr(parent, part)
                else:
                    logger.error(f"Path not found: {path}")
                    return

            final_key = parts[-1]
            if isinstance(parent, dict):
                parent[final_key] = value
            elif hasattr(parent, final_key):
                setattr(parent, final_key, value)
            else:
                logger.error(f"Cannot set {final_key} on {type(parent)}")
                return

        self._auto_save()

    def update_hp(self, entity_id: str, delta: int) -> int:
        """Update HP for a character or enemy.

        Args:
            entity_id: The ID of the character or enemy
            delta: HP change (positive for healing, negative for damage)

        Returns:
            The new HP value

        Raises:
            ValueError: If entity not found
        """
        # Check characters first
        if entity_id in self.state.characters:
            char = self.state.characters[entity_id]
            old_hp = char.hp
            new_hp = max(0, min(char.max_hp, char.hp + delta))
            char.hp = new_hp

            if new_hp == 0 and old_hp > 0:
                logger.info(f"{char.name} has fallen unconscious!")
                if "unconscious" not in char.conditions:
                    char.conditions.append("unconscious")

            if new_hp > 0 and "unconscious" in char.conditions:
                char.conditions.remove("unconscious")
                logger.info(f"{char.name} has regained consciousness!")

            self._auto_save()
            return new_hp

        # Check enemies
        if entity_id in self.state.enemies:
            enemy = self.state.enemies[entity_id]
            old_hp = enemy.hp
            new_hp = max(0, min(enemy.max_hp, enemy.hp + delta))
            enemy.hp = new_hp

            if new_hp == 0 and old_hp > 0:
                enemy.state = "dead"
                logger.info(f"{enemy.name} ({entity_id}) has been slain!")

            self._auto_save()
            return new_hp

        raise ValueError(f"Entity not found: {entity_id}")

    def get_character(self, char_id: str) -> CharacterState | None:
        """Get character by ID.

        Args:
            char_id: The character identifier

        Returns:
            The CharacterState or None if not found
        """
        return self.state.characters.get(char_id)

    def get_enemy(self, enemy_id: str) -> EnemyState | None:
        """Get enemy by ID.

        Args:
            enemy_id: The enemy identifier

        Returns:
            The EnemyState or None if not found
        """
        return self.state.enemies.get(enemy_id)

    def add_character(self, char_id: str, character: CharacterState) -> None:
        """Add a character to the world state.

        Args:
            char_id: Unique identifier for the character
            character: The CharacterState to add
        """
        self.state.characters[char_id] = character
        self._auto_save()

    def add_enemy(self, enemy_id: str, enemy: EnemyState) -> None:
        """Add an enemy to the world state.

        Args:
            enemy_id: Unique identifier for the enemy
            enemy: The EnemyState to add
        """
        self.state.enemies[enemy_id] = enemy
        self._auto_save()

    def remove_enemy(self, enemy_id: str) -> bool:
        """Remove an enemy from the world state.

        Args:
            enemy_id: The enemy identifier

        Returns:
            True if enemy was removed, False if not found
        """
        if enemy_id in self.state.enemies:
            del self.state.enemies[enemy_id]
            self._auto_save()
            return True
        return False

    def set_progress_flag(self, flag: str, value: bool = True) -> None:
        """Set a narrative progress flag.

        Args:
            flag: The flag name
            value: The flag value (default True)
        """
        self.state.narrative_progress.set_flag(flag, value)
        self._auto_save()

    def get_progress_flag(self, flag: str) -> bool:
        """Get a narrative progress flag.

        Args:
            flag: The flag name

        Returns:
            The flag value (False if not set)
        """
        return self.state.narrative_progress.get_flag(flag)

    def get_all_living_enemies(self) -> list[str]:
        """Get IDs of all living enemies.

        Returns:
            List of enemy IDs that are alive
        """
        return [eid for eid, enemy in self.state.enemies.items() if enemy.is_alive]

    def get_party_status(self) -> dict[str, dict[str, Any]]:
        """Get current status of all party members.

        Returns:
            Dict mapping character ID to status info
        """
        return {
            char_id: {
                "name": char.name,
                "hp": char.hp,
                "max_hp": char.max_hp,
                "conditions": char.conditions,
                "is_alive": char.is_alive,
            }
            for char_id, char in self.state.characters.items()
        }

    def _create_default_state(self) -> WorldState:
        """Create the default initial world state for Lost Mines campaign."""
        return WorldState(
            game_id="lost-mines-001",
            current_chapter=1,
            current_scene="intro",
            narrative_progress=NarrativeProgress(),
            characters={
                "human_player": CharacterState(
                    name="Vex",
                    character_class="Rogue",
                    race="Lightfoot Halfling",
                    background="Criminal",
                    level=1,
                    hp=9,
                    max_hp=9,
                    ac=14,
                    stats=CharacterStats(strength=8, dexterity=17, constitution=12, intelligence=13, wisdom=12, charisma=14),
                    proficiency_bonus=2,
                    saving_throws=["dex", "int"],
                    skills=[
                        "acrobatics",
                        "deception",
                        "investigation",
                        "perception",
                        "sleight_of_hand",
                        "stealth",
                    ],
                    inventory=[
                        "shortsword",
                        "shortbow",
                        "quiver (20 arrows)",
                        "leather armor",
                        "two daggers",
                        "thieves tools",
                        "burglar's pack",
                    ],
                    features=["Sneak Attack (1d6)", "Expertise (Stealth, Thieves' Tools)", "Thieves' Cant"],
                    racial_traits=["Lucky", "Brave", "Halfling Nimbleness", "Naturally Stealthy"],
                ),
                "ai_fighter": CharacterState(
                    name="Thokk",
                    character_class="Fighter",
                    race="Half-Orc",
                    background="Soldier",
                    level=1,
                    hp=12,
                    max_hp=12,
                    ac=16,
                    stats=CharacterStats(strength=16, dexterity=14, constitution=14, intelligence=8, wisdom=12, charisma=10),
                    proficiency_bonus=2,
                    saving_throws=["str", "con"],
                    skills=["athletics", "intimidation", "perception", "survival"],
                    inventory=["longsword", "shield", "chain mail", "handaxes (2)", "explorer's pack"],
                    features=["Fighting Style: Defense (+1 AC)", "Second Wind (1d10+1 HP, bonus action, 1/rest)"],
                    racial_traits=["Darkvision", "Menacing", "Relentless Endurance", "Savage Attacks"],
                ),
                "ai_cleric": CharacterState(
                    name="Lira",
                    character_class="Cleric (Life Domain)",
                    race="Human",
                    background="Acolyte",
                    level=1,
                    hp=10,
                    max_hp=10,
                    ac=16,
                    stats=CharacterStats(strength=14, dexterity=10, constitution=12, intelligence=10, wisdom=16, charisma=12),
                    proficiency_bonus=2,
                    saving_throws=["wis", "cha"],
                    skills=["insight", "medicine", "persuasion", "religion"],
                    inventory=["mace", "shield", "scale mail", "holy symbol", "priest's pack"],
                    features=[
                        "Spellcasting",
                        "Divine Domain: Life",
                        "Disciple of Life (+2+spell level HP when healing)",
                    ],
                    spells_known={
                        "cantrips": ["sacred flame", "spare the dying", "guidance"],
                        "1st_level_prepared": ["bless", "cure wounds", "healing word", "shield of faith"],
                        "domain_spells": ["bless", "cure wounds"],
                    },
                    spell_slots={"1st": 2},
                ),
            },
            npcs={
                "gundren": NPCState(
                    name="Gundren Rockseeker",
                    state="captured",
                    location="cragmaw_castle",
                    disposition="friendly",
                ),
                "sildar": NPCState(
                    name="Sildar Hallwinter",
                    state="captured",
                    location="cragmaw_hideout",
                    disposition="friendly",
                ),
            },
            enemies={},
        )


# Global instance for tool access
_manager: WorldStateManager | None = None


def get_world_state_manager(state_file: str = "data/world_state.json") -> WorldStateManager:
    """Get or create the global WorldStateManager instance.

    Args:
        state_file: Path to the state file (only used on first call)

    Returns:
        The WorldStateManager instance
    """
    global _manager
    if _manager is None:
        logger.info(f"[STATE] Creating new WorldStateManager (state_file={state_file})")
        _manager = WorldStateManager(state_file)
    else:
        logger.debug(f"[STATE] Reusing existing WorldStateManager (id={id(_manager)})")
    return _manager


def reset_world_state_manager() -> None:
    """Reset the global WorldStateManager instance.

    Useful for testing or starting a new game.
    """
    global _manager
    _manager = None


def world_state_tool(
    operation: str,
    path: str = "",
    value: Any = None,
    entity_id: str = "",
    delta: int = 0,
) -> str:
    """Tool function for managing game world state.

    This function is designed to be wrapped as a LangChain/Thenvoi tool.

    Args:
        operation: The operation to perform
            - "get": Get value at path
            - "set": Set value at path
            - "update_hp": Update entity HP by delta
            - "save": Save state to file
            - "load": Load state from file
            - "get_party_status": Get status of all party members
            - "get_living_enemies": Get list of living enemy IDs
        path: Dot-notation path for get/set operations
        value: Value to set (for "set" operation)
        entity_id: Entity ID (for "update_hp" operation)
        delta: HP change (for "update_hp" operation)

    Returns:
        String description of the result

    Example:
        >>> world_state_tool("get", path="combat.active")
        "combat.active = False"
        >>> world_state_tool("set", path="current_scene", value="goblin_ambush")
        "Set current_scene = goblin_ambush"
        >>> world_state_tool("update_hp", entity_id="goblin_1", delta=-7)
        "goblin_1 HP: 7 -> 0 (DEAD)"
    """
    manager = get_world_state_manager()

    if operation == "get":
        if not path:
            return "Error: path required for get operation"
        result = manager.get(path)
        return f"{path} = {result}"

    elif operation == "set":
        if not path:
            return "Error: path required for set operation"
        manager.set(path, value)
        return f"Set {path} = {value}"

    elif operation == "update_hp":
        if not entity_id:
            return "Error: entity_id required for update_hp operation"
        try:
            # Get old HP first
            char = manager.get_character(entity_id)
            enemy = manager.get_enemy(entity_id)
            entity = char or enemy
            if not entity:
                return f"Error: Entity not found: {entity_id}"

            old_hp = entity.hp
            new_hp = manager.update_hp(entity_id, delta)

            # Determine status
            if new_hp == 0:
                if char:
                    status = "UNCONSCIOUS"
                else:
                    status = "DEAD"
                return f"{entity_id} HP: {old_hp} -> {new_hp} ({status})"
            else:
                return f"{entity_id} HP: {old_hp} -> {new_hp}"

        except ValueError as e:
            return f"Error: {e}"

    elif operation == "save":
        manager.save()
        return "World state saved"

    elif operation == "load":
        manager.load()
        return "World state loaded"

    elif operation == "get_party_status":
        status = manager.get_party_status()
        lines = []
        for char_id, info in status.items():
            conditions = ", ".join(info["conditions"]) if info["conditions"] else "none"
            status_str = "alive" if info["is_alive"] else "unconscious"
            lines.append(f"- {info['name']}: {info['hp']}/{info['max_hp']} HP ({status_str}, conditions: {conditions})")
        return "Party Status:\n" + "\n".join(lines)

    elif operation == "get_living_enemies":
        enemies = manager.get_all_living_enemies()
        if enemies:
            return f"Living enemies: {', '.join(enemies)}"
        return "No living enemies"

    else:
        return f"Error: Unknown operation: {operation}"
