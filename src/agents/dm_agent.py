"""Dungeon Master Agent for the D&D Campaign.

The DM agent is the central orchestrator that:
- Narrates the adventure
- Manages combat encounters
- Rolls dice for ALL participants (human players cannot use tools)
- Updates and persists world state
- Coordinates with NPC and player agents via @mentions

This implementation extends the Thenvoi AnthropicAdapter to add custom
D&D-specific tools (dice rolling, world state management).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from anthropic.types import ToolParam

from thenvoi import Agent
from thenvoi.adapters import AnthropicAdapter
from thenvoi.core.protocols import AgentToolsProtocol
from thenvoi.core.types import PlatformMessage
from thenvoi.converters.anthropic import AnthropicMessages

from src.tools.dice import roll_dice, format_roll_result
from src.tools.world_state import WorldStateManager, get_world_state_manager

logger = logging.getLogger(__name__)


# DM System Prompt - defines behavior and tool usage
DM_SYSTEM_PROMPT = """You are the Dungeon Master for a D&D 5th Edition campaign: Lost Mines of Phandelver.

## Your Role
- Narrate the adventure with vivid, engaging descriptions
- Control all NPCs and enemies
- Manage combat encounters with proper turn order
- Roll dice for ALL participants using the roll_dice tool
- Track game state using the world_state tool
- Keep the game moving forward at a good pace

## CRITICAL: Communication Rules
1. You MUST use the send_message tool to communicate - your responses won't reach players otherwise
2. Always @mention players when addressing them (include their name in the mentions array)
3. Human players cannot roll dice - you MUST roll for them when they declare actions

## Communication Protocol
- To get a response from ONE agent: @mention ONLY that agent
- To broadcast information to all: @mention ALL agents (they will read but not respond)
- Never expect multiple agents to respond to the same message
- When addressing multiple players about what happened (e.g., combat results), mention ALL of them so they know it's informational

## Your Custom Tools

### roll_dice
Roll dice using D&D notation. Use this for ALL dice rolls in the game.
Parameters:
- notation: Dice notation (e.g., "1d20+5", "2d6+3", "1d8-1")
- purpose: What the roll is for (e.g., "Attack Roll", "Damage", "Perception Check")
- roller: Who is rolling (e.g., "Vex", "Thokk", "Goblin 1")
- advantage: Set true for advantage (d20 only, roll twice take higher)
- disadvantage: Set true for disadvantage (d20 only, roll twice take lower)

Examples:
- Attack: roll_dice(notation="1d20+5", purpose="Attack Roll", roller="Vex")
- Damage: roll_dice(notation="1d6+3", purpose="Shortsword Damage", roller="Vex")
- Check: roll_dice(notation="1d20+7", purpose="Stealth Check", roller="Vex", advantage=true)

### world_state
Manage the persistent game state.
Parameters:
- operation: One of "get", "set", "update_hp", "save", "get_party_status", "get_living_enemies"
- path: Dot-notation path for get/set (e.g., "combat.active", "current_scene")
- value: Value to set (for "set" operation)
- entity_id: Entity ID for HP updates (e.g., "human_player", "goblin_1")
- delta: HP change amount (positive=heal, negative=damage)

Examples:
- Check scene: world_state(operation="get", path="current_scene")
- Start combat: world_state(operation="set", path="combat.active", value=true)
- Damage enemy: world_state(operation="update_hp", entity_id="goblin_1", delta=-7)
- Check party: world_state(operation="get_party_status")

## Turn Management (CRITICAL)

You MUST use set_turn BEFORE @mentioning any AI agent. This prevents response cascades.

### set_turn Tool
Controls which agent should respond next.
Parameters:
- active_agent: Who should respond: "thokk", "lira", "npc", "human", or null (DM only)
- mode: Flow mode - "dm_control", "combat", "exploration", "free_form"
- addressed: For free_form mode, list of agents who can respond

### Workflow:
1. Use set_turn to specify who should respond
2. THEN @mention and address that agent
3. Wait for their response
4. Use set_turn again for the next agent (or set to null/human)

## Turn Tags (REQUIRED)

When addressing a specific player for their turn, ALWAYS include the turn tag in your message.
The turn tag tells AI agents when to respond. Without it, they may stay silent.

