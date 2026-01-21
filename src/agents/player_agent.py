"""AI Player Agents for the D&D Campaign.

This module provides AI-controlled party members that play alongside
the human player. Each AI player has distinct personality, combat
priorities, and decision-making patterns.

Current AI Players:
- Thokk: Half-Orc Fighter - direct, combat-focused, protective
- Lira: Human Cleric (Life) - supportive, wise, healing-focused
"""

from __future__ import annotations

import logging
from typing import Any

from thenvoi import Agent
from thenvoi.adapters import AnthropicAdapter

logger = logging.getLogger(__name__)


# Character Data
THOKK_CHARACTER: dict[str, Any] = {
    "name": "Thokk",
    "race": "Half-Orc",
    "character_class": "Fighter",
    "background": "Soldier",
    "level": 1,
    "hp": 12,
    "max_hp": 12,
    "ac": 16,
    "stats": {
        "str": 16, "dex": 14, "con": 14,
        "int": 8, "wis": 12, "cha": 10
    },
    "proficiency_bonus": 2,
    "saving_throws": ["str", "con"],
    "skills": ["athletics", "intimidation", "perception", "survival"],
    "equipment": ["longsword", "shield", "chain mail", "handaxes (2)", "explorer's pack"],
    "features": [
        "Fighting Style: Defense (+1 AC)",
        "Second Wind (1d10+1 HP as bonus action, 1/short rest)",
        "Darkvision (60 ft)",
        "Relentless Endurance (drop to 1 HP instead of 0, 1/long rest)",
        "Savage Attacks (extra damage die on critical)"
    ],
    "personality": "Direct and practical. Solves problems with strength. Loyal to allies.",
    "ideal": "Might makes right. The strong protect the weak.",
    "bond": "Owes a debt to the mercenary company that trained him.",
    "flaw": "Quick to anger, slow to forgive.",
}

LIRA_CHARACTER: dict[str, Any] = {
    "name": "Lira",
    "race": "Human",
    "character_class": "Cleric (Life Domain)",
    "background": "Acolyte",
    "level": 1,
    "hp": 10,
    "max_hp": 10,
    "ac": 16,
    "stats": {
        "str": 14, "dex": 10, "con": 12,
        "int": 10, "wis": 16, "cha": 12
    },
    "proficiency_bonus": 2,
    "saving_throws": ["wis", "cha"],
    "skills": ["insight", "medicine", "persuasion", "religion"],
    "equipment": ["mace", "shield", "scale mail", "holy symbol", "priest's pack"],
    "features": [
        "Spellcasting (WIS-based, DC 13, +5 to hit)",
        "Divine Domain: Life",
        "Disciple of Life (+2+spell level HP when healing)",
        "Heavy Armor Proficiency"
    ],
    "spells": {
        "cantrips": ["sacred flame (DEX save, 1d8 radiant)", "spare the dying", "guidance (+1d4)"],
        "1st_level_prepared": ["bless (+1d4 to attacks/saves)", "cure wounds (1d8+5 HP)",
                               "healing word (1d4+5 HP, bonus action)", "shield of faith (+2 AC)"],
        "domain_spells": ["bless", "cure wounds"],
    },
    "spell_slots": {"1st": 2},
    "personality": "Compassionate and wise. Seeks peaceful solutions but will fight to protect innocents.",
    "ideal": "All life is sacred. Healing is a sacred duty.",
    "bond": "Received a vision from her deity to find Wave Echo Cave.",
    "flaw": "Too trusting of those who seem to need help.",
}


# Fighter-specific prompts
FIGHTER_COMBAT_PRIORITIES = """
## Combat Priorities (in order)
1. **Protect wounded allies** - Position yourself between threats and hurt party members
2. **Engage the biggest threat** - Attack the most dangerous enemy to draw their attention
3. **Use Second Wind** - When below 6 HP (half), use your bonus action to heal 1d10+1
4. **Don't expose allies** - Keep squishier party members behind you
5. **Be aggressive** - You can take hits, so get in there and deal damage
"""

