"""Tests for scene management utilities.

These tests verify the SceneManager and related utility functions.
"""

import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os

from src.content.scenes import (
    SceneManager,
    create_trigger_result,
    format_trigger_for_dm,
    get_skill_modifier,
)
from src.content.chapter1 import SCENES
from src.tools.world_state import WorldStateManager


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{}')
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def state_manager(temp_state_file):
    """Create a WorldStateManager with temporary file."""
    return WorldStateManager(temp_state_file, auto_save=False)


@pytest.fixture
def scene_manager(state_manager):
    """Create a SceneManager with test scenes."""
    return SceneManager(SCENES, state_manager)


class TestSceneManager:
    """Tests for SceneManager class."""

    def test_init_with_scenes(self, state_manager):
        """SceneManager should initialize with scenes and state manager."""
        manager = SceneManager(SCENES, state_manager)
        assert manager.scenes == SCENES
        assert manager.state_manager == state_manager

    def test_get_current_scene_id(self, scene_manager):
        """Should return current scene ID from state."""
        # Default state has "intro" as current scene
        assert scene_manager.get_current_scene_id() == "intro"

    def test_get_current_scene(self, scene_manager):
        """Should return current scene definition."""
        scene = scene_manager.get_current_scene()
        assert scene is not None
        assert scene["name"] == "The Road to Phandalin"

    def test_get_scene_by_id(self, scene_manager):
        """Should return scene by specific ID."""
        scene = scene_manager.get_scene("goblin_ambush")
        assert scene is not None
        assert scene["name"] == "Goblin Ambush!"

    def test_get_scene_not_found(self, scene_manager):
        """Should return None for unknown scene."""
        scene = scene_manager.get_scene("nonexistent")
        assert scene is None

    def test_transition_to_scene(self, scene_manager):
        """Should transition to new scene."""
        result = scene_manager.transition_to_scene("goblin_ambush")
        assert result is True
        assert scene_manager.get_current_scene_id() == "goblin_ambush"

    def test_transition_to_unknown_scene(self, scene_manager):
        """Should fail to transition to unknown scene."""
        result = scene_manager.transition_to_scene("nonexistent")
        assert result is False
        # Should remain at original scene
        assert scene_manager.get_current_scene_id() == "intro"

    def test_get_available_triggers(self, scene_manager):
        """Should return triggers for current scene."""
        triggers = scene_manager.get_available_triggers()
        assert isinstance(triggers, dict)
        assert "investigate_horses" in triggers

    def test_get_trigger(self, scene_manager):
        """Should return specific trigger."""
        trigger = scene_manager.get_trigger("investigate_horses")
        assert trigger is not None
        assert trigger["skill"] == "investigation"
        assert trigger["dc"] == 10

    def test_get_trigger_not_found(self, scene_manager):
        """Should return None for unknown trigger."""
        trigger = scene_manager.get_trigger("nonexistent_trigger")
        assert trigger is None

    def test_is_combat_scene_false(self, scene_manager):
        """Should return False for non-combat scene."""
        assert scene_manager.is_combat_scene() is False

    def test_is_combat_scene_true(self, scene_manager):
        """Should return True for combat scene."""
        scene_manager.transition_to_scene("goblin_ambush")
        assert scene_manager.is_combat_scene() is True

    def test_get_scene_enemies(self, scene_manager):
        """Should return enemy IDs for combat scene."""
        scene_manager.transition_to_scene("goblin_ambush")
        enemies = scene_manager.get_scene_enemies()
        assert len(enemies) == 4
        assert "goblin_1" in enemies


class TestSceneManagerDMContext:
    """Tests for DM context generation."""

    def test_get_dm_context_includes_scene_name(self, scene_manager):
        """DM context should include scene name."""
        context = scene_manager.get_dm_context()
        assert "The Road to Phandalin" in context

    def test_get_dm_context_includes_chapter(self, scene_manager):
        """DM context should include chapter number."""
        context = scene_manager.get_dm_context()
        assert "Chapter" in context

    def test_get_dm_context_includes_triggers(self, scene_manager):
        """DM context should include available triggers."""
        context = scene_manager.get_dm_context()
        assert "Skill Check" in context or "investigate" in context.lower()

    def test_get_dm_context_includes_dm_notes(self, scene_manager):
        """DM context should include DM notes by default."""
        context = scene_manager.get_dm_context(include_dm_notes=True)
        assert "DM Notes" in context or len(context) > 500

    def test_get_dm_context_excludes_dm_notes(self, scene_manager):
        """DM context should exclude DM notes when disabled."""
        with_notes = scene_manager.get_dm_context(include_dm_notes=True)
        without_notes = scene_manager.get_dm_context(include_dm_notes=False)
        assert len(without_notes) < len(with_notes)


