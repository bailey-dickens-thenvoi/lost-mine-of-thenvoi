#!/usr/bin/env python3
"""Test connectivity for all agents on the Thenvoi platform.

This script validates that all agent credentials are properly configured
and can successfully connect to the Thenvoi platform.

Usage:
    python scripts/test_connection.py

Requirements:
    - All agent credentials must be configured in .env file
    - ANTHROPIC_API_KEY must be set for adapter creation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings


def check_credentials() -> tuple[bool, list[str]]:
    """Check if all required credentials are configured.

    Returns:
        Tuple of (all_configured, list_of_missing_agents)
    """
    settings = get_settings()

    missing = settings.validate_required_credentials()

    if not settings.is_anthropic_configured():
        missing.append("anthropic_api_key")

    return len(missing) == 0, missing


def print_credentials_status() -> None:
    """Print the status of all configured credentials."""
    settings = get_settings()

    print("\n=== Credential Configuration Status ===\n")

    # Agent credentials
    agents = [
        ("DM Agent", settings.get_dm_credentials()),
        ("NPC Agent", settings.get_npc_credentials()),
        ("Thokk (Fighter)", settings.get_thokk_credentials()),
        ("Lira (Cleric)", settings.get_lira_credentials()),
    ]

    for name, creds in agents:
        status = "[OK]" if creds.is_configured() else "[MISSING]"
        if creds.is_configured():
            # Show truncated agent_id
            agent_id_preview = f"{creds.agent_id[:8]}..." if len(creds.agent_id) > 8 else creds.agent_id
            print(f"  {status} {name}: agent_id={agent_id_preview}")
        else:
            print(f"  {status} {name}: Not configured")

    # Anthropic API key
    anthropic_status = "[OK]" if settings.is_anthropic_configured() else "[MISSING]"
    print(f"  {anthropic_status} Anthropic API Key")

    # Platform URLs
    print(f"\n  Platform REST URL: {settings.thenvoi_rest_url}")
    print(f"  Platform WS URL: {settings.thenvoi_ws_url}")

    # Test chatroom
    if settings.test_chatroom_id:
        print(f"  Test Chatroom ID: {settings.test_chatroom_id}")
    else:
        print("  Test Chatroom ID: Not configured")

    print()


async def test_agent_connection(
    agent_id: str,
    api_key: str,
    name: str,
) -> tuple[bool, str]:
    """Test that an agent can connect to the platform.

    This validates the credentials without starting the full agent loop.

    Args:
        agent_id: The agent's UUID
        api_key: The agent's API key
        name: Display name for logging

    Returns:
        Tuple of (success, message)
    """
    try:
        from thenvoi import Agent
        from thenvoi.adapters import AnthropicAdapter

        # Create a minimal adapter
        adapter = AnthropicAdapter(
            model="claude-sonnet-4-5-20250929",
            system_prompt=f"You are {name}. Respond with 'Connection test successful!'",
        )

        settings = get_settings()

        # Create agent (this validates credentials with the platform)
        agent = Agent.create(
            adapter=adapter,
            agent_id=agent_id,
            api_key=api_key,
            ws_url=settings.thenvoi_ws_url,
            rest_url=settings.thenvoi_rest_url,
        )

        # The Agent.create() call validates credentials
        # If we get here, the credentials are valid
        return True, f"{name} credentials valid"

    except Exception as e:
        return False, f"{name} failed: {e}"


async def run_connection_tests() -> bool:
    """Run connection tests for all configured agents.

    Returns:
        True if all tests pass, False otherwise
    """
    settings = get_settings()

    # Build list of agents to test
    agents_to_test = []

    dm_creds = settings.get_dm_credentials()
    if dm_creds.is_configured():
        agents_to_test.append(("DM Agent", dm_creds.agent_id, dm_creds.api_key))

    npc_creds = settings.get_npc_credentials()
    if npc_creds.is_configured():
        agents_to_test.append(("NPC Agent", npc_creds.agent_id, npc_creds.api_key))

    thokk_creds = settings.get_thokk_credentials()
    if thokk_creds.is_configured():
        agents_to_test.append(("Thokk", thokk_creds.agent_id, thokk_creds.api_key))

    lira_creds = settings.get_lira_credentials()
    if lira_creds.is_configured():
        agents_to_test.append(("Lira", lira_creds.agent_id, lira_creds.api_key))

    if not agents_to_test:
        print("No agents configured to test.")
        return False

    print(f"\n=== Testing {len(agents_to_test)} Agent Connections ===\n")

    # Run tests
    results = []
    for name, agent_id, api_key in agents_to_test:
        success, message = await test_agent_connection(agent_id, api_key, name)
        results.append((success, message))
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {message}")

    # Summary
    passed = sum(1 for success, _ in results if success)
    total = len(results)

    print(f"\n=== Results: {passed}/{total} agents connected successfully ===\n")

    return passed == total


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n" + "=" * 50)
    print("  Lost Mine of Thenvoi - Connection Test")
    print("=" * 50)

    # Check credentials first
    print_credentials_status()

    all_configured, missing = check_credentials()

    if not all_configured:
        print("Missing credentials:")
        for agent in missing:
            print(f"  - {agent}")
        print("\nPlease configure all credentials in your .env file.")
        print("See .env.example for the required format.")
        return 1

    # Run connection tests
    try:
        success = asyncio.run(run_connection_tests())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nTest interrupted.")
        return 1
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
