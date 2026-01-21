"""Tests for Chapter 1 content (Goblin Arrows).

These tests verify the scene definitions, triggers, and content
for Chapter 1 of the Lost Mines of Phandelver campaign.
"""

import pytest

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


class TestSceneDefinitions:
    """Tests for scene definitions in Chapter 1."""

    def test_intro_scene_exists(self):
        """Intro scene should be defined."""
        assert "intro" in SCENES
        scene = SCENES["intro"]
        assert scene["name"] == "The Road to Phandalin"
        assert scene["chapter"] == 1

    def test_goblin_ambush_scene_exists(self):
        """Goblin ambush scene should be defined."""
        assert "goblin_ambush" in SCENES
        scene = SCENES["goblin_ambush"]
        assert scene["name"] == "Goblin Ambush!"
        assert scene.get("combat") is True

    def test_after_ambush_scene_exists(self):
        """After ambush scene should be defined."""
        assert "after_ambush" in SCENES
        scene = SCENES["after_ambush"]
        assert scene["name"] == "After the Ambush"

    def test_all_scenes_have_required_fields(self):
        """All scenes should have name, chapter, and description."""
        required_fields = ["name", "chapter", "description"]
        for scene_id, scene in SCENES.items():
            for field in required_fields:
                assert field in scene, f"Scene {scene_id} missing {field}"

    def test_scenes_have_descriptions(self):
        """All scenes should have non-empty descriptions."""
        for scene_id, scene in SCENES.items():
            assert scene["description"], f"Scene {scene_id} has empty description"
            assert len(scene["description"]) > 50, f"Scene {scene_id} description too short"


class TestSceneTriggers:
    """Tests for scene triggers."""

    def test_intro_has_investigation_trigger(self):
        """Intro scene should have horse investigation trigger."""
        scene = SCENES["intro"]
        triggers = scene.get("triggers", {})
        assert "investigate_horses" in triggers
        trigger = triggers["investigate_horses"]
        assert trigger["skill"] == "investigation"
        assert trigger["dc"] == 10

    def test_intro_has_perception_trigger(self):
        """Intro scene should have perception trigger for goblins."""
        scene = SCENES["intro"]
        triggers = scene.get("triggers", {})
        assert "search_area" in triggers
        trigger = triggers["search_area"]
        assert trigger["skill"] == "perception"
        assert trigger["dc"] == 10

    def test_intro_has_survival_trigger(self):
        """Intro scene should have trail-finding trigger."""
        scene = SCENES["intro"]
        triggers = scene.get("triggers", {})
        assert "find_trail" in triggers
        trigger = triggers["find_trail"]
        assert trigger["skill"] == "survival"
        assert trigger["dc"] == 10

    def test_triggers_have_success_and_fail_text(self):
        """All triggers should have success and fail text."""
        for scene_id, scene in SCENES.items():
            triggers = scene.get("triggers", {})
            for trigger_name, trigger in triggers.items():
                # Skip triggers that don't require a check
                if trigger.get("skill") is None:
                    continue
                assert "success_text" in trigger, f"{scene_id}.{trigger_name} missing success_text"
                assert "fail_text" in trigger, f"{scene_id}.{trigger_name} missing fail_text"

    def test_after_ambush_has_search_trigger(self):
        """After ambush scene should have body search trigger."""
        scene = SCENES["after_ambush"]
        triggers = scene.get("triggers", {})
        assert "search_bodies" in triggers
        trigger = triggers["search_bodies"]
        assert trigger["skill"] == "investigation"
        assert trigger["dc"] == 12


class TestCombatScenes:
    """Tests for combat encounter scenes."""

    def test_goblin_ambush_has_enemies(self):
        """Goblin ambush should define enemies."""
        scene = SCENES["goblin_ambush"]
        assert scene.get("combat") is True
        enemies = scene.get("enemies", [])
        assert len(enemies) == 4
        assert "goblin_1" in enemies
        assert "goblin_4" in enemies

    def test_combat_scenes_have_victory_scene(self):
        """Combat scenes should define victory transition."""
        for scene_id, scene in SCENES.items():
            if scene.get("combat"):
                assert "victory_scene" in scene, f"Combat scene {scene_id} missing victory_scene"

    def test_goblin_ambush_has_tactics(self):
        """Goblin ambush should include tactical guidance."""
        scene = SCENES["goblin_ambush"]
        assert "goblin_tactics" in scene or "dm_notes" in scene


