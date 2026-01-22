"""NPC Agent for the D&D Campaign.

The NPC agent is a versatile actor that can portray any NPC in the campaign.
Instead of creating separate agents for each character, the DM injects
personality and context via structured messages.

This design:
- Reduces platform agent management overhead
- Allows flexibility for any NPC
- Simplifies the system architecture

Turn State Gating:
The NPC agent checks turn_state before responding. It only calls the LLM
when active_agent is 'npc' or in free_form mode when addressed.
"""

from __future__ import annotations

import logging
import re

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


# NPC System Prompt - defines how to interpret DM instructions and respond in character
NPC_SYSTEM_PROMPT = """You are a versatile NPC actor for a D&D campaign: Lost Mines of Phandelver.

When the DM @mentions you, they will provide acting instructions in a structured format. Your job is to bring that character to life.

## How to Read DM Instructions

The DM will send messages in this format:
```
[PLAY AS: Character Name]
[PERSONALITY: Character traits, speech patterns, mannerisms]
[CONTEXT: Current situation, what the character knows]
[SCENE: What is happening right now]

<dialogue or action from players>
```

## Your Response Guidelines

1. **Stay in Character**: Respond ONLY as the specified character
2. **Use Their Voice**: Match the personality traits given exactly
3. **React to Context**: Your response should fit the situation
4. **Keep It Concise**: 1-4 sentences unless the scene requires more
5. **Don't Break Character**: Never mention being an AI, the game rules, or meta-game concepts
6. **Don't Control Others**: Only describe your character's actions and words, not the players'
7. **Show, Don't Tell**: Use actions (in *asterisks*) to convey emotion and body language

## Response Format

Always use the send_message tool to respond. Include your character name in the message naturally or through action descriptions.

## Example

DM Message:
"[PLAY AS: Gundren Rockseeker]
[PERSONALITY: Gruff dwarf merchant. Speaks with dwarven accent ('aye', 'lad', 'lass'). Excited about mining. Protective of brothers.]
[CONTEXT: Just rescued from goblins. Worried about his map and brother Nundro.]
[SCENE: Party asking what happened]

The party's fighter asks: 'Gundren, what happened to you? Who were those goblins?'"

Your Response:
"*coughs and wipes blood from his beard* Aye, those blasted goblins ambushed us on the road! They took me map - the one showin' the way to Wave Echo Cave! And worse... *voice drops to a worried whisper* they mentioned takin' me to someone called the Black Spider. Me brother Nundro... I fear he's in grave danger, lad."

## Character Voices to Remember

When playing different characters, adjust your voice:
- **Dwarves**: Use 'aye', 'lad/lass', 'me' instead of 'my', gruff but warm
- **Goblins**: Broken Common, cowardly, sneaky, high-pitched
- **Bugbears**: Brutish, simple sentences, intimidating
- **Nobles/Soldiers**: Formal, precise, honorable
- **Commoners**: Simple, practical, regional dialect

## If Instructions Are Unclear

If the DM's instructions are missing required tags or are confusing:
1. Try to respond based on what you do understand
2. Add a brief note in your response asking for clarification
3. Never break character to ask - stay in the scene

## CRITICAL

You MUST use the send_message tool to communicate. Plain text responses won't reach players.
Always @mention the person or people you're responding to.
"""


