"""Tests for the DM Agent."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.dm_agent import DMAdapter, DM_SYSTEM_PROMPT
from src.tools.world_state import WorldStateManager, reset_world_state_manager


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state manager before each test."""
    reset_world_state_manager()
    yield
    reset_world_state_manager()


@pytest.fixture
def temp_state_file():
    """Create a unique temporary state file path for testing."""
    # Create a temp directory and generate unique filename
    import uuid
    temp_dir = tempfile.gettempdir()
    path = Path(temp_dir) / f"test_state_{uuid.uuid4()}.json"
    yield str(path)
    if path.exists():
        path.unlink()


@pytest.fixture
def state_manager(temp_state_file):
    """Create a WorldStateManager with temp file."""
    return WorldStateManager(temp_state_file, auto_save=True)


@pytest.fixture
def dm_adapter(state_manager):
    """Create a DMAdapter for testing."""
    return DMAdapter(state_manager=state_manager)


class TestDMAdapterInit:
    """Tests for DMAdapter initialization."""

    def test_creates_with_state_manager(self, state_manager):
        """Should initialize with provided state manager."""
        adapter = DMAdapter(state_manager=state_manager)
        assert adapter.state_manager is state_manager

    def test_creates_default_state_manager(self, temp_state_file):
        """Should create default state manager if not provided."""
        # Reset the global manager first
        reset_world_state_manager()
        with patch("src.agents.dm_agent.get_world_state_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.state = MagicMock()
            mock_manager.state.current_chapter = 1
            mock_manager.state.current_scene = "intro"
            mock_manager.state.combat = MagicMock()
            mock_manager.state.combat.active = False
            mock_manager.state.characters = {}
            mock_manager.state.narrative_progress = MagicMock()
            mock_manager.state.narrative_progress.ambush_triggered = False
            mock_manager.state.narrative_progress.goblins_defeated = False
            mock_manager.state.narrative_progress.goblin_trail_found = False
            mock_manager.state.narrative_progress.sildar_rescued = False
            mock_get.return_value = mock_manager

            adapter = DMAdapter()
            mock_get.assert_called_once()

    def test_has_custom_tools(self, dm_adapter):
        """Should have roll_dice and world_state tools."""
        tool_names = [t["name"] for t in dm_adapter._custom_tools]
        assert "roll_dice" in tool_names
        assert "world_state" in tool_names

    def test_roll_dice_tool_schema(self, dm_adapter):
        """roll_dice tool should have correct schema."""
        roll_tool = next(t for t in dm_adapter._custom_tools if t["name"] == "roll_dice")

        assert "input_schema" in roll_tool
        schema = roll_tool["input_schema"]
        assert schema["type"] == "object"
        assert "notation" in schema["properties"]
        assert "purpose" in schema["properties"]
        assert "roller" in schema["properties"]
        assert "advantage" in schema["properties"]
        assert "disadvantage" in schema["properties"]
        assert schema["required"] == ["notation", "purpose", "roller"]

    def test_world_state_tool_schema(self, dm_adapter):
        """world_state tool should have correct schema."""
        ws_tool = next(t for t in dm_adapter._custom_tools if t["name"] == "world_state")

        assert "input_schema" in ws_tool
        schema = ws_tool["input_schema"]
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert schema["required"] == ["operation"]


class TestDMStateSummary:
    """Tests for state summary generation."""

    def test_builds_state_summary(self, dm_adapter):
        """Should build a readable state summary."""
        summary = dm_adapter._build_state_summary()

        assert "Chapter:" in summary
        assert "Scene:" in summary
        assert "Combat:" in summary
        assert "Party Status:" in summary

    def test_state_summary_includes_characters(self, state_manager):
        """Should include character info in summary."""
        # Load default state which has characters
        state_manager.load()
        adapter = DMAdapter(state_manager=state_manager)
        summary = adapter._build_state_summary()

        assert "Vex" in summary
        assert "Thokk" in summary
        assert "Lira" in summary


class TestDMToolExecution:
    """Tests for custom tool execution."""

    def test_execute_roll_dice(self, dm_adapter):
        """Should execute roll_dice and return formatted result."""
        result = dm_adapter._execute_roll_dice({
            "notation": "1d20+5",
            "purpose": "Attack Roll",
            "roller": "Vex",
        })

        assert "Attack Roll" in result
        assert "Vex" in result
        assert "=" in result  # Has total

    def test_execute_roll_dice_with_advantage(self, dm_adapter):
        """Should handle advantage parameter."""
        result = dm_adapter._execute_roll_dice({
            "notation": "1d20+5",
            "purpose": "Stealth Check",
            "roller": "Vex",
            "advantage": True,
        })

        assert "(advantage)" in result
        assert "(took" in result  # Shows which roll was kept

    def test_execute_world_state_get(self, temp_state_file):
        """Should execute world_state get operation."""
        manager = WorldStateManager(temp_state_file, auto_save=True)
        adapter = DMAdapter(state_manager=manager)

        result = adapter._execute_world_state({
            "operation": "get",
            "path": "current_scene",
        })

        assert "current_scene" in result
        assert "intro" in result

    def test_execute_world_state_set(self, temp_state_file):
        """Should execute world_state set operation."""
        manager = WorldStateManager(temp_state_file, auto_save=True)
        adapter = DMAdapter(state_manager=manager)

        result = adapter._execute_world_state({
            "operation": "set",
            "path": "current_scene",
            "value": "goblin_ambush",
        })

        assert "Set" in result
        assert "goblin_ambush" in result

        # Verify it was actually set
        get_result = adapter._execute_world_state({
            "operation": "get",
            "path": "current_scene",
        })
        assert "goblin_ambush" in get_result

    def test_execute_world_state_update_hp(self, temp_state_file):
        """Should execute HP update operation."""
        manager = WorldStateManager(temp_state_file, auto_save=True)
        adapter = DMAdapter(state_manager=manager)

        result = adapter._execute_world_state({
            "operation": "update_hp",
            "entity_id": "human_player",
            "delta": -3,
        })

        assert "human_player HP" in result
        assert "9 -> 6" in result

    def test_execute_world_state_get_party_status(self, dm_adapter):
        """Should get party status."""
        result = dm_adapter._execute_world_state({
            "operation": "get_party_status",
        })

        assert "Party Status" in result
        assert "Vex" in result
        assert "Thokk" in result
        assert "Lira" in result


class TestDMSystemPrompt:
    """Tests for system prompt content."""

    def test_system_prompt_has_role_section(self):
        """System prompt should describe DM role."""
        assert "Dungeon Master" in DM_SYSTEM_PROMPT
        assert "Lost Mines of Phandelver" in DM_SYSTEM_PROMPT

    def test_system_prompt_has_tool_docs(self):
        """System prompt should document custom tools."""
        assert "roll_dice" in DM_SYSTEM_PROMPT
        assert "world_state" in DM_SYSTEM_PROMPT

    def test_system_prompt_has_combat_flow(self):
        """System prompt should describe combat flow."""
        assert "Combat Flow" in DM_SYSTEM_PROMPT
        assert "initiative" in DM_SYSTEM_PROMPT.lower()

    def test_system_prompt_has_party_info(self):
        """System prompt should list party members."""
        assert "Vex" in DM_SYSTEM_PROMPT
        assert "Thokk" in DM_SYSTEM_PROMPT
        assert "Lira" in DM_SYSTEM_PROMPT

    def test_system_prompt_has_state_placeholder(self):
        """System prompt should have state summary placeholder."""
        assert "{state_summary}" in DM_SYSTEM_PROMPT


class TestDMCustomToolSchemas:
    """Tests for custom tool schema structure."""

    def test_tool_schemas_are_anthropic_format(self, dm_adapter):
        """Tool schemas should match Anthropic format."""
        for tool in dm_adapter._custom_tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_roll_dice_has_all_params(self, dm_adapter):
        """roll_dice should have all expected parameters."""
        roll_tool = next(t for t in dm_adapter._custom_tools if t["name"] == "roll_dice")
        props = roll_tool["input_schema"]["properties"]

        assert "notation" in props
        assert props["notation"]["type"] == "string"

        assert "purpose" in props
        assert props["purpose"]["type"] == "string"

        assert "roller" in props
        assert props["roller"]["type"] == "string"

        assert "advantage" in props
        assert props["advantage"]["type"] == "boolean"

        assert "disadvantage" in props
        assert props["disadvantage"]["type"] == "boolean"

    def test_world_state_has_all_operations(self, dm_adapter):
        """world_state should list all valid operations."""
        ws_tool = next(t for t in dm_adapter._custom_tools if t["name"] == "world_state")
        ops = ws_tool["input_schema"]["properties"]["operation"]["enum"]

        assert "get" in ops
        assert "set" in ops
        assert "update_hp" in ops
        assert "save" in ops
        assert "get_party_status" in ops
        assert "get_living_enemies" in ops