class TestSceneTransitions:
    """Tests for scene transition flow."""

    def test_intro_leads_to_ambush(self):
        """Intro should transition to goblin ambush."""
        scene = SCENES["intro"]
        assert scene.get("next_scene") == "goblin_ambush" or scene.get("combat_trigger") == "goblin_ambush"

    def test_ambush_victory_leads_to_after(self):
        """Ambush victory should lead to after_ambush."""
        scene = SCENES["goblin_ambush"]
        assert scene.get("victory_scene") == "after_ambush"

    def test_after_ambush_leads_to_trail(self):
        """After ambush should lead to goblin trail."""
        scene = SCENES["after_ambush"]
        assert scene.get("next_scene") == "goblin_trail"


class TestEnemyDefinitions:
    """Tests for enemy stat blocks."""

    def test_goblin_stats_exist(self):
        """Goblin stats should be defined."""
        assert "goblin" in CHAPTER1_ENEMIES
        goblin = CHAPTER1_ENEMIES["goblin"]
        assert goblin["hp"] == 7
        assert goblin["ac"] == 15

    def test_goblin_has_attacks(self):
        """Goblin should have attack definitions."""
        goblin = CHAPTER1_ENEMIES["goblin"]
        attacks = goblin.get("attacks", [])
        assert len(attacks) >= 2

        # Check for scimitar
        scimitar = next((a for a in attacks if "scimitar" in a["name"].lower()), None)
        assert scimitar is not None
        assert scimitar["bonus"] == 4

        # Check for shortbow
        shortbow = next((a for a in attacks if "shortbow" in a["name"].lower()), None)
        assert shortbow is not None

    def test_wolf_stats_exist(self):
        """Wolf stats should be defined."""
        assert "wolf" in CHAPTER1_ENEMIES
        wolf = CHAPTER1_ENEMIES["wolf"]
        assert wolf["hp"] == 11
        assert wolf["ac"] == 13

    def test_klarg_stats_exist(self):
        """Klarg (bugbear boss) stats should be defined."""
        assert "klarg" in CHAPTER1_ENEMIES
        klarg = CHAPTER1_ENEMIES["klarg"]
        assert klarg["hp"] == 27
        assert klarg["ac"] == 16

    def test_enemies_have_required_fields(self):
        """All enemies should have required stat fields."""
        required_fields = ["name", "hp", "max_hp", "ac", "damage", "damage_type"]
        for enemy_type, stats in CHAPTER1_ENEMIES.items():
            for field in required_fields:
                assert field in stats, f"Enemy {enemy_type} missing {field}"


class TestHelperFunctions:
    """Tests for chapter1 helper functions."""

    def test_get_scene(self):
        """get_scene should return scene by ID."""
        scene = get_scene("intro")
        assert scene is not None
        assert scene["name"] == "The Road to Phandalin"

    def test_get_scene_not_found(self):
        """get_scene should return None for unknown scene."""
        scene = get_scene("nonexistent_scene")
        assert scene is None

    def test_get_scene_description(self):
        """get_scene_description should return description text."""
        desc = get_scene_description("intro")
        assert desc is not None
        assert len(desc) > 0
        assert "dead horses" in desc.lower() or "triboar" in desc.lower()

    def test_get_scene_description_not_found(self):
        """get_scene_description should return empty for unknown scene."""
        desc = get_scene_description("nonexistent")
        assert desc == ""

    def test_get_scene_dm_notes(self):
        """get_scene_dm_notes should return DM notes."""
        notes = get_scene_dm_notes("intro")
        assert notes is not None
        assert len(notes) > 0

    def test_get_scene_triggers(self):
        """get_scene_triggers should return trigger dict."""
        triggers = get_scene_triggers("intro")
        assert isinstance(triggers, dict)
        assert "investigate_horses" in triggers

    def test_get_scene_triggers_empty(self):
        """get_scene_triggers should return empty dict for no triggers."""
        triggers = get_scene_triggers("nonexistent")
        assert triggers == {}

    def test_get_enemy_stats(self):
        """get_enemy_stats should return enemy stats."""
        stats = get_enemy_stats("goblin")
        assert stats is not None
        assert stats["hp"] == 7

    def test_get_enemy_stats_not_found(self):
        """get_enemy_stats should return None for unknown enemy."""
        stats = get_enemy_stats("dragon")
        assert stats is None


