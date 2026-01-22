"""Main entry point for Lost Mine of Thenvoi.

This module provides the main entry point for running the D&D campaign.
Individual agents can be run separately or together based on command line args.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import NoReturn

from src.config import get_settings

# Path to the world state file
WORLD_STATE_PATH = Path(__file__).parent.parent / "data" / "world_state.json"


def print_banner() -> None:
    """Print the application banner."""
    banner = """
    ========================================
     Lost Mine of Thenvoi
     A D&D Campaign Powered by Multi-Agent AI
    ========================================
    """
    print(banner)


def reset_game_state() -> None:
    """Reset the game state by deleting the world state file.

    Safely removes data/world_state.json if it exists.
    Prints a confirmation message regardless of whether the file existed.
    """
    if WORLD_STATE_PATH.exists():
        WORLD_STATE_PATH.unlink()
    print("[OK] Game state reset. Starting fresh!")


def check_configuration() -> bool:
    """Check if all required configuration is present.

    Returns:
        True if configuration is valid, False otherwise.
    """
    settings = get_settings()

    # Check for Anthropic API key
    if not settings.is_anthropic_configured():
        print("[WARNING] ANTHROPIC_API_KEY not configured")
        print("  Set this in your .env file to use Claude models")
        return False

    # Check for agent credentials
    missing = settings.validate_required_credentials()
    if missing:
        print(f"[WARNING] Missing agent credentials: {', '.join(missing)}")
        print("  Create agents at platform.thenvoi.com and add credentials to .env")
        return False

    print("[OK] All configuration validated")
    return True


async def run_agent(agent_type: str) -> NoReturn:
    """Run a specific agent.

    Args:
        agent_type: One of 'dm', 'npc', 'thokk', 'lira'
    """
    # Import here to avoid circular imports
    # These will be implemented in subsequent issues
    print(f"[INFO] Starting {agent_type} agent...")

    if agent_type == "dm":
        from src.agents.dm_agent import run_dm_agent

        await run_dm_agent()
    elif agent_type == "npc":
        from src.agents.npc_agent import run_npc_agent

        await run_npc_agent()
    elif agent_type == "thokk":
        from src.agents.player_agent import run_thokk_agent

        await run_thokk_agent()
    elif agent_type == "lira":
        from src.agents.player_agent import run_lira_agent

        await run_lira_agent()
    else:
        print(f"[ERROR] Unknown agent type: {agent_type}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Lost Mine of Thenvoi - D&D Multi-Agent Campaign",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --check          # Check configuration
  python -m src.main --agent dm       # Run the DM agent
  python -m src.main --agent thokk    # Run the Thokk (Fighter) agent
  python -m src.main --new-game       # Reset game state and start fresh
  python -m src.main --new-game --agent dm  # Reset and start DM agent
        """,
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check configuration and exit",
    )

    parser.add_argument(
        "--new-game",
        action="store_true",
        help="Reset game state by deleting world_state.json",
    )

    parser.add_argument(
        "--agent",
        choices=["dm", "npc", "thokk", "lira"],
        help="Run a specific agent",
    )

    args = parser.parse_args()

    print_banner()

    if args.check:
        success = check_configuration()
        sys.exit(0 if success else 1)

    # Handle --new-game flag (can be combined with --agent)
    if args.new_game:
        reset_game_state()
        # If no agent specified, exit after reset
        if not args.agent:
            sys.exit(0)

    if args.agent:
        # Validate configuration before running
        settings = get_settings()
        missing = settings.validate_required_credentials([args.agent])
        if missing:
            print(f"[ERROR] Agent '{args.agent}' is not configured")
            print("  Add credentials to .env file")
            sys.exit(1)

        if not settings.is_anthropic_configured():
            print("[ERROR] ANTHROPIC_API_KEY not configured")
            sys.exit(1)

        # Run the agent
        try:
            asyncio.run(run_agent(args.agent))
        except KeyboardInterrupt:
            print("\n[INFO] Agent stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Agent crashed: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
