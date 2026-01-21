"""Agent test harness for integration testing.

This module provides the AgentTestHarness class that orchestrates
agents for integration testing without requiring platform connectivity.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Any, TYPE_CHECKING

from src.testing.mock_platform import MockThenvoiPlatform, MockMessage
from src.testing.fake_tools import FakeAgentTools
from src.tools.world_state import WorldStateManager
from src.content.chapter1 import SCENES, CHAPTER1_ENEMIES
from src.content.scenes import SceneManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AgentTestHarness:
    """Harness for testing agents in isolation or together.

    The harness provides:
    - Mock platform for message routing
    - World state management
    - Scene management
    - Simulated human player actions
    - Conversation logging

    Example:
        >>> harness = AgentTestHarness()
        >>> harness.setup_state()
        >>> await harness.simulate_human_action("I search the wagon")
        >>> log = harness.get_conversation_log()
    """

    def __init__(
        self,
        room_id: str = "test-campaign",
        state_file: str | None = None,
    ):
        """Initialize the test harness.

        Args:
            room_id: Room ID for the mock platform
            state_file: Path to state file (uses temp file if None)
        """
        self.room_id = room_id
        self.platform = MockThenvoiPlatform(room_id=room_id)

        # State management - use non-existent temp path to trigger default state creation
        if state_file is None:
            import os
            self._temp_state = tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=True
            )
            state_file = self._temp_state.name
            self._temp_state.close()
            # Delete the file so WorldStateManager creates default state
            if os.path.exists(state_file):
                os.remove(state_file)
        else:
            self._temp_state = None

        self.state_manager = WorldStateManager(state_file, auto_save=False)
        self.scene_manager = SceneManager(SCENES, self.state_manager)

        # Agent references (set during setup)
        self.dm_tools: FakeAgentTools | None = None
        self.npc_tools: FakeAgentTools | None = None
        self.thokk_tools: FakeAgentTools | None = None
        self.lira_tools: FakeAgentTools | None = None

        # Add human player to participants
        self.platform.add_participant("Human Player", "member")

    def setup_state(self) -> None:
        """Initialize game state to Chapter 1 intro."""
        # State manager creates default state on first access
        _ = self.state_manager.state
        logger.info("Game state initialized")

    def setup_dm(self) -> FakeAgentTools:
        """Set up the DM agent with fake tools.

        Returns:
            FakeAgentTools instance for the DM
        """
        self.dm_tools = FakeAgentTools(
            participants=[
                {"name": "DM Agent", "role": "owner"},
                {"name": "Human Player", "role": "member"},
                {"name": "NPC Agent", "role": "member"},
                {"name": "Thokk", "role": "member"},
                {"name": "Lira", "role": "member"},
            ]
        )

        async def dm_handler(msg: MockMessage) -> None:
            """Handle messages to DM."""
            logger.debug(f"DM received: {msg.content[:50]}...")
            # In real integration, this would invoke the DM adapter
            # For now, just record the message was received

        self.platform.register_agent("DM Agent", dm_handler)
        logger.info("DM Agent set up")
        return self.dm_tools

    def setup_npc(self) -> FakeAgentTools:
        """Set up the NPC agent with fake tools.

        Returns:
            FakeAgentTools instance for the NPC
        """
        self.npc_tools = FakeAgentTools()

        async def npc_handler(msg: MockMessage) -> None:
            """Handle messages to NPC."""
            logger.debug(f"NPC received: {msg.content[:50]}...")

        self.platform.register_agent("NPC Agent", npc_handler)
        logger.info("NPC Agent set up")
        return self.npc_tools

    def setup_thokk(self) -> FakeAgentTools:
        """Set up the Thokk (Fighter) agent with fake tools.

        Returns:
            FakeAgentTools instance for Thokk
        """
        self.thokk_tools = FakeAgentTools()

        async def thokk_handler(msg: MockMessage) -> None:
            """Handle messages to Thokk."""
            logger.debug(f"Thokk received: {msg.content[:50]}...")

        self.platform.register_agent("Thokk", thokk_handler)
        logger.info("Thokk Agent set up")
        return self.thokk_tools

    def setup_lira(self) -> FakeAgentTools:
        """Set up the Lira (Cleric) agent with fake tools.

        Returns:
            FakeAgentTools instance for Lira
        """
        self.lira_tools = FakeAgentTools()

        async def lira_handler(msg: MockMessage) -> None:
            """Handle messages to Lira."""
            logger.debug(f"Lira received: {msg.content[:50]}...")

        self.platform.register_agent("Lira", lira_handler)
        logger.info("Lira Agent set up")
        return self.lira_tools

    def setup_all_agents(self) -> dict[str, FakeAgentTools]:
        """Set up all agents.

        Returns:
            Dictionary mapping agent names to their FakeAgentTools
        """
        self.setup_state()
        return {
            "dm": self.setup_dm(),
            "npc": self.setup_npc(),
            "thokk": self.setup_thokk(),
            "lira": self.setup_lira(),
        }

    async def simulate_human_action(
        self,
        action: str,
        mentions: list[str] | None = None,
    ) -> MockMessage:
        """Simulate a human player taking an action.

        Args:
            action: The action text
            mentions: Who to @mention (defaults to DM Agent)

        Returns:
            The created message
        """
        if mentions is None:
            mentions = ["DM Agent"]

        return await self.platform.send_message(
            sender="Human Player",
            content=action,
            mentions=mentions,
        )

    async def dm_narrates(self, narration: str, mentions: list[str] | None = None) -> MockMessage:
        """Simulate the DM narrating.

        Args:
            narration: The narration text
            mentions: Who to @mention (defaults to all players)

        Returns:
            The created message
        """
        if mentions is None:
            mentions = ["Human Player", "Thokk", "Lira"]

        return await self.platform.send_message(
            sender="DM Agent",
            content=narration,
            mentions=mentions,
        )

    async def dm_prompts_turn(self, character: str, context: str = "") -> MockMessage:
        """Simulate the DM prompting a character's turn.

        Args:
            character: The character whose turn it is
            context: Additional combat context

        Returns:
            The created message
        """
        content = f"@{character}, your turn!"
        if context:
            content += f" {context}"

        return await self.platform.send_message(
            sender="DM Agent",
            content=content,
            mentions=[character],
        )

    async def invoke_npc(
        self,
        character_name: str,
        personality: str,
        context: str,
        scene: str,
        player_dialogue: str,
    ) -> MockMessage:
        """Invoke the NPC agent to play a character.

        Args:
            character_name: Name of the NPC to play
            personality: Personality description
            context: Current situation
            scene: Scene description
            player_dialogue: What the players said

        Returns:
            The created message
        """
        content = f"""[PLAY AS: {character_name}]