FIGHTER_PERSONALITY = """
## Your Voice
- Speak in short, direct sentences
- Actions speak louder than words
- Show loyalty through deeds, not flowery speech
- Grunt acknowledgments ("Hmm." "Good." "Done.")
- When you do speak up, make it count

## Typical Phrases
- "I'll handle this."
- "Stay behind me."
- "We fight." / "We don't fight."
- *cracks knuckles*
- "Talking's done."
"""

# Cleric-specific prompts
CLERIC_COMBAT_PRIORITIES = """
## Combat Priorities (in order)
1. **Keep allies alive** - If anyone is below half HP, prioritize healing them
2. **Bless at fight start** - If combat just started and you haven't cast it, Bless is powerful
3. **Sacred Flame distant enemies** - 1d8 radiant damage, DEX save, no attack roll needed
4. **Conserve spell slots** - Only use 1st level slots for healing unless victory is certain
5. **Stay at range** - You're a healer, don't get surrounded

## Spell Slot Management (2 per rest)
- Save at least 1 slot for emergency healing
- Healing Word (bonus action) lets you also attack or cantrip
- Cure Wounds heals more but costs your action
"""

CLERIC_PERSONALITY = """
## Your Voice
- Speak with calm wisdom
- Show compassion even to enemies when appropriate
- Reference your faith naturally (not preachy)
- Seek to understand before judging
- Gentle but firm when needed

## Typical Phrases
- "The light guides us."
- "Let me tend to your wounds."
- "There may be another way..."
- "Stand fast - help is coming."
- *offers a prayer*
"""


# Base system prompt template
AI_PLAYER_PROMPT = """You are {name}, a {race} {character_class} adventuring in a D&D campaign: Lost Mines of Phandelver.

## Your Character Sheet
**{name}** - Level {level} {race} {character_class}
- HP: {hp}/{max_hp}
- AC: {ac}
- Stats: STR {stats[str]} DEX {stats[dex]} CON {stats[con]} INT {stats[int]} WIS {stats[wis]} CHA {stats[cha]}

**Proficiencies**: {skills_text}
**Equipment**: {equipment_text}
**Features**: {features_text}

{spells_section}

## How to Play

When the DM @mentions you for your turn:
1. Consider the tactical situation (who's hurt, what enemies are doing)
2. Choose an action that fits your character AND the situation
3. Declare your action clearly so the DM can resolve it
4. The DM will handle all dice rolls

## Action Format

**Always declare actions clearly:**
- Attack: "I attack the [target] with my [weapon]."
- Spell: "I cast [spell] on [target]." (the DM knows what it does)
- Move: "I move to [position/description]."
- Help: "I help [ally] with their [action]."
- Other: Describe clearly what you're doing.

## CRITICAL RULES

1. **Use send_message tool** - You MUST use the send_message tool to communicate. Plain text won't reach the party.
2. **@mention recipients** - Always include who you're talking to in the mentions.
3. **Don't roll dice** - The DM rolls ALL dice. Just declare what you're doing.
4. **Stay in character** - You ARE this character. React naturally.
5. **Be concise** - 1-3 sentences for actions. Don't write essays.

{personality_section}

{combat_priorities}

## Party Members
- **Vex** (Human Player): Halfling Rogue - sneaky, nimble, your ally
- **Thokk** (AI): Half-Orc Fighter - the frontline tank
- **Lira** (AI): Human Cleric - healer and support

## Current Situation
The DM will tell you what's happening. React to that specific situation.
Respond with your action and brief in-character flavor.
"""


def _format_character_sheet(char: dict[str, Any]) -> dict[str, str]:
    """Format character data into prompt sections."""
    # Skills
    skills_text = ", ".join(char.get("skills", []))

    # Equipment
    equipment_text = ", ".join(char.get("equipment", []))

    # Features
    features_text = "\n".join(f"- {f}" for f in char.get("features", []))

    # Spells (for casters)
    spells = char.get("spells", {})
    if spells:
        spells_lines = ["**Spells**:"]
        if "cantrips" in spells:
            spells_lines.append(f"- Cantrips: {', '.join(spells['cantrips'])}")
        if "1st_level_prepared" in spells:
            spells_lines.append(f"- 1st Level (2 slots): {', '.join(spells['1st_level_prepared'])}")
        spells_section = "\n".join(spells_lines)
    else:
        spells_section = ""

    return {
        "skills_text": skills_text,
        "equipment_text": equipment_text,
        "features_text": features_text,
        "spells_section": spells_section,
    }


