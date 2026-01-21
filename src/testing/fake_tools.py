"""Fake implementation of AgentToolsProtocol for testing.

This module provides a fake implementation of the Thenvoi AgentToolsProtocol
that can be used to test agents without requiring actual platform connectivity.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SentMessage:
    """Record of a sent message."""

    content: str
    mentions: list[str]


@dataclass
class SentEvent:
    """Record of a sent event."""

    content: str
    message_type: str


class FakeAgentTools:
    """Fake implementation of AgentToolsProtocol for testing.

    This class records all tool calls and allows inspection of what
    an agent attempted to do during testing.

    Example:
        >>> tools = FakeAgentTools()
        >>> await tools.send_message("Hello!", ["Player"])
        >>> assert len(tools.sent_messages) == 1
        >>> assert tools.sent_messages[0].content == "Hello!"
    """

    def __init__(
        self,
        participants: list[dict[str, str]] | None = None,
        peers: list[dict[str, str]] | None = None,
    ):
        """Initialize fake tools.

        Args:
            participants: List of participants in the room
            peers: List of available peers to add
        """
        self.participants = participants or [
            {"name": "DM Agent", "role": "owner"},
            {"name": "Human Player", "role": "member"},
        ]
        self.peers = peers or []

        # Records of tool calls
        self.sent_messages: list[SentMessage] = []
        self.sent_events: list[SentEvent] = []
        self.added_participants: list[dict[str, str]] = []
        self.removed_participants: list[str] = []
        self.created_chatrooms: list[str] = []
        self.tool_calls: list[dict[str, Any]] = []

    async def send_message(self, content: str, mentions: list[str] | None = None) -> dict[str, Any]:
        """Record a sent message.

        Args:
            content: Message content
            mentions: List of @mentioned names

        Returns:
            Success response
        """
        msg = SentMessage(content=content, mentions=mentions or [])
        self.sent_messages.append(msg)
        logger.debug(f"FakeTools: send_message({content[:50]}..., mentions={mentions})")
        return {"success": True, "message_id": f"msg_{len(self.sent_messages)}"}

    async def send_event(self, content: str, message_type: str = "thought") -> dict[str, Any]:
        """Record a sent event.

        Args:
            content: Event content
            message_type: Event type (thought, tool_call, tool_result, error, task)

        Returns:
            Success response
        """
        event = SentEvent(content=content, message_type=message_type)
        self.sent_events.append(event)
        logger.debug(f"FakeTools: send_event({message_type}: {content[:50]}...)")
        return {"success": True}

    async def get_participants(self) -> list[dict[str, str]]:
        """Get room participants.

        Returns:
            List of participant info
        """
        return list(self.participants)

    async def add_participant(self, name: str, role: str = "member") -> dict[str, Any]:
        """Record adding a participant.

        Args:
            name: Participant name
            role: Participant role

        Returns:
            Success response
        """
        self.added_participants.append({"name": name, "role": role})
        self.participants.append({"name": name, "role": role})
        return {"success": True}

    async def remove_participant(self, name: str) -> dict[str, Any]:
        """Record removing a participant.

        Args:
            name: Participant name

        Returns:
            Success response
        """
        self.removed_participants.append(name)
        self.participants = [p for p in self.participants if p["name"] != name]
        return {"success": True}

    async def lookup_peers(self, page: int = 1, page_size: int = 10) -> list[dict[str, str]]:
        """Get available peers.

        Args:
            page: Page number
            page_size: Results per page

        Returns:
            List of peer info
        """
        start = (page - 1) * page_size
        end = start + page_size
        return self.peers[start:end]

    async def create_chatroom(self, task_id: str | None = None) -> dict[str, Any]:
        """Record creating a chatroom.

        Args:
            task_id: Optional task ID

        Returns:
            Success response with room ID
        """
        room_id = f"room_{len(self.created_chatrooms) + 1}"
        self.created_chatrooms.append(room_id)
        return {"success": True, "room_id": room_id}

    async def execute_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Record and execute a tool call.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Tool result (mock)
        """
        self.tool_calls.append({"name": tool_name, "input": tool_input})
        logger.debug(f"FakeTools: execute_tool_call({tool_name}, {tool_input})")

        # Return mock results for common platform tools
        if tool_name == "send_message":
            return await self.send_message(
                tool_input.get("content", ""),
                tool_input.get("mentions", []),
            )
        elif tool_name == "send_event":
            return await self.send_event(
                tool_input.get("content", ""),
                tool_input.get("message_type", "thought"),
            )
        elif tool_name == "get_participants":
            return await self.get_participants()
        elif tool_name == "add_participant":
            return await self.add_participant(
                tool_input.get("name", ""),
                tool_input.get("role", "member"),
            )
        elif tool_name == "remove_participant":
            return await self.remove_participant(tool_input.get("name", ""))
        elif tool_name == "lookup_peers":
            return await self.lookup_peers(
                tool_input.get("page", 1),
                tool_input.get("page_size", 10),
            )
        elif tool_name == "create_chatroom":
            return await self.create_chatroom(tool_input.get("task_id"))

        # Unknown tool - return generic success
        return {"success": True, "tool": tool_name}

    def get_anthropic_tool_schemas(self) -> list[dict[str, Any]]:
        """Get Anthropic-format tool schemas for platform tools.

        Returns:
            List of tool schemas
        """
        return [
            {
                "name": "send_message",
                "description": "Send a message to the chat room",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "mentions": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "send_event",
                "description": "Send an internal event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "message_type": {"type": "string"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "get_participants",
                "description": "Get room participants",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def clear(self) -> None:
        """Clear all recorded tool calls."""
        self.sent_messages.clear()
        self.sent_events.clear()
        self.added_participants.clear()
        self.removed_participants.clear()
        self.created_chatrooms.clear()
        self.tool_calls.clear()

    def get_last_message(self) -> SentMessage | None:
        """Get the last sent message.

        Returns:
            Last message or None
        """
        if self.sent_messages:
            return self.sent_messages[-1]
        return None

    def get_messages_with_mention(self, name: str) -> list[SentMessage]:
        """Get messages that mention a specific name.

        Args:
            name: Name to search for

        Returns:
            List of messages mentioning that name
        """
        return [m for m in self.sent_messages if name in m.mentions]