[PERSONALITY: {personality}]
[CONTEXT: {context}]
[SCENE: {scene}]

{player_dialogue}"""

        return await self.platform.send_message(
            sender="DM Agent",
            content=content,
            mentions=["NPC Agent"],
        )

    def get_conversation_log(self) -> list[dict[str, Any]]:
        """Get the full conversation log.

        Returns:
            List of message dictionaries
        """
        return self.platform.get_conversation_log()

    def get_messages_from(self, sender: str) -> list[MockMessage]:
        """Get messages from a specific sender.

        Args:
            sender: The sender's name

        Returns:
            List of messages from that sender
        """
        return self.platform.get_messages_from(sender)

    def get_current_scene(self) -> dict[str, Any] | None:
        """Get the current scene definition.

        Returns:
            Scene definition or None
        """
        return self.scene_manager.get_current_scene()

    def transition_to_scene(self, scene_id: str) -> bool:
        """Transition to a new scene.

        Args:
            scene_id: Target scene ID

        Returns:
            True if successful
        """
        return self.scene_manager.transition_to_scene(scene_id)

    def start_combat(self, enemies: list[str]) -> None:
        """Start a combat encounter.

        Args:
            enemies: List of enemy IDs
        """
        from src.game.models import EnemyState

        # Add enemies to state
        for enemy_id in enemies:
            # Determine enemy type from ID
            if "goblin" in enemy_id.lower():
                stats = CHAPTER1_ENEMIES["goblin"]
            elif "wolf" in enemy_id.lower():
                stats = CHAPTER1_ENEMIES["wolf"]
            elif "klarg" in enemy_id.lower():
                stats = CHAPTER1_ENEMIES["klarg"]
            else:
                stats = CHAPTER1_ENEMIES["goblin"]

            enemy = EnemyState(
                name=stats["name"],
                hp=stats["hp"],
                max_hp=stats["max_hp"],
                ac=stats["ac"],
                state="alive",
            )
            self.state_manager.add_enemy(enemy_id, enemy)

        # Set combat active
        self.state_manager.set("combat.active", True)
        self.state_manager.set("combat.round", 1)
        logger.info(f"Combat started with {len(enemies)} enemies")

    def end_combat(self) -> None:
        """End the current combat."""
        self.state_manager.set("combat.active", False)
        self.state_manager.set("combat.round", 0)
        logger.info("Combat ended")

    def get_party_status(self) -> dict[str, dict[str, Any]]:
        """Get current party status.

        Returns:
            Dictionary of character statuses
        """
        return self.state_manager.get_party_status()

    def get_living_enemies(self) -> list[str]:
        """Get IDs of living enemies.

        Returns:
            List of living enemy IDs
        """
        return self.state_manager.get_all_living_enemies()

    def damage_entity(self, entity_id: str, damage: int) -> int:
        """Apply damage to an entity.

        Args:
            entity_id: Entity ID
            damage: Damage amount (positive number)

        Returns:
            New HP value
        """
        return self.state_manager.update_hp(entity_id, -damage)

    def heal_entity(self, entity_id: str, healing: int) -> int:
        """Heal an entity.

        Args:
            entity_id: Entity ID
            healing: Healing amount

        Returns:
            New HP value
        """
        return self.state_manager.update_hp(entity_id, healing)

    def cleanup(self) -> None:
        """Clean up test resources."""
        if self._temp_state:
            import os
            try:
                os.remove(self._temp_state.name)
            except OSError:
                pass
