"""Integration tests for the Lost Mine of Thenvoi multi-agent system.

These tests verify that all system components work together correctly:
- Mock platform message routing
- Agent coordination
- Combat flow
- Scene transitions
- NPC invocation
"""

import pytest
import asyncio

from src.testing.mock_platform import MockThenvoiPlatform, MockMessage
from src.testing.fake_tools import FakeAgentTools
from src.testing.harness import AgentTestHarness


class TestMockPlatform:
    """Tests for the mock platform."""

    @pytest.fixture
    def platform(self):
        """Create a mock platform."""
        return MockThenvoiPlatform()

    @pytest.mark.asyncio
    async def test_send_message(self, platform):
        """Should record sent messages."""
        msg = await platform.send_message("Player", "Hello!", ["DM Agent"])
        assert msg.sender == "Player"
        assert msg.content == "Hello!"
        assert "DM Agent" in msg.mentions

    @pytest.mark.asyncio
    async def test_message_dispatch(self, platform):
        """Should dispatch messages to mentioned agents."""
        received = []

        async def handler(msg: MockMessage):
            received.append(msg)

        platform.register_agent("TestAgent", handler)
        await platform.send_message("Player", "Hello!", ["TestAgent"])

        assert len(received) == 1
        assert received[0].content == "Hello!"

    @pytest.mark.asyncio
    async def test_no_dispatch_without_mention(self, platform):
        """Should not dispatch to agents not mentioned."""
        received = []

        async def handler(msg: MockMessage):
            received.append(msg)

        platform.register_agent("TestAgent", handler)
        await platform.send_message("Player", "Hello!", ["OtherAgent"])

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_conversation_log(self, platform):
        """Should maintain conversation log."""
        await platform.send_message("Player1", "Hello", [])
        await platform.send_message("Player2", "Hi there", [])
        await platform.send_message("Player1", "How are you?", [])

        log = platform.get_conversation_log()
        assert len(log) == 3
        assert log[0]["sender"] == "Player1"
        assert log[1]["sender"] == "Player2"
        assert log[2]["sender"] == "Player1"

    def test_get_messages_from(self, platform):
        """Should filter messages by sender."""
        asyncio.run(platform.send_message("Alice", "From Alice", []))
        asyncio.run(platform.send_message("Bob", "From Bob", []))
        asyncio.run(platform.send_message("Alice", "Also Alice", []))

        alice_msgs = platform.get_messages_from("Alice")
        assert len(alice_msgs) == 2

    def test_register_unregister_agent(self, platform):
        """Should register and unregister agents."""
        async def handler(msg):
            pass

        platform.register_agent("TestAgent", handler)
        assert "TestAgent" in platform.agents

        result = platform.unregister_agent("TestAgent")
        assert result is True
        assert "TestAgent" not in platform.agents

    def test_get_participants(self, platform):
        """Should track participants."""
        async def handler(msg):
            pass

        platform.register_agent("Agent1", handler)
        platform.add_participant("Player", "member")

        participants = platform.get_participants()
        names = [p["name"] for p in participants]
        assert "Agent1" in names
        assert "Player" in names


class TestFakeAgentTools:
    """Tests for fake agent tools."""

    @pytest.fixture
    def tools(self):
        """Create fake tools."""
        return FakeAgentTools()

    @pytest.mark.asyncio
    async def test_send_message(self, tools):
        """Should record sent messages."""
        await tools.send_message("Hello!", ["Player"])

        assert len(tools.sent_messages) == 1
        assert tools.sent_messages[0].content == "Hello!"
        assert "Player" in tools.sent_messages[0].mentions

    @pytest.mark.asyncio
    async def test_send_event(self, tools):
        """Should record sent events."""
        await tools.send_event("Thinking...", "thought")

        assert len(tools.sent_events) == 1
        assert tools.sent_events[0].content == "Thinking..."
        assert tools.sent_events[0].message_type == "thought"

    @pytest.mark.asyncio
    async def test_get_participants(self, tools):
        """Should return participants."""
        participants = await tools.get_participants()
        assert len(participants) >= 2  # Default participants

    @pytest.mark.asyncio
    async def test_add_participant(self, tools):
        """Should record adding participant."""
        await tools.add_participant("NewAgent", "member")

        assert len(tools.added_participants) == 1
        assert tools.added_participants[0]["name"] == "NewAgent"

    @pytest.mark.asyncio
    async def test_execute_tool_call(self, tools):
        """Should record tool calls."""
        await tools.execute_tool_call("send_message", {
            "content": "Test",
            "mentions": ["DM"]
        })

        assert len(tools.tool_calls) == 1
        assert tools.tool_calls[0]["name"] == "send_message"

    def test_get_anthropic_tool_schemas(self, tools):
        """Should return tool schemas."""
        schemas = tools.get_anthropic_tool_schemas()
        assert len(schemas) >= 3  # send_message, send_event, get_participants

    def test_clear(self, tools):
        """Should clear all records."""
        asyncio.run(tools.send_message("Test", []))
        asyncio.run(tools.send_event("Event", "thought"))

        tools.clear()

        assert len(tools.sent_messages) == 0
        assert len(tools.sent_events) == 0


