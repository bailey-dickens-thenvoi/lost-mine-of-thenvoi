"""Tests for World State Manager."""

import json
import tempfile
from pathlib import Path

import pytest

from src.game.models import (
    CharacterState,
    CharacterStats,
    CombatState,
    EnemyState,
    NarrativeProgress,
    NPCState,
    WorldState,
)
from src.tools.world_state import (
    WorldStateManager,
    get_world_state_manager,
    reset_world_state_manager,
    world_state_tool,
)


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = Path(f.name)
    yield str(path)
    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def manager(temp_state_file):
    """Create a WorldStateManager with a temp file."""
    return WorldStateManager(temp_state_file, auto_save=False)


@pytest.fixture(autouse=True)
def reset_global_manager():
    """Reset global manager before each test."""
    reset_world_state_manager()
    yield
    reset_world_state_manager()


class TestWorldStateModels:
    """Tests for Pydantic models."""

    def test_combat_state_defaults(self):
        """CombatState should have sensible defaults."""
        combat = CombatState()
        assert combat.active is False
        assert combat.round == 0
        assert combat.turn_order == []
        assert combat.current_turn_index == 0

    def test_combat_state_get_current_combatant(self):
        """Should return current combatant or None."""
        combat = CombatState()
        assert combat.get_current_combatant() is None

        combat.active = True
        combat.turn_order = ["player1", "goblin1", "player2"]
        combat.current_turn_index = 1
        assert combat.get_current_combatant() == "goblin1"

    def test_character_stats_modifier(self):
        """Should calculate ability modifiers correctly."""
        stats = CharacterStats(strength=8, dexterity=17, constitution=12, intelligence=10, wisdom=14, charisma=18)
        assert stats.get_modifier("str") == -1
        assert stats.get_modifier("dex") == 3
        assert stats.get_modifier("con") == 1
        assert stats.get_modifier("int") == 0
        assert stats.get_modifier("wis") == 2
        assert stats.get_modifier("cha") == 4

    def test_character_state_alive_check(self):
        """Should correctly detect alive/unconscious state."""
        char = CharacterState(
            name="Test",
            character_class="Fighter",
            hp=10,
            max_hp=10,
            ac=15,
            stats=CharacterStats(),
        )
        assert char.is_alive is True
        assert char.is_unconscious is False

        char.hp = 0
        assert char.is_alive is False
        assert char.is_unconscious is True

    def test_enemy_state_alive_check(self):
        """Should correctly detect alive state."""
        enemy = EnemyState(name="Goblin", hp=7, max_hp=7, ac=15)
        assert enemy.is_alive is True

        enemy.hp = 0
        assert enemy.is_alive is False

        enemy.hp = 7
        enemy.state = "fled"
        assert enemy.is_alive is False

    def test_narrative_progress_flags(self):
        """Should set and get progress flags."""
        progress = NarrativeProgress()

        # Built-in flag
        assert progress.get_flag("goblins_defeated") is False
        progress.set_flag("goblins_defeated", True)
        assert progress.get_flag("goblins_defeated") is True

        # Custom flag
        assert progress.get_flag("custom_event") is False
        progress.set_flag("custom_event", True)
        assert progress.get_flag("custom_event") is True