class TestCreateTriggerResult:
    """Tests for create_trigger_result function."""

    def test_success_result(self):
        """Should return success result when roll meets DC."""
        trigger = {
            "skill": "investigation",
            "dc": 10,
            "success_text": "You found it!",
            "fail_text": "Nothing here.",
        }
        result = create_trigger_result(trigger, roll_total=15)
        assert result["success"] is True
        assert result["text"] == "You found it!"
        assert result["dc"] == 10
        assert result["roll"] == 15

    def test_failure_result(self):
        """Should return failure result when roll is below DC."""
        trigger = {
            "skill": "perception",
            "dc": 15,
            "success_text": "You see them!",
            "fail_text": "The forest seems quiet.",
        }
        result = create_trigger_result(trigger, roll_total=12)
        assert result["success"] is False
        assert result["text"] == "The forest seems quiet."

    def test_exact_dc_succeeds(self):
        """Roll exactly equal to DC should succeed."""
        trigger = {"skill": "survival", "dc": 10, "success_text": "Found it!", "fail_text": "Lost."}
        result = create_trigger_result(trigger, roll_total=10)
        assert result["success"] is True

    def test_default_text(self):
        """Should use default text if not provided."""
        trigger = {"skill": "athletics", "dc": 12}
        result = create_trigger_result(trigger, roll_total=8)
        assert "fail" in result["text"].lower() or "nothing" in result["text"].lower()


class TestFormatTriggerForDM:
    """Tests for format_trigger_for_dm function."""

    def test_format_basic_trigger(self):
        """Should format trigger with skill and DC."""
        trigger = {"skill": "investigation", "dc": 10}
        formatted = format_trigger_for_dm("investigate_horses", trigger)
        assert "investigate_horses" in formatted
        assert "INVESTIGATION" in formatted
        assert "DC 10" in formatted

    def test_format_perception_trigger(self):
        """Should format perception trigger correctly."""
        trigger = {"skill": "perception", "dc": 15}
        formatted = format_trigger_for_dm("spot_hidden", trigger)
        assert "PERCEPTION" in formatted
        assert "DC 15" in formatted


class TestGetSkillModifier:
    """Tests for get_skill_modifier function."""

    def test_strength_skill(self):
        """Athletics should use strength."""
        stats = {"str": 16, "dex": 10, "con": 12, "int": 10, "wis": 10, "cha": 10}
        mod = get_skill_modifier(stats, "athletics")
        assert mod == 3  # (16 - 10) // 2

    def test_dexterity_skill(self):
        """Stealth should use dexterity."""
        stats = {"str": 10, "dex": 17, "con": 10, "int": 10, "wis": 10, "cha": 10}
        mod = get_skill_modifier(stats, "stealth")
        assert mod == 3  # (17 - 10) // 2

    def test_wisdom_skill(self):
        """Perception should use wisdom."""
        stats = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 14, "cha": 10}
        mod = get_skill_modifier(stats, "perception")
        assert mod == 2  # (14 - 10) // 2

    def test_intelligence_skill(self):
        """Investigation should use intelligence."""
        stats = {"str": 10, "dex": 10, "con": 10, "int": 18, "wis": 10, "cha": 10}
        mod = get_skill_modifier(stats, "investigation")
        assert mod == 4  # (18 - 10) // 2

    def test_charisma_skill(self):
        """Persuasion should use charisma."""
        stats = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 15}
        mod = get_skill_modifier(stats, "persuasion")
        assert mod == 2  # (15 - 10) // 2

    def test_negative_modifier(self):
        """Low ability score should give negative modifier."""
        stats = {"str": 8, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
        mod = get_skill_modifier(stats, "athletics")
        assert mod == -1  # (8 - 10) // 2

    def test_unknown_skill(self):
        """Unknown skill should default to wisdom."""
        stats = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 14, "cha": 10}
        mod = get_skill_modifier(stats, "unknown_skill")
        assert mod == 2  # Uses wisdom by default

    def test_case_insensitive(self):
        """Skill lookup should be case insensitive."""
        stats = {"str": 10, "dex": 17, "con": 10, "int": 10, "wis": 10, "cha": 10}
        mod1 = get_skill_modifier(stats, "STEALTH")
        mod2 = get_skill_modifier(stats, "stealth")
        assert mod1 == mod2


class TestSceneManagerCombatEnd:
    """Tests for combat end detection."""

    def test_check_scene_completion_no_combat(self, scene_manager):
        """Non-combat scene should not auto-complete."""
        complete, next_scene = scene_manager.check_scene_completion()
        # Intro is not auto-complete
        assert complete is False or next_scene is None

    def test_check_scene_completion_combat_ongoing(self, scene_manager):
        """Combat scene with living enemies should not complete."""
        scene_manager.transition_to_scene("goblin_ambush")

        # Add enemies to state
        from src.game.models import EnemyState
        scene_manager.state_manager.add_enemy(
            "goblin_1",
            EnemyState(name="Goblin 1", hp=7, max_hp=7, ac=15, state="alive")
        )

        complete, next_scene = scene_manager.check_scene_completion()
        assert complete is False

    def test_check_scene_completion_combat_victory(self, scene_manager):
        """Combat scene with all enemies dead should complete."""
        scene_manager.transition_to_scene("goblin_ambush")

        # Enemies dict is empty = all dead
        # (Or we could add dead enemies)
        complete, next_scene = scene_manager.check_scene_completion()
        # With no enemies added, all enemies are considered dead
        assert complete is True or next_scene == "after_ambush"