class TestAgentTestHarness:
    """Tests for the agent test harness."""

    @pytest.fixture
    def harness(self):
        """Create a test harness."""
        h = AgentTestHarness()
        yield h
        h.cleanup()

    def test_setup_state(self, harness):
        """Should initialize game state."""
        harness.setup_state()
        state = harness.state_manager.state
        assert state.current_scene == "intro"
        assert state.current_chapter == 1

    def test_setup_dm(self, harness):
        """Should set up DM agent."""
        tools = harness.setup_dm()
        assert tools is not None
        assert "DM Agent" in harness.platform.agents

    def test_setup_all_agents(self, harness):
        """Should set up all agents."""
        agents = harness.setup_all_agents()
        assert "dm" in agents
        assert "npc" in agents
        assert "thokk" in agents
        assert "lira" in agents
        assert "DM Agent" in harness.platform.agents
        assert "NPC Agent" in harness.platform.agents
        assert "Thokk" in harness.platform.agents
        assert "Lira" in harness.platform.agents

    @pytest.mark.asyncio
    async def test_simulate_human_action(self, harness):
        """Should send human player message."""
        harness.setup_all_agents()
        msg = await harness.simulate_human_action("I search the room")

        assert msg.sender == "Human Player"
        assert msg.content == "I search the room"
        assert "DM Agent" in msg.mentions

    @pytest.mark.asyncio
    async def test_dm_narrates(self, harness):
        """Should send DM narration."""
        harness.setup_all_agents()
        msg = await harness.dm_narrates("You enter a dark cave.")

        assert msg.sender == "DM Agent"
        assert "cave" in msg.content.lower()

    @pytest.mark.asyncio
    async def test_dm_prompts_turn(self, harness):
        """Should prompt character turn."""
        harness.setup_all_agents()
        msg = await harness.dm_prompts_turn("Thokk", "A goblin is nearby!")

        assert msg.sender == "DM Agent"
        assert "Thokk" in msg.content
        assert "Thokk" in msg.mentions

    @pytest.mark.asyncio
    async def test_invoke_npc(self, harness):
        """Should invoke NPC with context."""
        harness.setup_all_agents()
        msg = await harness.invoke_npc(
            character_name="Gundren Rockseeker",
            personality="Gruff dwarf merchant",
            context="Just rescued from goblins",
            scene="Cave exit",
            player_dialogue="Party: 'Are you alright?'"
        )

        assert msg.sender == "DM Agent"
        assert "PLAY AS: Gundren" in msg.content
        assert "PERSONALITY" in msg.content
        assert "NPC Agent" in msg.mentions

    def test_get_conversation_log(self, harness):
        """Should return conversation log."""
        harness.setup_all_agents()
        asyncio.run(harness.simulate_human_action("Test"))

        log = harness.get_conversation_log()
        assert len(log) >= 1

    def test_get_current_scene(self, harness):
        """Should get current scene."""
        harness.setup_state()
        scene = harness.get_current_scene()
        assert scene["name"] == "The Road to Phandalin"

    def test_transition_to_scene(self, harness):
        """Should transition scenes."""
        harness.setup_state()
        result = harness.transition_to_scene("goblin_ambush")
        assert result is True
        assert harness.state_manager.get("current_scene") == "goblin_ambush"


class TestCombatIntegration:
    """Integration tests for combat flow."""

    @pytest.fixture
    def harness(self):
        """Create a test harness."""
        h = AgentTestHarness()
        h.setup_all_agents()
        yield h
        h.cleanup()

    def test_start_combat(self, harness):
        """Should initialize combat with enemies."""
        harness.start_combat(["goblin_1", "goblin_2"])

        assert harness.state_manager.get("combat.active") is True
        enemies = harness.get_living_enemies()
        assert len(enemies) == 2

    def test_damage_enemy(self, harness):
        """Should damage enemies."""
        harness.start_combat(["goblin_1"])
        new_hp = harness.damage_entity("goblin_1", 5)
        assert new_hp == 2  # 7 - 5

    def test_kill_enemy(self, harness):
        """Should kill enemy when HP reaches 0."""
        harness.start_combat(["goblin_1"])
        new_hp = harness.damage_entity("goblin_1", 10)
        assert new_hp == 0

        enemies = harness.get_living_enemies()
        assert "goblin_1" not in enemies

    def test_heal_character(self, harness):
        """Should heal characters."""
        # Damage first
        harness.damage_entity("human_player", 5)
        party = harness.get_party_status()
        assert party["human_player"]["hp"] == 4

        # Then heal
        harness.heal_entity("human_player", 3)
        party = harness.get_party_status()
        assert party["human_player"]["hp"] == 7

    def test_end_combat(self, harness):
        """Should end combat."""
        harness.start_combat(["goblin_1"])
        harness.end_combat()

        assert harness.state_manager.get("combat.active") is False


