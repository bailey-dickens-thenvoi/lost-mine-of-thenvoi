"""Mock Thenvoi platform for local testing.

This module provides a mock implementation of the Thenvoi platform
that can be used for integration testing without requiring actual
platform connectivity.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class MockMessage:
    """Represents a message in the mock platform."""

    id: str
    sender: str
    content: str
    mentions: list[str]
    timestamp: datetime
    room_id: str = "test-room"

    @classmethod
    def create(
        cls,
        sender: str,
        content: str,
        mentions: list[str] | None = None,
        room_id: str = "test-room",
    ) -> "MockMessage":
        """Create a new mock message."""
        return cls(
            id=str(uuid4()),
            sender=sender,
            content=content,
            mentions=mentions or [],
            timestamp=datetime.now(),
            room_id=room_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "mentions": self.mentions,
            "timestamp": self.timestamp.isoformat(),
            "room_id": self.room_id,
        }


# Type alias for agent message handlers
AgentHandler = Callable[[MockMessage], Coroutine[Any, Any, None]]


class MockThenvoiPlatform:
    """Mock Thenvoi platform for local testing.

    This class simulates the core functionality of the Thenvoi platform:
    - Message routing based on @mentions
    - Agent registration and message dispatch
    - Conversation history tracking

    Example:
        >>> platform = MockThenvoiPlatform()
        >>> platform.register_agent("DM Agent", dm_handler)
        >>> await platform.send_message("Player", "I attack!", ["DM Agent"])
    """

    def __init__(self, room_id: str = "test-room"):
        """Initialize the mock platform.

        Args:
            room_id: Default room ID for messages
        """
        self.room_id = room_id
        self.messages: list[MockMessage] = []
        self.agents: dict[str, AgentHandler] = {}
        self.participants: list[dict[str, str]] = []
        self._processing = False
        self._message_queue: asyncio.Queue[MockMessage] = asyncio.Queue()

    def register_agent(self, name: str, handler: AgentHandler) -> None:
        """Register an agent with a message handler.

        Args:
            name: The agent's display name (used for @mentions)
            handler: Async function to call when agent receives a message
        """
        self.agents[name] = handler
        self.participants.append({"name": name, "role": "member"})
        logger.debug(f"Registered agent: {name}")

    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent.

        Args:
            name: The agent's display name

        Returns:
            True if agent was removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            self.participants = [p for p in self.participants if p["name"] != name]
            return True
        return False

    async def send_message(
        self,
        sender: str,
        content: str,
        mentions: list[str] | None = None,
    ) -> MockMessage:
        """Send a message to the platform.

        Messages are only delivered to agents that are @mentioned.

        Args:
            sender: The sender's name
            content: The message content
            mentions: List of @mentioned agent names

        Returns:
            The created MockMessage
        """
        msg = MockMessage.create(
            sender=sender,
            content=content,
            mentions=mentions or [],
            room_id=self.room_id,
        )

        self.messages.append(msg)
        logger.debug(f"Message from {sender}: {content[:50]}...")

        # Dispatch to mentioned agents
        await self._dispatch_message(msg)

        return msg

    async def _dispatch_message(self, msg: MockMessage) -> None:
        """Dispatch a message to mentioned agents.

        Args:
            msg: The message to dispatch
        """
        for agent_name in msg.mentions:
            if agent_name in self.agents:
                handler = self.agents[agent_name]
                try:
                    logger.debug(f"Dispatching to {agent_name}")
                    await handler(msg)
                except Exception as e:
                    logger.error(f"Error dispatching to {agent_name}: {e}")

    def get_messages(self) -> list[MockMessage]:
        """Get all messages.

        Returns:
            List of all messages
        """
        return list(self.messages)

    def get_messages_from(self, sender: str) -> list[MockMessage]:
        """Get messages from a specific sender.

        Args:
            sender: The sender's name

        Returns:
            List of messages from that sender
        """
        return [m for m in self.messages if m.sender == sender]

    def get_messages_mentioning(self, name: str) -> list[MockMessage]:
        """Get messages that mention a specific agent.

        Args:
            name: The agent's name

        Returns:
            List of messages mentioning that agent
        """
        return [m for m in self.messages if name in m.mentions]

    def get_conversation_log(self) -> list[dict[str, Any]]:
        """Get the full conversation log as dictionaries.

        Returns:
            List of message dictionaries
        """
        return [m.to_dict() for m in self.messages]

    def get_participants(self) -> list[dict[str, str]]:
        """Get list of participants.

        Returns:
            List of participant info dicts
        """
        return list(self.participants)

    def add_participant(self, name: str, role: str = "member") -> None:
        """Add a participant (non-agent).

        Args:
            name: Participant name
            role: Participant role
        """
        self.participants.append({"name": name, "role": role})

    def clear_messages(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def get_last_message(self) -> MockMessage | None:
        """Get the most recent message.

        Returns:
            The last message or None if no messages
        """
        if self.messages:
            return self.messages[-1]
        return None

    def get_last_message_from(self, sender: str) -> MockMessage | None:
        """Get the most recent message from a sender.

        Args:
            sender: The sender's name

        Returns:
            The last message from that sender or None
        """
        messages = self.get_messages_from(sender)
        if messages:
            return messages[-1]
        return None