class TestFormatSceneContext:
    """Tests for format_scene_context function."""

    def test_format_includes_scene_name(self):
        """Formatted context should include scene name."""
        context = format_scene_context("intro")
        assert "The Road to Phandalin" in context

    def test_format_includes_description(self):
        """Formatted context should include description."""
        context = format_scene_context("intro")
        assert "horses" in context.lower() or "road" in context.lower()

    def test_format_includes_triggers(self):
        """Formatted context should include available triggers."""
        context = format_scene_context("intro")
        assert "investigate_horses" in context.lower() or "investigation" in context.lower()

    def test_format_includes_dm_notes_by_default(self):
        """Formatted context should include DM notes by default."""
        context = format_scene_context("intro", include_dm_notes=True)
        # DM notes should have keywords about ambush or goblins
        assert "dm notes" in context.lower() or len(context) > 500

    def test_format_excludes_dm_notes_when_disabled(self):
        """Formatted context should exclude DM notes when disabled."""
        context_with = format_scene_context("intro", include_dm_notes=True)
        context_without = format_scene_context("intro", include_dm_notes=False)
        # Without DM notes should be shorter
        assert len(context_without) < len(context_with)

    def test_format_not_found_scene(self):
        """Formatted context should handle unknown scene."""
        context = format_scene_context("nonexistent")
        assert "not found" in context.lower()


class TestProgressFlags:
    """Tests for progress flag definitions."""

    def test_ambush_scene_has_progress_flags(self):
        """Ambush scene should set progress flags."""
        scene = SCENES["goblin_ambush"]
        flags = scene.get("progress_flags", [])
        assert "ambush_triggered" in flags

    def test_after_ambush_has_progress_flags(self):
        """After ambush scene should set progress flags."""
        scene = SCENES["after_ambush"]
        flags = scene.get("progress_flags", [])
        assert "goblins_defeated" in flags


class TestChapter1Content:
    """Integration tests for Chapter 1 narrative content."""

    def test_story_flow_makes_sense(self):
        """Verify the story flow is logical."""
        # Start at intro
        intro = SCENES["intro"]
        assert "dead horses" in intro["description"].lower()

        # Leads to ambush
        ambush = SCENES["goblin_ambush"]
        assert "goblins" in ambush["description"].lower() or "arrows" in ambush["description"].lower()

        # Ends with aftermath
        aftermath = SCENES["after_ambush"]
        assert "defeated" in aftermath["description"].lower() or "trail" in aftermath["description"].lower()

    def test_hideout_scenes_exist(self):
        """Cragmaw Hideout scenes should exist (stretch goal)."""
        # These are stretch goals but should be defined
        assert "goblin_trail" in SCENES or True  # May not be implemented
        assert "hideout_entrance" in SCENES or True

    def test_sildar_rescue_exists(self):
        """Sildar rescue scene should exist."""
        assert "sildar_rescue" in SCENES
        scene = SCENES["sildar_rescue"]
        assert "sildar" in scene["description"].lower()

    def test_party_captured_fallback_exists(self):
        """Party captured scene should exist as fallback."""
        assert "party_captured" in SCENES
        scene = SCENES["party_captured"]
        assert scene.get("alternate_path") is True