class TestSceneIntegration:
    """Integration tests for scene flow."""

    @pytest.fixture
    def harness(self):
        """Create a test harness."""
        h = AgentTestHarness()
        h.setup_all_agents()
        yield h
        h.cleanup()

    @pytest.mark.asyncio
    async def test_intro_scene_flow(self, harness):
        """Test the intro scene flow."""
        # Start at intro
        scene = harness.get_current_scene()
        assert scene["name"] == "The Road to Phandalin"

        # DM describes scene
        await harness.dm_narrates(scene["description"][:200])

        # Player investigates
        await harness.simulate_human_action("I investigate the dead horses")

        log = harness.get_conversation_log()
        assert len(log) >= 2

    @pytest.mark.asyncio
    async def test_combat_scene_flow(self, harness):
        """Test transitioning to and running combat."""
        # Transition to combat
        harness.transition_to_scene("goblin_ambush")
        harness.start_combat(["goblin_1", "goblin_2", "goblin_3", "goblin_4"])

        # DM announces combat
        await harness.dm_narrates("Roll for initiative! Goblins attack!")

        # Prompt turns
        await harness.dm_prompts_turn("Thokk", "Two goblins are 30 feet away!")
        await harness.dm_prompts_turn("Human Player", "Your turn!")
        await harness.simulate_human_action("I attack goblin_1 with my shortsword")

        log = harness.get_conversation_log()
        assert len(log) >= 4

    @pytest.mark.asyncio
    async def test_npc_scene_flow(self, harness):
        """Test NPC interaction flow."""
        # Set up rescue scene
        harness.transition_to_scene("sildar_rescue")

        # DM describes scene
        scene = harness.get_current_scene()
        await harness.dm_narrates("You find a wounded man...")

        # Invoke NPC
        await harness.invoke_npc(
            character_name="Sildar Hallwinter",
            personality="Noble warrior, grateful",
            context="Just rescued from goblins",
            scene="Cragmaw Hideout",
            player_dialogue="The party asks: 'What happened?'"
        )

        log = harness.get_conversation_log()
        npc_invocations = [m for m in log if "PLAY AS" in m.get("content", "")]
        assert len(npc_invocations) >= 1


class TestFullDemoFlow:
    """Test a simplified version of the full demo flow."""

    @pytest.mark.asyncio
    async def test_chapter1_demo_flow(self):
        """Test a simplified Chapter 1 flow."""
        harness = AgentTestHarness()
        harness.setup_all_agents()

        try:
            # Scene 1: Intro
            scene = harness.get_current_scene()
            await harness.dm_narrates(
                "The party travels along the Triboar Trail. "
                "Ahead, you spot two dead horses on the road."
            )

            # Player action
            await harness.simulate_human_action(
                "I approach carefully and investigate the horses"
            )

            # Transition to ambush
            harness.transition_to_scene("goblin_ambush")
            harness.start_combat(["goblin_1", "goblin_2", "goblin_3", "goblin_4"])

            # Scene 2: Combat
            await harness.dm_narrates(
                "Arrows fly from the treeline! Goblins attack!"
            )

            # Combat round
            await harness.dm_prompts_turn("Thokk")
            await harness.dm_prompts_turn("Human Player", "The nearest goblin is 15 feet away!")
            await harness.simulate_human_action("I attack goblin_1 with my shortsword")

            # Resolve damage (simulated)
            harness.damage_entity("goblin_1", 7)
            harness.damage_entity("goblin_2", 7)
            harness.damage_entity("goblin_3", 7)
            harness.damage_entity("goblin_4", 7)

            # Combat ends
            harness.end_combat()

            # Scene 3: After ambush
            harness.transition_to_scene("after_ambush")
            harness.state_manager.set_progress_flag("goblins_defeated")

            await harness.dm_narrates(
                "The goblins are defeated! You notice a trail leading north."
            )

            # Verify flow completed
            log = harness.get_conversation_log()
            assert len(log) >= 5  # Multiple messages exchanged

            # Check progress
            assert harness.state_manager.get_progress_flag("goblins_defeated")

        finally:
            harness.cleanup()
