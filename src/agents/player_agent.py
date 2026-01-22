"""AI Player Agents for the D&D Campaign.

This module provides AI-controlled party members that play alongside
the human player. Each AI player has distinct personality, combat
priorities, and decision-making patterns.

Current AI Players:
- Thokk: Half-Orc Fighter - direct, combat-focused, protective
- Lira: Human Cleric (Life) - supportive, wise, healing-focused

Turn State Gating:
AI players check the turn_state in WorldState before responding.
They only call the LLM when it's their turn, preventing response cascades.
"""

from __future__ import annotations

import logging
from typing import Any

from thenvoi import Agent
from thenvoi.adapters import AnthropicAdapter
from thenvoi.core.protocols import AgentToolsProtocol
from thenvoi.core.types import PlatformMessage
from thenvoi.converters.anthropic import AnthropicMessages

from src.game.models import TurnState
from src.tools.world_state import get_world_state_manager

logger = logging.getLogger(__name__)


# Known agent names for multi-mention detection
KNOWN_AGENT_NAMES = ["thokk", "lira", "vex", "gundren", "sildar", "klarg", "npc"]


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

    Turn State Gating:
    The adapter checks turn_state before calling the LLM. If it's not
    this agent's turn, the message is added to history but no LLM call
    is made. This prevents response cascades while preserving context.
    """

    def __init__(
        self,
        character: dict[str, Any],
        personality_section: str,
        combat_priorities: str,
        agent_id: str,
        model: str = "claude-sonnet-4-5-20250929",
        anthropic_api_key: str | None = None,
        **kwargs,
    ):
        """Initialize the AI player adapter.

        Args:
            character: Character data dictionary
            personality_section: Character-specific personality text
            combat_priorities: Character-specific combat priorities
            agent_id: Unique identifier for this agent ('thokk', 'lira')
            model: Claude model to use
            anthropic_api_key: Anthropic API key (required)
            **kwargs: Additional arguments for AnthropicAdapter
        """
        self.character = character
        self.agent_id = agent_id
        system_prompt = build_player_system_prompt(
            character, personality_section, combat_priorities
        )

        super().__init__(
            model=model,
            system_prompt=system_prompt,
            anthropic_api_key=anthropic_api_key,
            enable_execution_reporting=True,
            **kwargs,
        )

    def _count_agent_mentions(self, msg: PlatformMessage) -> int:
        """Count how many known agent names are mentioned in the message.

        Args:
            msg: The platform message to check

        Returns:
            Number of distinct agent names mentioned
        """
        # Get message content - try different attributes that might contain the text
        content = ""
        if hasattr(msg, 'content'):
            content = str(msg.content).lower()
        elif hasattr(msg, 'text'):
            content = str(msg.text).lower()

        # Also check format_for_llm output
        try:
            llm_content = msg.format_for_llm().lower()
            content = f"{content} {llm_content}"
        except Exception:
            pass

        mentioned = set()
        for name in KNOWN_AGENT_NAMES:
            if name.lower() in content:
                mentioned.add(name)

        return len(mentioned)

    def should_respond(self, turn_state: TurnState, msg: PlatformMessage | None = None) -> tuple[bool, str]:
        """Check if this agent should respond based on turn state.

        This prevents response cascades by only allowing agents to
        call the LLM when the DM has explicitly set their turn.

        Args:
            turn_state: Current turn state from world state
            msg: Optional message to check for multi-mentions

        Returns:
            Tuple of (should_respond: bool, reason: str)
        """
        # Log turn state for debugging
        logger.info(
            f"[TURN_CHECK] {self.agent_id}.should_respond() called - "
            f"active_agent={turn_state.active_agent!r}, mode={turn_state.mode!r}, "
            f"addressed={turn_state.addressed_agents}"
        )

        # NEW: Multi-mention suppression - if multiple agents mentioned, this is informational
        if msg is not None:
            mentioned_count = self._count_agent_mentions(msg)
            if mentioned_count > 1:
                reason = f"Multiple agents mentioned ({mentioned_count}) - informational message, not responding"
                logger.info(f"[TURN_CHECK] {self.agent_id}: Returning False - {reason}")
                return False, reason

        # Always yield to human interjections
        if turn_state.is_human_turn():
            reason = "it's human's turn"
            logger.info(f"[TURN_CHECK] {self.agent_id}: Returning False - {reason}")
            return False, reason

        # Check if it's this agent's turn
        is_my_turn = turn_state.is_agent_turn(self.agent_id)
        if is_my_turn:
            reason = f"active_agent={turn_state.active_agent!r} matches {self.agent_id!r}"
            logger.info(f"[TURN_CHECK] {self.agent_id}: Returning True - {reason}")
            return True, reason
        else:
            reason = f"active_agent={turn_state.active_agent!r} does not match {self.agent_id!r}"
            logger.info(f"[TURN_CHECK] {self.agent_id}: Returning False - {reason}")
            return False, reason

    def _get_turn_state(self) -> TurnState:
        """Get the current turn state from world state.

        Returns:
            Current TurnState
        """
        manager = get_world_state_manager()
        # Log where we're getting state from and what it contains
        logger.debug(
            f"[STATE_SOURCE] {self.agent_id}: Getting turn_state from manager "
            f"(state_file={manager.state_file}, id={id(manager)})"
        )
        return manager.state.turn_state

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: AnthropicMessages,
        participants_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        """Handle incoming message with turn state gating.

        Key behavior:
        - Always adds message to history (preserves context)
        - Only calls LLM if it's this agent's turn
        - Skips LLM call silently if not their turn
        """
        # Log message receipt with sender info and content preview
        sender_info = getattr(msg, 'sender', None) or getattr(msg, 'author', 'unknown')
        content_preview = ""
        try:
            content_preview = msg.format_for_llm()[:100] + "..." if len(msg.format_for_llm()) > 100 else msg.format_for_llm()
        except Exception:
            content_preview = "[unable to preview]"
        logger.info(
            f"[MSG_RECV] {self.agent_id} received message {msg.id} in room {room_id} "
            f"from {sender_info}"
        )
        logger.info(f"[MSG_RECV] {self.agent_id} content preview: {content_preview}")

        # Initialize history for this room on first message
        if is_session_bootstrap:
            if history:
                self._message_history[room_id] = list(history)
                logger.info(
                    f"Room {room_id}: {self.agent_id} loaded {len(history)} historical messages"
                )
            else:
                self._message_history[room_id] = []
        elif room_id not in self._message_history:
            self._message_history[room_id] = []

        # Inject participants message if changed
        if participants_msg:
            self._message_history[room_id].append({
                "role": "user",
                "content": f"[System]: {participants_msg}",
            })

        # Always add current message to history (preserves context)
        user_message = msg.format_for_llm()
        self._message_history[room_id].append({
            "role": "user",
            "content": user_message,
        })

        # GATE: Check turn state before calling LLM
        logger.info(f"[GATE] {self.agent_id}: About to check turn state...")
        turn_state = self._get_turn_state()
        logger.info(
            f"[GATE] {self.agent_id}: Retrieved turn_state - "
            f"active_agent={turn_state.active_agent!r}, mode={turn_state.mode!r}, "
            f"addressed={turn_state.addressed_agents}, turn_started_at={turn_state.turn_started_at}"
        )

        should_respond, reason = self.should_respond(turn_state, msg)
        if not should_respond:
            logger.info(
                f"[GATE] {self.agent_id}: BLOCKED - {reason}, "
                f"skipping LLM call"
            )
            return

        # It's our turn - proceed with LLM call
        logger.info(f"[GATE] {self.agent_id}: ALLOWED - {reason}, calling LLM")

        # Get tool schemas
        tool_schemas = tools.get_anthropic_tool_schemas()

        # Tool loop
        while True:
            try:
                response = await self._call_anthropic(
                    messages=self._message_history[room_id],
                    tools=tool_schemas,
                )
            except Exception as e:
                logger.error(f"Error calling Anthropic: {e}", exc_info=True)
                await self._report_error(tools, str(e))
                raise

            # Check for tool use
            if response.stop_reason != "tool_use":
                text_content = self._extract_text_content(response.content)
                if text_content:
                    self._message_history[room_id].append({
                        "role": "assistant",
                        "content": text_content,
                    })
                break

            # Add assistant response with tool_use blocks to history
            serialized_content = self._serialize_content_blocks(response.content)
            self._message_history[room_id].append({
                "role": "assistant",
                "content": serialized_content,
            })

            # Process tool calls
            tool_results = await self._process_tool_calls(response, tools)

            # Add tool results to history
            self._message_history[room_id].append({
                "role": "user",
                "content": tool_results,
            })

        logger.debug(
            f"{self.agent_id}: Message {msg.id} processed, "
            f"history now has {len(self._message_history[room_id])} messages"
        )


class FighterAdapter(AIPlayerAdapter):
    """AI Player adapter for Thokk the Fighter."""

    def __init__(self, **kwargs):
        super().__init__(
            character=THOKK_CHARACTER,
            personality_section=FIGHTER_PERSONALITY,
            combat_priorities=FIGHTER_COMBAT_PRIORITIES,
            agent_id="thokk",
            **kwargs,
        )


class ClericAdapter(AIPlayerAdapter):
    """AI Player adapter for Lira the Cleric."""

    def __init__(self, **kwargs):
        super().__init__(
            character=LIRA_CHARACTER,
            personality_section=CLERIC_PERSONALITY,
            combat_priorities=CLERIC_COMBAT_PRIORITIES,
            agent_id="lira",
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

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")

    logger.info("Starting Thokk (Fighter) Agent...")

    adapter = FighterAdapter(anthropic_api_key=settings.anthropic_api_key)

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

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")

    logger.info("Starting Lira (Cleric) Agent...")

    adapter = ClericAdapter(anthropic_api_key=settings.anthropic_api_key)

    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.lira_agent_id,
        api_key=settings.lira_api_key,
        ws_url=settings.thenvoi_ws_url,
        rest_url=settings.thenvoi_rest_url,
    )

    logger.info("Lira connected, ready to heal!")
    await agent.run()