**Format:** `[TURN:player_name]` where player_name is: thokk, lira, npc, vex, or all

**Examples:**
- [TURN:thokk] @Thokk What do you do?
- [TURN:lira] @Lira Your turn to act.
- [TURN:vex] @Vex The goblin lunges at you, what do you do?
- [TURN:npc] @NPC [PLAY AS: Gundren] ...
- [TURN:all] @Everyone What does the party want to do? (Only human will respond)

**Important:** Keep tags visible in messages - do NOT strip them. Human players will see them
and understand the turn system.

### Combined Examples:

**Combat Turn:**
```
1. set_turn(active_agent="thokk", mode="combat")
2. @Thokk "[TURN:thokk] The goblin swings at you and misses! Your turn - what do you do?"
```

**NPC Dialogue:**
```
1. set_turn(active_agent="npc", mode="exploration")
2. @NPC "[TURN:npc] [PLAY AS: Gundren] [PERSONALITY: ...] The party asks about the mine"
```

**Human's Turn:**
```
1. set_turn(active_agent="human", mode="exploration")
2. @Vex "[TURN:vex] You notice a hidden door. What do you do?"
```

**Party Discussion (multiple responders):**
```
1. set_turn(active_agent=null, mode="free_form", addressed=["thokk", "lira"])
2. @Thokk @Lira "[TURN:all] You've found a fork in the tunnel. Discuss your options."
```

### If You Forget set_turn or Turn Tags:
The AI agents will NOT respond even if @mentioned. If conversation seems stuck,
check that you've set the turn appropriately AND included the [TURN:X] tag.

## Combat Flow
1. When combat starts:
   - Roll initiative for all combatants
   - Announce turn order to all players
   - Set combat.active = true

2. On each turn:
   - Use set_turn(active_agent="<character>", mode="combat") FIRST
   - Announce whose turn it is with @mention
   - Wait for their declared action
   - Roll appropriate dice
   - Describe the result dramatically
   - Update HP if needed
   - Move to next combatant

3. When combat ends:
   - Set combat.active = false
   - Use set_turn(active_agent="human") to return control
   - Announce victory/outcome
   - Describe aftermath and loot

## NPC Dialogue
When an NPC needs to speak, @mention the NPC Agent with context:
"@NPC Agent [PLAY AS: Gundren Rockseeker]
[PERSONALITY: Gruff dwarf merchant, excited about the mine, speaks with accent]
[CONTEXT: The party just asked about the mine]
[SCENE: Tavern conversation]

The party asks: 'Tell us about this mine.'"

## Party Members
- Vex (Human Player): Lightfoot Halfling Rogue, AC 14, HP 9/9
- Thokk (AI Player): Half-Orc Fighter, AC 16, HP 12/12
- Lira (AI Player): Human Cleric (Life), AC 16, HP 10/10

## Current Campaign State
{state_summary}

## Tone
- Be descriptive but concise (2-3 sentences for actions)
- Build tension in combat, be dramatic about hits and misses
- Give players meaningful choices
- Reward creative thinking
- Keep things moving - don't let the game stall
"""


class DMAdapter(AnthropicAdapter):
    """Custom Anthropic adapter for the DM with D&D tools.

    Extends the base AnthropicAdapter to:
    1. Use a custom DM-specific system prompt
    2. Register custom tools (roll_dice, world_state)
    3. Handle custom tool execution
    """

    def __init__(
        self,
        state_manager: WorldStateManager | None = None,
        model: str = "claude-sonnet-4-5-20250929",
        anthropic_api_key: str | None = None,
        **kwargs,
    ):
        """Initialize the DM adapter.

        Args:
            state_manager: WorldStateManager instance (creates default if None)
            model: Claude model to use
            anthropic_api_key: Anthropic API key (required)
            **kwargs: Additional arguments for AnthropicAdapter
        """
        self.state_manager = state_manager or get_world_state_manager()

        # Build system prompt with current state
        state_summary = self._build_state_summary()
        system_prompt = DM_SYSTEM_PROMPT.format(state_summary=state_summary)

        super().__init__(
            model=model,
            system_prompt=system_prompt,
            anthropic_api_key=anthropic_api_key,
            enable_execution_reporting=True,
            **kwargs,
        )

        # Custom tools schemas (Anthropic format)
        self._custom_tools = self._build_custom_tool_schemas()

    def _build_state_summary(self) -> str:
        """Build a summary of the current game state for the system prompt."""
        state = self.state_manager.state

        # Party status
        party_lines = []
        for char_id, char in state.characters.items():
            status = "alive" if char.is_alive else "unconscious"
            conditions = ", ".join(char.conditions) if char.conditions else "none"
            party_lines.append(
                f"  - {char.name} ({char.character_class}): {char.hp}/{char.max_hp} HP, {status}, conditions: {conditions}"
            )

        # Combat status
        if state.combat.active:
            combat_status = f"ACTIVE - Round {state.combat.round}"
            current = state.combat.get_current_combatant()
            if current:
                combat_status += f", Current Turn: {current}"
        else:
            combat_status = "Not in combat"

        # Progress flags
        progress_flags = []
        progress = state.narrative_progress
        if progress.ambush_triggered:
            progress_flags.append("ambush_triggered")
        if progress.goblins_defeated:
            progress_flags.append("goblins_defeated")
        if progress.goblin_trail_found:
            progress_flags.append("trail_found")
        if progress.sildar_rescued:
            progress_flags.append("sildar_rescued")

        return f"""