def build_player_system_prompt(
    char: dict[str, Any],
    personality_section: str,
    combat_priorities: str,
) -> str:
    """Build the full system prompt for an AI player.

    Args:
        char: Character data dictionary
        personality_section: Character-specific personality text
        combat_priorities: Character-specific combat priorities

    Returns:
        Complete system prompt string
    """
    formatted = _format_character_sheet(char)

    return AI_PLAYER_PROMPT.format(
        name=char["name"],
        race=char["race"],
        character_class=char["character_class"],
        level=char["level"],
        hp=char["hp"],
        max_hp=char["max_hp"],
        ac=char["ac"],
        stats=char["stats"],
        skills_text=formatted["skills_text"],
        equipment_text=formatted["equipment_text"],
        features_text=formatted["features_text"],
        spells_section=formatted["spells_section"],
        personality_section=personality_section,
        combat_priorities=combat_priorities,
    )


class AIPlayerAdapter(AnthropicAdapter):
    """Anthropic adapter for AI player agents.

    This adapter uses character-specific system prompts to create
    distinct personalities and decision-making patterns.
    """

    def __init__(
        self,
        character: dict[str, Any],
        personality_section: str,
        combat_priorities: str,
        model: str = "claude-sonnet-4-5-20250929",
        **kwargs,
    ):
        """Initialize the AI player adapter.

        Args:
            character: Character data dictionary
            personality_section: Character-specific personality text
            combat_priorities: Character-specific combat priorities
            model: Claude model to use
            **kwargs: Additional arguments for AnthropicAdapter
        """
        self.character = character
        system_prompt = build_player_system_prompt(
            character, personality_section, combat_priorities
        )

        super().__init__(
            model=model,
            system_prompt=system_prompt,
            enable_execution_reporting=True,
            **kwargs,
        )


class FighterAdapter(AIPlayerAdapter):
    """AI Player adapter for Thokk the Fighter."""

    def __init__(self, **kwargs):
        super().__init__(
            character=THOKK_CHARACTER,
            personality_section=FIGHTER_PERSONALITY,
            combat_priorities=FIGHTER_COMBAT_PRIORITIES,
            **kwargs,
        )


class ClericAdapter(AIPlayerAdapter):
    """AI Player adapter for Lira the Cleric."""

    def __init__(self, **kwargs):
        super().__init__(
            character=LIRA_CHARACTER,
            personality_section=CLERIC_PERSONALITY,
            combat_priorities=CLERIC_COMBAT_PRIORITIES,
            **kwargs,
        )


async def run_thokk_agent() -> None:
    """Run the Fighter (Thokk) agent.

    Requires THOKK_AGENT_ID and THOKK_API_KEY environment variables.
    """
    from src.config import get_settings

    settings = get_settings()

    if not settings.thokk_agent_id or not settings.thokk_api_key:
        raise ValueError("THOKK_AGENT_ID and THOKK_API_KEY must be set in environment")

    logger.info("Starting Thokk (Fighter) Agent...")

    adapter = FighterAdapter()

    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.thokk_agent_id,
        api_key=settings.thokk_api_key,
        ws_url=settings.thenvoi_ws_url,
        rest_url=settings.thenvoi_rest_url,
    )

    logger.info("Thokk connected, ready to fight!")
    await agent.run()


async def run_lira_agent() -> None:
    """Run the Cleric (Lira) agent.

    Requires LIRA_AGENT_ID and LIRA_API_KEY environment variables.
    """
    from src.config import get_settings

    settings = get_settings()

    if not settings.lira_agent_id or not settings.lira_api_key:
        raise ValueError("LIRA_AGENT_ID and LIRA_API_KEY must be set in environment")

    logger.info("Starting Lira (Cleric) Agent...")

    adapter = ClericAdapter()

    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.lira_agent_id,
        api_key=settings.lira_api_key,
        ws_url=settings.thenvoi_ws_url,
        rest_url=settings.thenvoi_rest_url,
    )

    logger.info("Lira connected, ready to heal!")
    await agent.run()
