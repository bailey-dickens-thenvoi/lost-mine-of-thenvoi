"""NPC helper functions for the D&D campaign.

This module provides utilities for loading NPC data and formatting
messages for the NPC agent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default path to NPC data file
DEFAULT_NPC_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "npcs.json"


def load_npc_data(path: str | Path | None = None) -> dict[str, Any]:
    """Load NPC definitions from JSON file.

    Args:
        path: Path to npcs.json file. Uses default if not provided.

    Returns:
        Dictionary of NPC definitions keyed by NPC ID.

    Raises:
        FileNotFoundError: If the NPC data file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    data_path = Path(path) if path else DEFAULT_NPC_DATA_PATH

    if not data_path.exists():
        logger.warning(f"NPC data file not found at {data_path}")
        return {}

    with open(data_path) as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} NPC definitions from {data_path}")
    return data


def get_npc(npc_id: str, npc_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Get a specific NPC's data.

    Args:
        npc_id: The NPC identifier (e.g., "gundren_rockseeker")
        npc_data: Pre-loaded NPC data, or None to load from file

    Returns:
        NPC data dictionary or None if not found
    """
    if npc_data is None:
        npc_data = load_npc_data()

    return npc_data.get(npc_id)


def format_npc_prompt(
    npc_id: str,
    context: str,
    scene: str,
    player_action: str,
    npc_data: dict[str, Any] | None = None,
) -> str:
    """Format a message for the NPC agent.

    This creates the structured message format that the NPC agent
    expects from the DM. The DM uses this to invoke NPC roleplay.

    Args:
        npc_id: Key in npcs.json (e.g., "gundren_rockseeker")
        context: Current situation and what the character knows
        scene: What's happening right now
        player_action: What the player said or did
        npc_data: Pre-loaded NPC data, or None to load from file

    Returns:
        Formatted message to send to NPC agent

    Raises:
        KeyError: If the NPC ID is not found in the data

    Example:
        >>> prompt = format_npc_prompt(
        ...     npc_id="gundren_rockseeker",
        ...     context="Just rescued from goblins. Worried about his map.",
        ...     scene="Party asking what happened",
        ...     player_action="Fighter: 'Gundren, are you okay?'"
        ... )
        >>> print(prompt)
        [PLAY AS: Gundren Rockseeker]
        [PERSONALITY: Gruff but kind-hearted...]
        ...
    """
    if npc_data is None:
        npc_data = load_npc_data()

    npc = npc_data.get(npc_id)
    if npc is None:
        raise KeyError(f"NPC not found: {npc_id}")

    return f"""[PLAY AS: {npc['name']}]
[PERSONALITY: {npc['personality']}]
[CONTEXT: {context}]
[SCENE: {scene}]

{player_action}"""


def format_npc_prompt_custom(
    name: str,
    personality: str,
    context: str,
    scene: str,
    player_action: str,
) -> str:
    """Format a message for the NPC agent with custom personality.

    Use this for NPCs not in the data file, or to override personality.

    Args:
        name: Character name
        personality: Character traits and speech patterns
        context: Current situation
        scene: What's happening now
        player_action: What the player said/did

    Returns:
        Formatted message for NPC agent
    """
    return f"""[PLAY AS: {name}]
[PERSONALITY: {personality}]
[CONTEXT: {context}]
[SCENE: {scene}]

{player_action}"""


def get_npc_names(npc_data: dict[str, Any] | None = None) -> list[str]:
    """Get list of all NPC display names.

    Args:
        npc_data: Pre-loaded NPC data, or None to load from file

    Returns:
        List of NPC display names
    """
    if npc_data is None:
        npc_data = load_npc_data()

    return [npc["name"] for npc in npc_data.values()]


def get_npcs_at_location(
    location: str,
    npc_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Get all NPCs at a specific location.

    Args:
        location: Location ID (e.g., "cragmaw_hideout", "phandalin")
        npc_data: Pre-loaded NPC data, or None to load from file

    Returns:
        List of NPC data dictionaries at that location
    """
    if npc_data is None:
        npc_data = load_npc_data()

    return [
        {**npc, "id": npc_id}
        for npc_id, npc in npc_data.items()
        if npc.get("location") == location
    ]


def get_alive_npcs(npc_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Get all living NPCs.

    Args:
        npc_data: Pre-loaded NPC data, or None to load from file

    Returns:
        List of NPC data dictionaries for living NPCs
    """
    if npc_data is None:
        npc_data = load_npc_data()

    return [
        {**npc, "id": npc_id}
        for npc_id, npc in npc_data.items()
        if npc.get("current_state") != "dead"
    ]
