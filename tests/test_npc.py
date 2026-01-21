"""Tests for NPC Agent and helpers."""

import json
import tempfile
from pathlib import Path

import pytest

from src.agents.npc_agent import NPCAdapter, NPC_SYSTEM_PROMPT
from src.game.npcs import (
    format_npc_prompt,
    format_npc_prompt_custom,
    get_alive_npcs,
    get_npc,
    get_npc_names,
    get_npcs_at_location,
    load_npc_data,
)


@pytest.fixture
def sample_npc_data():
    """Sample NPC data for testing."""
    return {
        "gundren_rockseeker": {
            "name": "Gundren Rockseeker",
            "race": "Dwarf",
            "role": "Quest giver",
            "personality": "Gruff but kind. Dwarven accent.",
            "knowledge": ["Wave Echo Cave location"],
            "goals": "Reclaim Wave Echo Cave",
            "secrets": "Has a map",
            "current_state": "captured",
            "location": "cragmaw_castle",
        },
        "sildar_hallwinter": {
            "name": "Sildar Hallwinter",
            "race": "Human",
            "role": "Warrior",
            "personality": "Honorable, formal.",
            "knowledge": ["Lords' Alliance"],
            "goals": "Find Iarno",
            "secrets": "Fears the worst",
            "current_state": "captured",
            "location": "cragmaw_hideout",
        },
        "klarg": {
            "name": "Klarg",
            "race": "Bugbear",
            "role": "Boss",
            "personality": "Brutish, broken Common.",
            "knowledge": ["Black Spider"],
            "goals": "Please King Grol",
            "secrets": "Insecure",
            "current_state": "alive",
            "location": "cragmaw_hideout",
        },
        "dead_npc": {
            "name": "Dead NPC",
            "race": "Human",
            "role": "Test",
            "personality": "None",
            "knowledge": [],
            "goals": "None",
            "secrets": "None",
            "current_state": "dead",
            "location": "phandalin",
        },
    }