class TestWorldStateManager:
    """Tests for WorldStateManager class."""

    def test_creates_default_state(self, temp_state_file):
        """Should create default state if file doesn't exist."""
        manager = WorldStateManager(temp_state_file)
        state = manager.load()

        assert state.game_id == "lost-mines-001"
        assert state.current_chapter == 1
        assert state.current_scene == "intro"
        assert "human_player" in state.characters
        assert "ai_fighter" in state.characters
        assert "ai_cleric" in state.characters

    def test_save_and_load(self, temp_state_file):
        """Should save and reload state correctly."""
        manager = WorldStateManager(temp_state_file, auto_save=False)
        manager.load()

        manager.state.current_scene = "goblin_ambush"
        manager.state.narrative_progress.ambush_triggered = True
        manager.save()

        # Create new manager and load
        manager2 = WorldStateManager(temp_state_file, auto_save=False)
        state2 = manager2.load()

        assert state2.current_scene == "goblin_ambush"
        assert state2.narrative_progress.ambush_triggered is True

    def test_get_path_simple(self, manager):
        """Should get top-level values."""
        assert manager.get("current_scene") == "intro"
        assert manager.get("current_chapter") == 1

    def test_get_path_nested(self, manager):
        """Should get nested values with dot notation."""
        assert manager.get("combat.active") is False
        assert manager.get("narrative_progress.goblins_defeated") is False

    def test_get_path_character(self, manager):
        """Should get character data."""
        assert manager.get("characters.human_player.name") == "Vex"
        assert manager.get("characters.ai_fighter.hp") == 12

    def test_get_path_not_found(self, manager):
        """Should return None for invalid paths."""
        assert manager.get("nonexistent") is None
        assert manager.get("combat.nonexistent") is None

    def test_set_path_simple(self, manager):
        """Should set top-level values."""
        manager.set("current_scene", "goblin_ambush")
        assert manager.get("current_scene") == "goblin_ambush"

    def test_set_path_nested(self, manager):
        """Should set nested values."""
        manager.set("combat.active", True)
        assert manager.get("combat.active") is True

        manager.set("combat.round", 3)
        assert manager.get("combat.round") == 3

    def test_update_hp_character_damage(self, manager):
        """Should damage characters and track unconscious state."""
        # Damage the rogue
        new_hp = manager.update_hp("human_player", -5)
        assert new_hp == 4
        assert manager.state.characters["human_player"].hp == 4

    def test_update_hp_character_heal(self, manager):
        """Should heal characters up to max HP."""
        # Damage then heal
        manager.update_hp("human_player", -5)
        new_hp = manager.update_hp("human_player", 10)
        assert new_hp == 9  # Max HP is 9

    def test_update_hp_character_unconscious(self, manager):
        """Should mark characters unconscious at 0 HP."""
        manager.update_hp("human_player", -20)
        char = manager.get_character("human_player")

        assert char.hp == 0
        assert "unconscious" in char.conditions

    def test_update_hp_character_revive(self, manager):
        """Should remove unconscious when healed."""
        manager.update_hp("human_player", -20)
        manager.update_hp("human_player", 5)
        char = manager.get_character("human_player")

        assert char.hp == 5
        assert "unconscious" not in char.conditions

    def test_update_hp_enemy_damage(self, manager):
        """Should damage enemies and mark dead at 0 HP."""
        # Add an enemy
        manager.add_enemy(
            "goblin_1", EnemyState(name="Goblin", hp=7, max_hp=7, ac=15, state="alive")
        )

        new_hp = manager.update_hp("goblin_1", -5)
        assert new_hp == 2

        new_hp = manager.update_hp("goblin_1", -5)
        assert new_hp == 0
        assert manager.get_enemy("goblin_1").state == "dead"

    def test_update_hp_entity_not_found(self, manager):
        """Should raise ValueError for unknown entity."""
        with pytest.raises(ValueError, match="Entity not found"):
            manager.update_hp("nonexistent", -5)

    def test_add_and_get_character(self, manager):
        """Should add and retrieve characters."""
        new_char = CharacterState(
            name="Test Character",
            character_class="Wizard",
            hp=6,
            max_hp=6,
            ac=12,
            stats=CharacterStats(),
        )
        manager.add_character("test_wizard", new_char)

        retrieved = manager.get_character("test_wizard")
        assert retrieved is not None
        assert retrieved.name == "Test Character"

    def test_add_remove_enemy(self, manager):
        """Should add and remove enemies."""
        enemy = EnemyState(name="Goblin", hp=7, max_hp=7, ac=15)
        manager.add_enemy("goblin_1", enemy)

        assert manager.get_enemy("goblin_1") is not None
        assert manager.remove_enemy("goblin_1") is True
        assert manager.get_enemy("goblin_1") is None
        assert manager.remove_enemy("goblin_1") is False

    def test_get_all_living_enemies(self, manager):
        """Should return only living enemies."""
        manager.add_enemy("goblin_1", EnemyState(name="G1", hp=7, max_hp=7, ac=15, state="alive"))
        manager.add_enemy("goblin_2", EnemyState(name="G2", hp=0, max_hp=7, ac=15, state="dead"))
        manager.add_enemy("goblin_3", EnemyState(name="G3", hp=7, max_hp=7, ac=15, state="fled"))

        living = manager.get_all_living_enemies()
        assert "goblin_1" in living
        assert "goblin_2" not in living
        assert "goblin_3" not in living

    def test_get_party_status(self, manager):
        """Should return party status summary."""
        status = manager.get_party_status()

        assert "human_player" in status
        assert status["human_player"]["name"] == "Vex"
        assert status["human_player"]["hp"] == 9
        assert status["human_player"]["is_alive"] is True

    def test_progress_flags(self, manager):
        """Should set and get progress flags."""
        assert manager.get_progress_flag("goblins_defeated") is False
        manager.set_progress_flag("goblins_defeated", True)
        assert manager.get_progress_flag("goblins_defeated") is True

    def test_auto_save(self, temp_state_file):
        """Should auto-save when enabled."""
        manager = WorldStateManager(temp_state_file, auto_save=True)
        manager.load()
        manager.set("current_scene", "test_scene")

        # Read file directly to verify save
        with open(temp_state_file) as f:
            data = json.load(f)
        assert data["current_scene"] == "test_scene"


