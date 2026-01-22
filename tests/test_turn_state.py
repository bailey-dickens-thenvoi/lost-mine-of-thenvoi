"""Tests for Turn State System.

These tests verify the turn state gating logic that prevents
agent response cascades.
"""

import pytest
import time

from src.game.models import TurnState, WorldState
from src.game.tags import (
    ParsedMessage,
    parse_message_tag,
    strip_tags_for_display,
    create_tagged_message,
    is_turn_tag,
    get_turn_target,
    is_narration,
    is_prompt,
    is_combat_result,
)


class TestTurnState:
    """Tests for TurnState model."""

    def test_default_state(self):
        """Default state should have no active agent."""
        state = TurnState()
        assert state.active_agent is None
        assert state.mode == "dm_control"
        assert state.addressed_agents == []
        assert state.turn_started_at is None

    def test_is_agent_turn_direct_match(self):
        """Should return True when active_agent matches."""
        state = TurnState(active_agent="thokk", mode="combat")
        assert state.is_agent_turn("thokk") is True
        assert state.is_agent_turn("lira") is False
        assert state.is_agent_turn("npc") is False

    def test_is_agent_turn_free_form_mode(self):
        """Should return True in free_form mode when agent is addressed."""
        state = TurnState(
            active_agent=None,
            mode="free_form",
            addressed_agents=["thokk", "lira"],
        )
        assert state.is_agent_turn("thokk") is True
        assert state.is_agent_turn("lira") is True
        assert state.is_agent_turn("npc") is False

    def test_is_agent_turn_no_match(self):
        """Should return False when not the agent's turn."""
        state = TurnState(active_agent="lira", mode="combat")
        assert state.is_agent_turn("thokk") is False
        assert state.is_agent_turn("npc") is False

    def test_is_agent_turn_dm_control(self):
        """Should return False in dm_control mode."""
        state = TurnState(active_agent=None, mode="dm_control")
        assert state.is_agent_turn("thokk") is False
        assert state.is_agent_turn("lira") is False
        assert state.is_agent_turn("npc") is False

    def test_is_human_turn(self):
        """Should correctly identify human's turn."""
        state = TurnState(active_agent="human", mode="exploration")
        assert state.is_human_turn() is True

        state = TurnState(active_agent="thokk", mode="combat")
        assert state.is_human_turn() is False

        state = TurnState(active_agent=None, mode="dm_control")
        assert state.is_human_turn() is False


class TestWorldStateWithTurnState:
    """Tests for TurnState integration with WorldState."""

    def test_world_state_has_turn_state(self):
        """WorldState should include turn_state field."""
        world = WorldState()
        assert hasattr(world, "turn_state")
        assert isinstance(world.turn_state, TurnState)

    def test_world_state_turn_state_default(self):
        """WorldState turn_state should have sensible defaults."""
        world = WorldState()
        assert world.turn_state.active_agent is None
        assert world.turn_state.mode == "dm_control"

    def test_world_state_turn_state_modification(self):
        """Should be able to modify turn_state."""
        world = WorldState()
        world.turn_state.active_agent = "thokk"
        world.turn_state.mode = "combat"
        world.turn_state.turn_started_at = time.time()

        assert world.turn_state.active_agent == "thokk"
        assert world.turn_state.mode == "combat"
        assert world.turn_state.turn_started_at is not None

    def test_world_state_serialization(self):
        """TurnState should serialize with WorldState."""
        world = WorldState()
        world.turn_state.active_agent = "lira"
        world.turn_state.mode = "exploration"
        world.turn_state.addressed_agents = ["thokk", "npc"]

        data = world.model_dump()
        assert "turn_state" in data
        assert data["turn_state"]["active_agent"] == "lira"
        assert data["turn_state"]["mode"] == "exploration"
        assert data["turn_state"]["addressed_agents"] == ["thokk", "npc"]

    def test_world_state_deserialization(self):
        """TurnState should deserialize with WorldState."""
        data = {
            "turn_state": {
                "active_agent": "npc",
                "mode": "free_form",
                "addressed_agents": ["thokk"],
                "turn_started_at": 1234567890.0,
            }
        }
        world = WorldState.model_validate(data)
        assert world.turn_state.active_agent == "npc"
        assert world.turn_state.mode == "free_form"
        assert world.turn_state.addressed_agents == ["thokk"]
        assert world.turn_state.turn_started_at == 1234567890.0


class TestTagParsing:
    """Tests for message tag parsing utilities."""

    def test_parse_tag_with_value(self):
        """Should parse tags with values."""
        result = parse_message_tag("[TURN:thokk] Your turn!")
        assert result.tag == "TURN"
        assert result.tag_value == "thokk"
        assert result.content == "Your turn!"

    def test_parse_tag_without_value(self):
        """Should parse tags without values."""
        result = parse_message_tag("[NARRATION] The cave grows dark.")
        assert result.tag == "NARRATION"
        assert result.tag_value is None
        assert result.content == "The cave grows dark."

    def test_parse_no_tag(self):
        """Should handle messages without tags."""
        result = parse_message_tag("Just a normal message")
        assert result.tag is None
        assert result.tag_value is None
        assert result.content == "Just a normal message"

    def test_parse_combat_tag(self):
        """Should parse combat result tags."""
        result = parse_message_tag("[COMBAT:hit] The sword strikes true!")
        assert result.tag == "COMBAT"
        assert result.tag_value == "hit"
        assert result.content == "The sword strikes true!"

    def test_parse_multiline_content(self):
        """Should preserve multiline content."""
        message = "[NARRATION] Line 1\nLine 2\nLine 3"
        result = parse_message_tag(message)
        assert result.tag == "NARRATION"
        assert "Line 1" in result.content
        assert "Line 2" in result.content
        assert "Line 3" in result.content