@pytest.fixture
def temp_npc_file(sample_npc_data):
    """Create a temporary NPC data file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_npc_data, f)
        path = Path(f.name)
    yield str(path)
    if path.exists():
        path.unlink()


class TestLoadNpcData:
    """Tests for loading NPC data."""

    def test_load_from_default_path(self):
        """Should load NPCs from default data file."""
        data = load_npc_data()
        # The actual npcs.json should have at least these NPCs
        assert "gundren_rockseeker" in data
        assert "sildar_hallwinter" in data
        assert "klarg" in data

    def test_load_from_custom_path(self, temp_npc_file, sample_npc_data):
        """Should load NPCs from custom path."""
        data = load_npc_data(temp_npc_file)
        assert data == sample_npc_data

    def test_load_nonexistent_file(self):
        """Should return empty dict for nonexistent file."""
        data = load_npc_data("/nonexistent/path.json")
        assert data == {}


class TestGetNpc:
    """Tests for getting individual NPCs."""

    def test_get_existing_npc(self, sample_npc_data):
        """Should return NPC data for valid ID."""
        npc = get_npc("gundren_rockseeker", sample_npc_data)
        assert npc is not None
        assert npc["name"] == "Gundren Rockseeker"

    def test_get_nonexistent_npc(self, sample_npc_data):
        """Should return None for invalid ID."""
        npc = get_npc("nonexistent", sample_npc_data)
        assert npc is None


class TestFormatNpcPrompt:
    """Tests for NPC prompt formatting."""

    def test_format_basic_prompt(self, sample_npc_data):
        """Should format prompt with all required tags."""
        prompt = format_npc_prompt(
            npc_id="gundren_rockseeker",
            context="Just rescued from goblins",
            scene="Party asking questions",
            player_action="Fighter: 'Are you okay?'",
            npc_data=sample_npc_data,
        )

        assert "[PLAY AS: Gundren Rockseeker]" in prompt
        assert "[PERSONALITY:" in prompt
        assert "[CONTEXT: Just rescued from goblins]" in prompt
        assert "[SCENE: Party asking questions]" in prompt
        assert "Fighter: 'Are you okay?'" in prompt

    def test_format_includes_personality(self, sample_npc_data):
        """Should include NPC personality in prompt."""
        prompt = format_npc_prompt(
            npc_id="gundren_rockseeker",
            context="test",
            scene="test",
            player_action="test",
            npc_data=sample_npc_data,
        )

        assert "Gruff but kind" in prompt
        assert "Dwarven accent" in prompt

    def test_format_nonexistent_npc_raises(self, sample_npc_data):
        """Should raise KeyError for unknown NPC."""
        with pytest.raises(KeyError, match="NPC not found"):
            format_npc_prompt(
                npc_id="nonexistent",
                context="test",
                scene="test",
                player_action="test",
                npc_data=sample_npc_data,
            )


class TestFormatNpcPromptCustom:
    """Tests for custom NPC prompt formatting."""

    def test_format_custom_prompt(self):
        """Should format prompt with custom personality."""
        prompt = format_npc_prompt_custom(
            name="Random Villager",
            personality="Nervous, stutters when scared",
            context="Goblins attacked the village",
            scene="Party arrived to help",
            player_action="Rogue: 'What happened here?'",
        )

        assert "[PLAY AS: Random Villager]" in prompt
        assert "[PERSONALITY: Nervous, stutters when scared]" in prompt
        assert "[CONTEXT: Goblins attacked the village]" in prompt
        assert "[SCENE: Party arrived to help]" in prompt
        assert "Rogue: 'What happened here?'" in prompt


class TestGetNpcNames:
    """Tests for getting NPC names."""

    def test_get_all_names(self, sample_npc_data):
        """Should return all NPC display names."""
        names = get_npc_names(sample_npc_data)
        assert "Gundren Rockseeker" in names
        assert "Sildar Hallwinter" in names
        assert "Klarg" in names
        assert len(names) == 4


class TestGetNpcsAtLocation:
    """Tests for location-based NPC queries."""

    def test_get_npcs_at_hideout(self, sample_npc_data):
        """Should return NPCs at Cragmaw Hideout."""
        npcs = get_npcs_at_location("cragmaw_hideout", sample_npc_data)
        names = [n["name"] for n in npcs]
        assert "Sildar Hallwinter" in names
        assert "Klarg" in names
        assert len(npcs) == 2

    def test_get_npcs_at_castle(self, sample_npc_data):
        """Should return NPCs at Cragmaw Castle."""
        npcs = get_npcs_at_location("cragmaw_castle", sample_npc_data)
        names = [n["name"] for n in npcs]
        assert "Gundren Rockseeker" in names
        assert len(npcs) == 1

    def test_get_npcs_at_empty_location(self, sample_npc_data):
        """Should return empty list for location with no NPCs."""
        npcs = get_npcs_at_location("nonexistent_location", sample_npc_data)
        assert npcs == []

    def test_includes_npc_id(self, sample_npc_data):
        """Should include NPC ID in returned data."""
        npcs = get_npcs_at_location("cragmaw_castle", sample_npc_data)
        assert npcs[0]["id"] == "gundren_rockseeker"


class TestGetAliveNpcs:
    """Tests for getting alive NPCs."""

    def test_excludes_dead_npcs(self, sample_npc_data):
        """Should exclude dead NPCs."""
        alive = get_alive_npcs(sample_npc_data)
        names = [n["name"] for n in alive]
        assert "Dead NPC" not in names
        assert len(alive) == 3

    def test_includes_captured_npcs(self, sample_npc_data):
        """Captured NPCs should be considered alive."""
        alive = get_alive_npcs(sample_npc_data)
        names = [n["name"] for n in alive]
        assert "Gundren Rockseeker" in names
        assert "Sildar Hallwinter" in names


class TestNPCAdapter:
    """Tests for NPCAdapter class."""

    def test_adapter_has_system_prompt(self):
        """NPCAdapter should have NPC system prompt."""
        adapter = NPCAdapter()
        # The system_prompt is stored in the parent class
        assert adapter.system_prompt == NPC_SYSTEM_PROMPT

    def test_adapter_uses_correct_model(self):
        """Should use Claude Sonnet by default."""
        adapter = NPCAdapter()
        assert "claude" in adapter.model.lower()
        assert "sonnet" in adapter.model.lower()

    def test_adapter_enables_reporting(self):
        """Should have execution reporting enabled."""
        adapter = NPCAdapter()
        assert adapter.enable_execution_reporting is True


class TestNPCSystemPrompt:
    """Tests for NPC system prompt content."""

    def test_prompt_has_instruction_format(self):
        """Should explain the DM instruction format."""
        assert "[PLAY AS:" in NPC_SYSTEM_PROMPT
        assert "[PERSONALITY:" in NPC_SYSTEM_PROMPT
        assert "[CONTEXT:" in NPC_SYSTEM_PROMPT
        assert "[SCENE:" in NPC_SYSTEM_PROMPT

    def test_prompt_has_response_guidelines(self):
        """Should include response guidelines."""
        assert "Stay in Character" in NPC_SYSTEM_PROMPT
        assert "Concise" in NPC_SYSTEM_PROMPT

    def test_prompt_has_example(self):
        """Should include example interaction."""
        assert "Gundren" in NPC_SYSTEM_PROMPT
        assert "aye" in NPC_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_send_message(self):
        """Should mention using send_message tool."""
        assert "send_message" in NPC_SYSTEM_PROMPT

    def test_prompt_has_voice_guidance(self):
        """Should have guidance for different character voices."""
        assert "Dwarves" in NPC_SYSTEM_PROMPT
        assert "Goblins" in NPC_SYSTEM_PROMPT
        assert "Bugbears" in NPC_SYSTEM_PROMPT


class TestNPCDataFile:
    """Tests for the actual npcs.json data file."""

    def test_actual_data_file_exists(self):
        """The npcs.json file should exist."""
        data = load_npc_data()
        assert len(data) > 0

    def test_gundren_has_required_fields(self):
        """Gundren should have all required fields."""
        data = load_npc_data()
        gundren = data.get("gundren_rockseeker", {})

        assert "name" in gundren
        assert "race" in gundren
        assert "personality" in gundren
        assert "knowledge" in gundren
        assert "goals" in gundren

    def test_klarg_is_bugbear(self):
        """Klarg should be a bugbear."""
        data = load_npc_data()
        klarg = data.get("klarg", {})
        assert klarg.get("race") == "Bugbear"

    def test_all_npcs_have_personality(self):
        """Every NPC should have a personality defined."""
        data = load_npc_data()
        for npc_id, npc in data.items():
            assert "personality" in npc, f"{npc_id} missing personality"
            assert len(npc["personality"]) > 10, f"{npc_id} personality too short"