class TestWorldStateTool:
    """Tests for the world_state_tool function."""

    def test_get_operation(self, temp_state_file):
        """Should get values via tool."""
        reset_world_state_manager()
        # Initialize global manager with temp file
        manager = get_world_state_manager(temp_state_file)

        result = world_state_tool("get", path="current_scene")
        assert "current_scene = intro" in result

    def test_set_operation(self, temp_state_file):
        """Should set values via tool."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("set", path="current_scene", value="goblin_ambush")
        assert "Set current_scene = goblin_ambush" in result

        result = world_state_tool("get", path="current_scene")
        assert "goblin_ambush" in result

    def test_update_hp_operation(self, temp_state_file):
        """Should update HP via tool."""
        reset_world_state_manager()
        manager = get_world_state_manager(temp_state_file)

        result = world_state_tool("update_hp", entity_id="human_player", delta=-5)
        assert "human_player HP: 9 -> 4" in result

    def test_update_hp_unconscious(self, temp_state_file):
        """Should show UNCONSCIOUS status for players at 0 HP."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("update_hp", entity_id="human_player", delta=-20)
        assert "UNCONSCIOUS" in result

    def test_update_hp_enemy_death(self, temp_state_file):
        """Should show DEAD status for enemies at 0 HP."""
        reset_world_state_manager()
        manager = get_world_state_manager(temp_state_file)
        manager.add_enemy("goblin_1", EnemyState(name="Goblin", hp=7, max_hp=7, ac=15))

        result = world_state_tool("update_hp", entity_id="goblin_1", delta=-10)
        assert "DEAD" in result

    def test_get_party_status_operation(self, temp_state_file):
        """Should return party status via tool."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("get_party_status")
        assert "Party Status:" in result
        assert "Vex" in result
        assert "Thokk" in result
        assert "Lira" in result

    def test_get_living_enemies_operation(self, temp_state_file):
        """Should return living enemies via tool."""
        reset_world_state_manager()
        manager = get_world_state_manager(temp_state_file)

        result = world_state_tool("get_living_enemies")
        assert "No living enemies" in result

        manager.add_enemy("goblin_1", EnemyState(name="G1", hp=7, max_hp=7, ac=15))
        result = world_state_tool("get_living_enemies")
        assert "goblin_1" in result

    def test_save_load_operations(self, temp_state_file):
        """Should save and load via tool."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("save")
        assert "saved" in result.lower()

        result = world_state_tool("load")
        assert "loaded" in result.lower()

    def test_error_missing_path(self, temp_state_file):
        """Should return error for missing path."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("get")
        assert "Error" in result

    def test_error_unknown_operation(self, temp_state_file):
        """Should return error for unknown operation."""
        reset_world_state_manager()
        get_world_state_manager(temp_state_file)

        result = world_state_tool("invalid_op")
        assert "Error" in result
        assert "Unknown operation" in result
