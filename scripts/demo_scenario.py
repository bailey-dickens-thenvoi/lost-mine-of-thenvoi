#!/usr/bin/env python3
"""Demo Scenario: Goblin Arrows Ambush

This script demonstrates a complete playthrough of Chapter 1:
1. Party on the road (intro narration)
2. Discovering dead horses
3. Player investigation
4. Goblin ambush combat
5. Post-combat exploration

This can be run without the actual Thenvoi platform using the mock
infrastructure, making it useful for demos and testing.

Usage:
    python scripts/demo_scenario.py

Options:
    --verbose    Show detailed logging
    --fast       Skip delays between actions
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testing.harness import AgentTestHarness
from src.content.chapter1 import get_scene_description


# Configure logging
def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


class DemoRunner:
    """Runs the demo scenario."""

    def __init__(self, fast_mode: bool = False):
        """Initialize the demo runner.

        Args:
            fast_mode: If True, skip delays between actions
        """
        self.fast_mode = fast_mode
        self.harness = AgentTestHarness()
        self.harness.setup_all_agents()

    async def delay(self, seconds: float) -> None:
        """Wait for specified seconds (skipped in fast mode)."""
        if not self.fast_mode:
            await asyncio.sleep(seconds)

    def print_header(self, text: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60 + "\n")

    def print_section(self, text: str) -> None:
        """Print a section header."""
        print(f"\n--- {text} ---\n")

    def print_dm(self, text: str) -> None:
        """Print DM narration."""
        print(f"[DM]: {text}")

    def print_player(self, name: str, text: str) -> None:
        """Print player action."""
        print(f"[{name}]: {text}")

    def print_roll(self, text: str) -> None:
        """Print a dice roll result."""
        print(f"  >> {text}")

    def print_combat_status(self) -> None:
        """Print current combat status."""
        party = self.harness.get_party_status()
        enemies = self.harness.get_living_enemies()

        print("\n  PARTY STATUS:")
        for char_id, info in party.items():
            status = "OK" if info["is_alive"] else "DOWN"
            print(f"    {info['name']}: {info['hp']}/{info['max_hp']} HP [{status}]")

        print(f"\n  ENEMIES REMAINING: {len(enemies)}")
        for enemy_id in enemies:
            enemy = self.harness.state_manager.get_enemy(enemy_id)
            if enemy:
                print(f"    {enemy.name}: {enemy.hp}/{enemy.max_hp} HP")

    async def run_intro(self) -> None:
        """Run the intro scene."""
        self.print_section("Scene 1: The Road to Phandalin")

        # Get intro description
        desc = get_scene_description("intro")
        self.print_dm(desc)

        await self.delay(2)

    async def run_investigation(self) -> None:
        """Run the player investigation."""
        self.print_section("Scene 2: Investigation")

        # Human player investigates
        action = "I approach the dead horses and investigate them carefully."
        self.print_player("Vex", action)
        await self.harness.simulate_human_action(action)

        await self.delay(1)

        # DM rolls and responds
        self.print_roll("Investigation Check for Vex: [14] + 4 = 18 vs DC 10... Success!")
        self.print_dm(
            "You recognize these horses from Gundren's description - they belonged "
            "to him and Sildar! The saddlebags have been looted, and the arrows "
            "look goblin-made."
        )

        await self.delay(1)

        # Perception check
        self.print_player("Thokk", "I scan the treeline for threats.")
        self.print_roll("Perception Check for Thokk: [8] + 1 = 9 vs DC 10... Failure.")
        self.print_dm("The forest seems quiet. Perhaps too quiet...")

        await self.delay(2)

    async def run_ambush(self) -> None:
        """Run the goblin ambush."""
        self.print_section("Scene 3: AMBUSH!")

        # Transition and start combat
        self.harness.transition_to_scene("goblin_ambush")
        self.harness.start_combat(["goblin_1", "goblin_2", "goblin_3", "goblin_4"])

        desc = get_scene_description("goblin_ambush")
        self.print_dm(desc)

        await self.delay(1)

        # Initiative
        print("\n  INITIATIVE ORDER:")
        print("    1. Goblin 2 (18)")
        print("    2. Thokk (15)")
        print("    3. Vex (14)")
        print("    4. Lira (12)")
        print("    5. Goblin 1 (11)")
        print("    6. Goblin 3 (9)")
        print("    7. Goblin 4 (7)")

        self.harness.state_manager.set("combat.round", 1)

        await self.delay(2)

    async def run_combat_round(self, round_num: int) -> bool:
        """Run a single combat round.

        Args:
            round_num: Current round number

        Returns:
            True if combat should continue
        """
        self.print_section(f"Round {round_num}")
        self.harness.state_manager.set("combat.round", round_num)

        # Goblin 2's turn
        if "goblin_2" in self.harness.get_living_enemies():
            self.print_dm("Goblin 2's turn! It fires an arrow at Thokk!")
            self.print_roll("Attack Roll: [12] + 4 = 16 vs AC 16... Hit!")
            self.print_roll("Damage: [4] + 2 = 6 piercing damage")
            self.harness.damage_entity("ai_fighter", 6)
            await self.delay(1)

        # Thokk's turn
        self.print_dm("@Thokk, your turn! Goblins are 30 feet away!")
        await self.harness.dm_prompts_turn("Thokk")

        self.print_player("Thokk", "Thokk charges Goblin 2 and swings his longsword!")
        self.print_roll("Attack Roll: [17] + 5 = 22 vs AC 15... Hit!")
        self.print_roll("Damage: [7] + 3 = 10 slashing damage!")
        self.harness.damage_entity("goblin_2", 10)
        self.print_dm("Goblin 2 falls!")
        await self.delay(1)

        # Vex's turn
        self.print_dm("@Vex, your turn! Goblin 1 is 20 feet away!")
        await self.harness.dm_prompts_turn("Human Player")

        self.print_player("Vex", "I shoot my shortbow at Goblin 1, using Thokk for Sneak Attack!")
        await self.harness.simulate_human_action("I shoot Goblin 1 with my shortbow")
        self.print_roll("Attack Roll: [15] + 5 = 20 vs AC 15... Hit!")
        self.print_roll("Damage: [5] + 3 = 8 piercing + [4] Sneak Attack = 12 damage!")
        self.harness.damage_entity("goblin_1", 12)
        self.print_dm("Your arrow strikes true! Goblin 1 collapses!")
        await self.delay(1)

        # Lira's turn
        self.print_dm("@Lira, your turn! Two goblins remain!")
        await self.harness.dm_prompts_turn("Lira")

        self.print_player("Lira", "I cast Sacred Flame on Goblin 3!")
        self.print_roll("Goblin 3 DEX Save: [6] vs DC 13... Failure!")
        self.print_roll("Damage: [6] radiant damage")
        self.harness.damage_entity("goblin_3", 6)
        self.print_dm("Divine fire engulfs the goblin!")
        await self.delay(1)

        # Remaining goblin turns
        if "goblin_3" in self.harness.get_living_enemies():
            self.print_dm("Goblin 3, wounded, attacks Lira!")
            self.print_roll("Attack Roll: [8] + 4 = 12 vs AC 16... Miss!")
            self.print_dm("The goblin's scimitar glances off Lira's shield!")

        if "goblin_4" in self.harness.get_living_enemies():
            self.print_dm("Goblin 4 sees its companions falling and flees toward the forest!")
            self.print_dm("(It's heading north - toward what must be their hideout!)")
            self.harness.state_manager.remove_enemy("goblin_4")

        await self.delay(1)
        self.print_combat_status()

        # Check if combat continues
        remaining = self.harness.get_living_enemies()
        return len(remaining) > 0

    async def run_combat(self) -> None:
        """Run the full combat encounter."""
        round_num = 1
        while await self.run_combat_round(round_num):
            round_num += 1
            if round_num > 5:  # Safety limit
                break

        # End combat
        self.harness.end_combat()
        self.print_section("COMBAT ENDS")
        self.print_dm("The goblins are defeated! One fled north into the forest.")

        await self.delay(2)

    async def run_aftermath(self) -> None:
        """Run the post-combat scene."""
        self.print_section("Scene 4: After the Ambush")

        self.harness.transition_to_scene("after_ambush")
        self.harness.state_manager.set_progress_flag("goblins_defeated")

        desc = get_scene_description("after_ambush")
        self.print_dm(desc)

        await self.delay(1)

        # Player searches
        self.print_player("Vex", "I search the goblin bodies.")
        self.print_roll("Investigation Check: [16] + 4 = 20 vs DC 12... Success!")
        self.print_dm(
            "Among the goblins' belongings, you find a crude map on bark showing "
            "a cave entrance. One goblin has a human-made leather pouch with 15 gold pieces - "
            "this must have belonged to one of the ambush victims."
        )

        await self.delay(1)

        # Find trail
        self.print_player("Thokk", "I look for tracks where the goblin fled.")
        self.print_roll("Survival Check: [11] + 2 = 13 vs DC 10... Success!")
        self.print_dm(
            "The trail is clear - goblin footprints and drag marks lead north "
            "into the forest. Someone was dragged this way, and the fleeing goblin "
            "headed the same direction."
        )

        self.harness.state_manager.set_progress_flag("goblin_trail_found")

        await self.delay(1)

    async def run_conclusion(self) -> None:
        """Run the conclusion."""
        self.print_header("DEMO COMPLETE")

        print("The party has defeated the goblin ambush and discovered a trail")
        print("leading to the goblins' hideout. Gundren and Sildar are still missing.")
        print("\nThe adventure continues...")

        print("\n--- FINAL STATE ---")
        print(f"Current Scene: {self.harness.state_manager.get('current_scene')}")
        print("Progress Flags:")
        print(f"  - goblins_defeated: {self.harness.state_manager.get_progress_flag('goblins_defeated')}")
        print(f"  - trail_found: {self.harness.state_manager.get_progress_flag('goblin_trail_found')}")

        party = self.harness.get_party_status()
        print("\nFinal Party Status:")
        for char_id, info in party.items():
            print(f"  - {info['name']}: {info['hp']}/{info['max_hp']} HP")

    async def run(self) -> None:
        """Run the full demo."""
        try:
            self.print_header("LOST MINES OF PHANDELVER - DEMO")
            print("Chapter 1: Goblin Arrows")
            print("A demonstration of the multi-agent D&D campaign system")

            await self.run_intro()
            await self.run_investigation()
            await self.run_ambush()
            await self.run_combat()
            await self.run_aftermath()
            await self.run_conclusion()

        finally:
            self.harness.cleanup()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Lost Mines of Thenvoi demo scenario"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed logging"
    )
    parser.add_argument(
        "--fast", "-f",
        action="store_true",
        help="Skip delays between actions"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    runner = DemoRunner(fast_mode=args.fast)
    asyncio.run(runner.run())

    return 0


if __name__ == "__main__":
    sys.exit(main())