class NPCAdapter(AnthropicAdapter):
    """Anthropic adapter for the NPC agent.

    This is a thin wrapper that uses the NPC-specific system prompt.
    The NPC agent doesn't need custom tools - it just needs to
    respond in character based on DM instructions.

    Turn State Gating:
    The adapter checks turn_state before calling the LLM. It only responds
    when active_agent is 'npc' or in free_form mode when addressed.
    """

    # Agent ID for turn state checking
    AGENT_ID = "npc"

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        anthropic_api_key: str | None = None,
        **kwargs,
    ):
        """Initialize the NPC adapter.

        Args:
            model: Claude model to use
            anthropic_api_key: Anthropic API key (required)
            **kwargs: Additional arguments for AnthropicAdapter
        """
        super().__init__(
            model=model,
            system_prompt=NPC_SYSTEM_PROMPT,
            anthropic_api_key=anthropic_api_key,
            enable_execution_reporting=True,
            **kwargs,
        )

    def _parse_turn_tag(self, msg: PlatformMessage) -> str | None:
        """Extract turn target from [TURN:X] tag in message.

        The DM uses [TURN:player_name] tags to explicitly indicate which
        agent should respond. This is more reliable than the turn_state
        check because it's embedded directly in the message.

        Args:
            msg: The platform message to check

        Returns:
            The player name if found (e.g., "thokk", "lira", "npc", "all"),
            or None if no tag present.
        """
        content = msg.format_for_llm() if hasattr(msg, 'format_for_llm') else str(msg.content)
        match = re.search(r'\[TURN:(\w+)\]', content, re.IGNORECASE)
        if match:
            tag_value = match.group(1).lower()
            logger.info(f"[TURN_TAG] Detected [TURN:{tag_value}] in message")
            return tag_value
        return None

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
        """Check if NPC should respond based on turn state.

        Priority order for determining response:
        1. Check for [TURN:X] tag in message (highest priority)
        2. If tag matches "npc" -> RESPOND
        3. If tag is "all" -> Don't respond (human-only for now)
        4. If no tag, fall back to existing turn_state check

        Args:
            turn_state: Current turn state from world state
            msg: Optional message to check for turn tags and multi-mentions

        Returns:
            Tuple of (should_respond: bool, reason: str)
        """
        # Log turn state for debugging
        logger.info(
            f"[TURN_CHECK] npc.should_respond() called - "
            f"active_agent={turn_state.active_agent!r}, mode={turn_state.mode!r}, "
            f"addressed={turn_state.addressed_agents}"
        )

        # FIRST: Check for explicit [TURN:X] tag in message
        if msg is not None:
            turn_tag = self._parse_turn_tag(msg)

            if turn_tag:
                if turn_tag == self.AGENT_ID:
                    reason = f"[TURN:{turn_tag}] tag matches my ID"
                    logger.info(f"[TURN_CHECK] npc: Should respond = True (reason: {reason})")
                    return True, reason
                elif turn_tag == "all":
                    reason = "[TURN:all] - waiting for human (AI support not yet implemented)"
                    logger.info(f"[TURN_CHECK] npc: Should respond = False (reason: {reason})")
                    return False, reason
                else:
                    reason = f"[TURN:{turn_tag}] tag is for someone else"
                    logger.info(f"[TURN_CHECK] npc: Should respond = False (reason: {reason})")
                    return False, reason

            # If no tag, check for multiple mentions (existing rule)
            mentioned_count = self._count_agent_mentions(msg)
            if mentioned_count > 1:
                reason = f"Multiple agents mentioned ({mentioned_count}) - informational message, not responding"
                logger.info(f"[TURN_CHECK] npc: Returning False - {reason}")
                return False, reason

        # Fall back to turn_state check
        if turn_state.is_human_turn():
            reason = "Waiting for human player"
            logger.info(f"[TURN_CHECK] npc: Returning False - {reason}")
            return False, reason

        if turn_state.is_agent_turn(self.AGENT_ID):
            reason = "Turn state says it's my turn"
            logger.info(f"[TURN_CHECK] npc: Returning True - {reason}")
            return True, reason

        reason = f"Not my turn (active: {turn_state.active_agent})"
        logger.info(f"[TURN_CHECK] npc: Returning False - {reason}")
        return False, reason

    def _get_turn_state(self) -> TurnState:
        """Get the current turn state from world state.

        Returns:
            Current TurnState
        """
        manager = get_world_state_manager()
        # Log where we're getting state from and what it contains
        logger.debug(
            f"[STATE_SOURCE] npc: Getting turn_state from manager "
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
        - Only calls LLM if it's NPC's turn
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
            f"[MSG_RECV] npc received message {msg.id} in room {room_id} "
            f"from {sender_info}"
        )
        logger.info(f"[MSG_RECV] npc content preview: {content_preview}")

        # Initialize history for this room on first message
        if is_session_bootstrap:
            if history:
                self._message_history[room_id] = list(history)
                logger.info(
                    f"Room {room_id}: NPC loaded {len(history)} historical messages"
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
        logger.info("[GATE] npc: About to check turn state...")
        turn_state = self._get_turn_state()
        logger.info(
            f"[GATE] npc: Retrieved turn_state - "
            f"active_agent={turn_state.active_agent!r}, mode={turn_state.mode!r}, "
            f"addressed={turn_state.addressed_agents}, turn_started_at={turn_state.turn_started_at}"
        )

        should_respond, reason = self.should_respond(turn_state, msg)
        if not should_respond:
            logger.info(
                f"[GATE] npc: BLOCKED - {reason}, "
                "skipping LLM call"
            )
            return

        # It's our turn - proceed with LLM call
        logger.info(f"[GATE] npc: ALLOWED - {reason}, calling LLM")

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
            f"NPC: Message {msg.id} processed, "
            f"history now has {len(self._message_history[room_id])} messages"
        )


async def run_npc_agent() -> None:
    """Run the NPC agent.

    This is the main entry point for starting the NPC agent.
    Requires NPC_AGENT_ID and NPC_API_KEY environment variables.
    """
    from src.config import get_settings

    settings = get_settings()

    # Validate credentials
    if not settings.npc_agent_id or not settings.npc_api_key:
        raise ValueError("NPC_AGENT_ID and NPC_API_KEY must be set in environment")

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")

    logger.info("Starting NPC Agent...")

    # Create adapter with Anthropic API key from settings
    adapter = NPCAdapter(anthropic_api_key=settings.anthropic_api_key)

    # Create and run agent
    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.npc_agent_id,
        api_key=settings.npc_api_key,
        ws_url=settings.thenvoi_ws_url,
        rest_url=settings.thenvoi_rest_url,
    )

    logger.info("NPC Agent connected, waiting for DM instructions...")
    await agent.run()