class TestTagStripping:
    """Tests for tag stripping."""

    def test_strip_tag_with_value(self):
        """Should strip tags with values."""
        result = strip_tags_for_display("[TURN:thokk] Your turn!")
        assert result == "Your turn!"

    def test_strip_tag_without_value(self):
        """Should strip tags without values."""
        result = strip_tags_for_display("[NARRATION] Description here")
        assert result == "Description here"

    def test_strip_no_tag(self):
        """Should return original message if no tag."""
        result = strip_tags_for_display("No tag message")
        assert result == "No tag message"


class TestTagCreation:
    """Tests for creating tagged messages."""

    def test_create_tag_with_value(self):
        """Should create tag with value."""
        result = create_tagged_message("TURN", "Your turn!", "thokk")
        assert result == "[TURN:thokk] Your turn!"

    def test_create_tag_without_value(self):
        """Should create tag without value."""
        result = create_tagged_message("NARRATION", "The cave grows dark.")
        assert result == "[NARRATION] The cave grows dark."


class TestTagHelpers:
    """Tests for tag helper functions."""

    def test_is_turn_tag(self):
        """Should identify TURN tags."""
        assert is_turn_tag("[TURN:thokk] Your turn!") is True
        assert is_turn_tag("[NARRATION] Description") is False
        assert is_turn_tag("No tag") is False

    def test_get_turn_target(self):
        """Should extract turn target."""
        assert get_turn_target("[TURN:thokk] Your turn!") == "thokk"
        assert get_turn_target("[TURN:lira] Lira's turn!") == "lira"
        assert get_turn_target("[NARRATION] Not a turn") is None
        assert get_turn_target("No tag") is None

    def test_is_narration(self):
        """Should identify narration tags."""
        assert is_narration("[NARRATION] The cave grows dark.") is True
        assert is_narration("[TURN:thokk] Your turn!") is False
        assert is_narration("No tag") is False

    def test_is_prompt(self):
        """Should identify prompt tags."""
        assert is_prompt("[PROMPT] What do you do?") is True
        assert is_prompt("[NARRATION] Description") is False
        assert is_prompt("No tag") is False

    def test_is_combat_result(self):
        """Should identify combat result tags."""
        is_combat, result_type = is_combat_result("[COMBAT:hit] Strike!")
        assert is_combat is True
        assert result_type == "hit"

        is_combat, result_type = is_combat_result("[COMBAT:miss] Missed!")
        assert is_combat is True
        assert result_type == "miss"

        is_combat, result_type = is_combat_result("[NARRATION] Not combat")
        assert is_combat is False
        assert result_type is None


class TestShouldRespondLogic:
    """Tests for should_respond logic patterns."""

    def test_ai_player_should_respond_on_turn(self):
        """AI player should respond when it's their turn."""
        turn_state = TurnState(active_agent="thokk", mode="combat")

        # Simulate the should_respond logic from AIPlayerAdapter
        agent_id = "thokk"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is True

    def test_ai_player_should_not_respond_on_other_turn(self):
        """AI player should not respond when it's another agent's turn."""
        turn_state = TurnState(active_agent="lira", mode="combat")

        agent_id = "thokk"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is False

    def test_ai_player_should_not_respond_on_human_turn(self):
        """AI player should not respond when it's human's turn."""
        turn_state = TurnState(active_agent="human", mode="exploration")

        agent_id = "thokk"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is False

    def test_ai_player_should_respond_in_free_form(self):
        """AI player should respond in free_form when addressed."""
        turn_state = TurnState(
            active_agent=None,
            mode="free_form",
            addressed_agents=["thokk", "lira"],
        )

        agent_id = "thokk"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is True

    def test_npc_should_respond_on_turn(self):
        """NPC should respond when it's their turn."""
        turn_state = TurnState(active_agent="npc", mode="exploration")

        agent_id = "npc"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is True

    def test_npc_should_not_respond_on_player_turn(self):
        """NPC should not respond on player turn."""
        turn_state = TurnState(active_agent="thokk", mode="combat")

        agent_id = "npc"
        should_respond = (
            not turn_state.is_human_turn()
            and turn_state.is_agent_turn(agent_id)
        )
        assert should_respond is False


class TestModeScenarios:
    """Tests for different mode scenarios."""

    def test_dm_control_mode(self):
        """In dm_control mode, no agent should respond."""
        turn_state = TurnState(active_agent=None, mode="dm_control")

        for agent_id in ["thokk", "lira", "npc"]:
            assert turn_state.is_agent_turn(agent_id) is False

    def test_combat_mode_strict_turns(self):
        """In combat mode, only active_agent should respond."""
        turn_state = TurnState(active_agent="thokk", mode="combat")

        assert turn_state.is_agent_turn("thokk") is True
        assert turn_state.is_agent_turn("lira") is False
        assert turn_state.is_agent_turn("npc") is False

    def test_exploration_mode(self):
        """In exploration mode, active_agent should respond."""
        turn_state = TurnState(active_agent="human", mode="exploration")

        assert turn_state.is_human_turn() is True
        assert turn_state.is_agent_turn("thokk") is False

    def test_free_form_multiple_responders(self):
        """In free_form mode, multiple agents can respond."""
        turn_state = TurnState(
            active_agent=None,
            mode="free_form",
            addressed_agents=["thokk", "lira"],
        )

        assert turn_state.is_agent_turn("thokk") is True
        assert turn_state.is_agent_turn("lira") is True
        assert turn_state.is_agent_turn("npc") is False