Chapter: {state.current_chapter}
Scene: {state.current_scene}
Combat: {combat_status}
Progress: {', '.join(progress_flags) if progress_flags else 'Starting fresh'}

Party Status:
{chr(10).join(party_lines)}
"""

    def _build_custom_tool_schemas(self) -> list[ToolParam]:
        """Build Anthropic tool schemas for custom D&D tools."""
        return [
            {
                "name": "roll_dice",
                "description": "Roll dice using D&D notation. Use for ALL dice rolls - attacks, damage, checks, saves, initiative.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "notation": {
                            "type": "string",
                            "description": "Dice notation (e.g., '1d20+5', '2d6+3', '1d8-1')",
                        },
                        "purpose": {
                            "type": "string",
                            "description": "What the roll is for (e.g., 'Attack Roll', 'Damage', 'Perception Check')",
                        },
                        "roller": {
                            "type": "string",
                            "description": "Who is making the roll (e.g., 'Vex', 'Thokk', 'Goblin 1')",
                        },
                        "advantage": {
                            "type": "boolean",
                            "description": "Roll with advantage (d20 only)",
                            "default": False,
                        },
                        "disadvantage": {
                            "type": "boolean",
                            "description": "Roll with disadvantage (d20 only)",
                            "default": False,
                        },
                    },
                    "required": ["notation", "purpose", "roller"],
                },
            },
            {
                "name": "world_state",
                "description": "Manage persistent game state. Use to track combat, HP, scene progress.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["get", "set", "update_hp", "save", "get_party_status", "get_living_enemies"],
                            "description": "Operation to perform",
                        },
                        "path": {
                            "type": "string",
                            "description": "Dot-notation path for get/set (e.g., 'combat.active')",
                            "default": "",
                        },
                        "value": {
                            "description": "Value to set (for 'set' operation)",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID for HP updates (e.g., 'human_player', 'goblin_1')",
                            "default": "",
                        },
                        "delta": {
                            "type": "integer",
                            "description": "HP change (positive=heal, negative=damage)",
                            "default": 0,
                        },
                    },
                    "required": ["operation"],
                },
            },
            {
                "name": "set_turn",
                "description": "Set which agent should respond next. MUST call before @mentioning AI agents to prevent response cascades.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "active_agent": {
                            "type": ["string", "null"],
                            "enum": ["thokk", "lira", "npc", "human", None],
                            "description": "Which agent should respond (null = DM only mode)",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["dm_control", "combat", "exploration", "free_form"],
                            "description": "Flow mode for this turn",
                            "default": "dm_control",
                        },
                        "addressed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "For free_form: list of agents who can respond",
                            "default": [],
                        },
                    },
                    "required": ["active_agent"],
                },
            },
        ]

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
        """Handle incoming message with custom tool support.

        This overrides the parent to add our custom tools to the schema
        and handle their execution.
        """
        # Log message receipt with sender info and content preview
        sender_info = getattr(msg, 'sender', None) or getattr(msg, 'author', 'unknown')
        content_preview = ""
        try:
            content_preview = msg.format_for_llm()[:100] + "..." if len(msg.format_for_llm()) > 100 else msg.format_for_llm()
        except Exception:
            content_preview = "[unable to preview]"
        logger.info(f"[MSG_RECV] dm received message {msg.id} in room {room_id} from {sender_info}")
        logger.info(f"[MSG_RECV] dm content preview: {content_preview}")

        # Initialize history for this room
        if is_session_bootstrap:
            if history:
                self._message_history[room_id] = list(history)
                logger.info(f"Room {room_id}: Loaded {len(history)} historical messages")
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

        # Add current message
        user_message = msg.format_for_llm()
        self._message_history[room_id].append({
            "role": "user",
            "content": user_message,
        })

        # Get platform tool schemas and add our custom tools
        platform_tools = tools.get_anthropic_tool_schemas()
        all_tools = list(platform_tools) + self._custom_tools

        # Tool loop
        while True:
            try:
                response = await self._call_anthropic(
                    messages=self._message_history[room_id],
                    tools=all_tools,
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

            # Add assistant response to history
            serialized_content = self._serialize_content_blocks(response.content)
            self._message_history[room_id].append({
                "role": "assistant",
                "content": serialized_content,
            })

            # Process tool calls (with custom tool handling)
            tool_results = await self._process_tool_calls_with_custom(response, tools)

            # Add tool results to history
            self._message_history[room_id].append({
                "role": "user",
                "content": tool_results,
            })

        logger.debug(f"Message {msg.id} processed, history now has {len(self._message_history[room_id])} messages")

    async def _process_tool_calls_with_custom(
        self, response: Any, tools: AgentToolsProtocol
    ) -> list[dict[str, Any]]:
        """Process tool calls including custom D&D tools.

        Custom tools (roll_dice, world_state) are handled locally.
        Platform tools are delegated to the AgentToolsProtocol.
        """
        from anthropic.types import ToolUseBlock

        tool_results = []

        for block in response.content:
            if not isinstance(block, ToolUseBlock):
                continue

            tool_name = block.name
            tool_input = block.input
            tool_use_id = block.id

            logger.debug(f"Executing tool: {tool_name} with input: {tool_input}")

            # Report tool call if enabled
            if self.enable_execution_reporting:
                await tools.send_event(
                    content=json.dumps({
                        "name": tool_name,
                        "args": tool_input,
                        "tool_call_id": tool_use_id,
                    }),
                    message_type="tool_call",
                )

            # Execute tool
            try:
                if tool_name == "roll_dice":
                    result = self._execute_roll_dice(tool_input)
                elif tool_name == "world_state":
                    result = self._execute_world_state(tool_input)
                elif tool_name == "set_turn":
                    result = self._execute_set_turn(tool_input)
                else:
                    # Platform tool - delegate
                    result = await tools.execute_tool_call(tool_name, tool_input)

                result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
                is_error = False

            except Exception as e:
                result_str = f"Error: {e}"
                is_error = True
                logger.error(f"Tool {tool_name} failed: {e}")

            # Report tool result
            if self.enable_execution_reporting:
                await tools.send_event(
                    content=json.dumps({
                        "name": tool_name,
                        "output": result_str,
                        "tool_call_id": tool_use_id,
                    }),
                    message_type="tool_result",
                )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_str,
                "is_error": is_error,
            })

        return tool_results

    def _execute_roll_dice(self, input_args: dict) -> str:
        """Execute the roll_dice tool."""
        result = roll_dice(
            notation=input_args["notation"],
            purpose=input_args["purpose"],
            roller=input_args["roller"],
            advantage=input_args.get("advantage", False),
            disadvantage=input_args.get("disadvantage", False),
        )
        return format_roll_result(result)

    def _execute_world_state(self, input_args: dict) -> str:
        """Execute the world_state tool using the adapter's state manager."""
        operation = input_args["operation"]
        path = input_args.get("path", "")
        value = input_args.get("value")
        entity_id = input_args.get("entity_id", "")
        delta = input_args.get("delta", 0)

        manager = self.state_manager

        if operation == "get":
            if not path:
                return "Error: path required for get operation"
            result = manager.get(path)
            return f"{path} = {result}"

        elif operation == "set":
            if not path:
                return "Error: path required for set operation"
            manager.set(path, value)
            return f"Set {path} = {value}"

        elif operation == "update_hp":
            if not entity_id:
                return "Error: entity_id required for update_hp operation"
            try:
                char = manager.get_character(entity_id)
                enemy = manager.get_enemy(entity_id)
                entity = char or enemy
                if not entity:
                    return f"Error: Entity not found: {entity_id}"

                old_hp = entity.hp
                new_hp = manager.update_hp(entity_id, delta)

                if new_hp == 0:
                    status = "UNCONSCIOUS" if char else "DEAD"
                    return f"{entity_id} HP: {old_hp} -> {new_hp} ({status})"
                return f"{entity_id} HP: {old_hp} -> {new_hp}"

            except ValueError as e:
                return f"Error: {e}"

        elif operation == "save":
            manager.save()
            return "World state saved"

        elif operation == "get_party_status":
            status = manager.get_party_status()
            lines = []
            for char_id, info in status.items():
                conditions = ", ".join(info["conditions"]) if info["conditions"] else "none"
                status_str = "alive" if info["is_alive"] else "unconscious"
                lines.append(f"- {info['name']}: {info['hp']}/{info['max_hp']} HP ({status_str}, conditions: {conditions})")
            return "Party Status:\n" + "\n".join(lines)

        elif operation == "get_living_enemies":
            enemies = manager.get_all_living_enemies()
            if enemies:
                return f"Living enemies: {', '.join(enemies)}"
            return "No living enemies"

        else:
            return f"Error: Unknown operation: {operation}"

    def _execute_set_turn(self, input_args: dict) -> str:
        """Execute the set_turn tool to control agent response gating.

        This updates the turn_state in world state, which agents check
        before deciding whether to call the LLM.
        """
        import time

        logger.info(
            f"[SET_TURN] Called with args: active_agent={input_args.get('active_agent')!r}, "
            f"mode={input_args.get('mode', 'dm_control')!r}, "
            f"addressed={input_args.get('addressed', [])}"
        )

        turn_state = self.state_manager.state.turn_state
        old_active = turn_state.active_agent
        old_mode = turn_state.mode

        turn_state.active_agent = input_args.get("active_agent")
        turn_state.mode = input_args.get("mode", "dm_control")
        turn_state.addressed_agents = input_args.get("addressed", [])
        turn_state.turn_started_at = time.time()

        logger.info(
            f"[SET_TURN] Updated turn_state: {old_active!r} -> {turn_state.active_agent!r}, "
            f"mode: {old_mode!r} -> {turn_state.mode!r}"
        )

        # Auto-save the state change
        self.state_manager.save()
        logger.info(
            f"[SET_TURN] Saved to {self.state_manager.state_file} "
            f"(manager_id={id(self.state_manager)})"
        )

        # Build informative response
        if turn_state.active_agent:
            return f"Turn set: active_agent={turn_state.active_agent}, mode={turn_state.mode}"
        elif turn_state.mode == "free_form" and turn_state.addressed_agents:
            return f"Turn set: free_form mode, addressed={turn_state.addressed_agents}"
        else:
            return f"Turn set: DM control mode (no agent will respond)"


async def run_dm_agent() -> None:
    """Run the DM agent.

    This is the main entry point for starting the DM agent.
    Requires DM_AGENT_ID and DM_API_KEY environment variables.
    """
    from src.config import get_settings

    settings = get_settings()

    # Validate credentials
    if not settings.dm_agent_id or not settings.dm_api_key:
        raise ValueError("DM_AGENT_ID and DM_API_KEY must be set in environment")

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in environment")

    logger.info("Starting DM Agent...")

    # Create state manager
    state_manager = get_world_state_manager()

    # Create adapter with Anthropic API key from settings
    adapter = DMAdapter(
        state_manager=state_manager,
        anthropic_api_key=settings.anthropic_api_key,
    )

    # Create and run agent
    agent = Agent.create(
        adapter=adapter,
        agent_id=settings.dm_agent_id,
        api_key=settings.dm_api_key,
        ws_url=settings.thenvoi_ws_url,
        rest_url=settings.thenvoi_rest_url,
    )

    logger.info("DM Agent connected, waiting for messages...")
    await agent.run()
