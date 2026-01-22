"""Tag parsing utilities for DM messages.

Structured tags help DM messages be more parseable and enable
richer game flow control.

Tag Format:
    [TAG:value] Content...
    [TAG] Content...

Example Tags:
    [TURN:thokk] Thokk, it's your turn!
    [NARRATION] The cave grows darker...
    [COMBAT:hit] The arrow strikes true!
    [INFO] Party HP: Thokk 8/12, Lira 10/10
    [PROMPT] What do you do?
"""

from __future__ import annotations

import re
from typing import NamedTuple


class ParsedMessage(NamedTuple):
    """Result of parsing a tagged message.

    Attributes:
        tag: The tag name (e.g., 'TURN', 'NARRATION', 'COMBAT')
        tag_value: Optional value after colon (e.g., 'thokk' in '[TURN:thokk]')
        content: The message content after the tag
    """

    tag: str | None
    tag_value: str | None
    content: str


# Pattern matches: [TAG] or [TAG:value] at start of message
# Group 1: tag name
# Group 2: optional tag value (after colon)
# Group 3: rest of message content
TAG_PATTERN = re.compile(r"^\[(\w+)(?::([^\]]+))?\]\s*(.*)$", re.DOTALL)


def parse_message_tag(message: str) -> ParsedMessage:
    """Parse a tagged message into components.

    Args:
        message: The message to parse

    Returns:
        ParsedMessage with tag, tag_value, and content

    Examples:
        >>> parse_message_tag("[TURN:thokk] Your turn!")
        ParsedMessage(tag='TURN', tag_value='thokk', content='Your turn!')

        >>> parse_message_tag("[NARRATION] The cave grows dark.")
        ParsedMessage(tag='NARRATION', tag_value=None, content='The cave grows dark.')

        >>> parse_message_tag("No tag here")
        ParsedMessage(tag=None, tag_value=None, content='No tag here')
    """
    match = TAG_PATTERN.match(message)
    if match:
        return ParsedMessage(
            tag=match.group(1),
            tag_value=match.group(2),
            content=match.group(3),
        )
    return ParsedMessage(tag=None, tag_value=None, content=message)


def strip_tags_for_display(message: str) -> str:
    """Remove tags from a message for human-readable display.

    Args:
        message: The message potentially containing tags

    Returns:
        The message content without the leading tag

    Examples:
        >>> strip_tags_for_display("[TURN:thokk] Your turn!")
        'Your turn!'

        >>> strip_tags_for_display("No tag here")
        'No tag here'
    """
    parsed = parse_message_tag(message)
    return parsed.content


def create_tagged_message(tag: str, content: str, tag_value: str | None = None) -> str:
    """Create a tagged message.

    Args:
        tag: The tag name (e.g., 'TURN', 'NARRATION')
        content: The message content
        tag_value: Optional value for the tag

    Returns:
        Formatted tagged message

    Examples:
        >>> create_tagged_message("TURN", "Your turn!", "thokk")
        '[TURN:thokk] Your turn!'

        >>> create_tagged_message("NARRATION", "The cave grows dark.")
        '[NARRATION] The cave grows dark.'
    """
    if tag_value:
        return f"[{tag}:{tag_value}] {content}"
    return f"[{tag}] {content}"


def is_turn_tag(message: str) -> bool:
    """Check if a message contains a TURN tag.

    Args:
        message: The message to check

    Returns:
        True if the message starts with a [TURN:...] tag
    """
    parsed = parse_message_tag(message)
    return parsed.tag == "TURN"


def get_turn_target(message: str) -> str | None:
    """Extract the turn target from a TURN-tagged message.

    Args:
        message: The message to parse

    Returns:
        The turn target agent ID, or None if not a TURN message

    Examples:
        >>> get_turn_target("[TURN:thokk] Your turn!")
        'thokk'

        >>> get_turn_target("Not a turn message")
        None
    """
    parsed = parse_message_tag(message)
    if parsed.tag == "TURN":
        return parsed.tag_value
    return None


def is_narration(message: str) -> bool:
    """Check if a message is a narration (no response expected).

    Args:
        message: The message to check

    Returns:
        True if the message is tagged as narration
    """
    parsed = parse_message_tag(message)
    return parsed.tag == "NARRATION"


def is_prompt(message: str) -> bool:
    """Check if a message is prompting for input.

    Args:
        message: The message to check

    Returns:
        True if the message is tagged as a prompt
    """
    parsed = parse_message_tag(message)
    return parsed.tag == "PROMPT"


def is_combat_result(message: str) -> tuple[bool, str | None]:
    """Check if a message is a combat result.

    Args:
        message: The message to check

    Returns:
        Tuple of (is_combat, result_type) where result_type is
        'hit', 'miss', 'crit', 'init', etc.

    Examples:
        >>> is_combat_result("[COMBAT:hit] The sword strikes true!")
        (True, 'hit')

        >>> is_combat_result("Regular message")
        (False, None)
    """
    parsed = parse_message_tag(message)
    if parsed.tag == "COMBAT":
        return (True, parsed.tag_value)
    return (False, None)
