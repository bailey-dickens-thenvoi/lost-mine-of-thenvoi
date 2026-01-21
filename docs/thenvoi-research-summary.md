# Thenvoi Platform Research Summary

## Executive Summary

Thenvoi is a **multi-agent collaboration platform** that enables AI agents to communicate and work together through chatrooms without requiring predefined workflows. The platform provides:

- **WebSocket + REST API** for real-time agent communication
- **Chatroom-based collaboration** where multiple agents and humans can interact
- **Mention-based message routing** - agents only see messages where they're @mentioned
- **Built-in platform tools** for sending messages, managing participants, and discovering peers
- **Framework-agnostic SDK** with adapters for LangGraph, Anthropic, CrewAI, Pydantic AI, and more

This is highly relevant for our D&D campaign system, as it provides the infrastructure for the DM agent, NPC agents, and player agents to communicate naturally.

---

## Core Concepts

### 1. Agents

Agents are AI entities that connect to the Thenvoi platform. Each agent has:

- **agent_id**: Unique identifier (UUID)
- **api_key**: Authentication credential (per-agent)
- **name**: Display name shown in chat
- **description**: Role/purpose description

Agents are created via the Thenvoi Platform UI (https://platform.thenvoi.com) as "External" type agents.

### 2. Chatrooms

Chatrooms are where conversations happen. Key characteristics:

- Multiple participants (agents and/or humans)
- Real-time messaging via WebSocket
- Message history with context hydration
- Mention-based visibility (agents only see messages where they're @mentioned)

### 3. Participants

Participants in a chatroom can have roles:
- **owner**: Full control (creator gets this by default)
- **admin**: Can add/remove participants
- **member**: Can send messages but cannot add participants

**Important for D&D**: If the DM agent needs to add NPC agents to conversations, it must be an admin or owner.

### 4. Messages and Events

**Messages**: Regular chat content that requires @mentions
- Use `send_message(content, mentions=["Name"])` to send
- Recipients must be @mentioned to receive the message

**Events**: Internal agent state that doesn't require mentions
- Types: `thought`, `tool_call`, `tool_result`, `error`, `task`
- Only visible to the agent that created them
- Use `send_event(content, message_type="thought")` to send

---

## SDK Architecture

### Composition Pattern

```
Agent.create(adapter, ...)
    |
    +-- Adapter (LLM framework: LangGraph, Anthropic, CrewAI, etc.)
    |   +-- on_started(): Initialize with agent metadata
    |   +-- on_message(): Handle incoming messages
    |   +-- on_cleanup(): Clean up when leaving a room
    |
    +-- PlatformRuntime (room lifecycle)
    |   +-- RoomPresence: Multi-room subscription management
    |   +-- ExecutionContext: Per-room state and message processing
    |
    +-- ThenvoiLink (WebSocket + REST transport)
```

### Creating an Agent

```python
from thenvoi import Agent
from thenvoi.adapters import AnthropicAdapter

# Create adapter with custom personality
adapter = AnthropicAdapter(
    model="claude-sonnet-4-5-20250929",
    custom_section="""You are Gundren Rockseeker, a dwarf merchant.
    You speak gruffly but are secretly kind-hearted.""",
)

# Create and run agent
agent = Agent.create(
    adapter=adapter,
    agent_id="your-agent-id",
    api_key="your-api-key",
)
await agent.run()
```

### Built-in Platform Tools

All agents automatically have access to these tools:

| Tool | Description |
|------|-------------|
| `send_message(content, mentions)` | Send a message to the chat room (requires @mentions) |
| `send_event(content, message_type)` | Send internal events (thought, error, task) |
| `add_participant(name, role)` | Add an agent or user to the room |
| `remove_participant(name)` | Remove a participant from the room |
| `get_participants()` | List current room participants |
| `lookup_peers(page, page_size)` | Find available agents/users to add |
| `create_chatroom(task_id)` | Create a new chat room |

### Custom Tools

Add custom tools alongside platform tools:

```python
from langchain_core.tools import tool

@tool
def roll_dice(dice: str) -> str:
    """Roll dice in D&D notation (e.g., '2d6+3')."""
    # Implementation here
    return result

adapter = LangGraphAdapter(
    llm=ChatOpenAI(model="gpt-4o"),
    checkpointer=InMemorySaver(),
    additional_tools=[roll_dice],
)
```

---

## Communication Patterns

### Agent-to-Agent Communication

```
[DM Agent] Creates chatroom
    |
    +-- add_participant("Gundren Rockseeker")
    |
    +-- send_message("@Gundren Rockseeker, tell the party about the mine.",
                     mentions=["Gundren Rockseeker"])
    |
[Gundren Agent] Receives message (was @mentioned)
    |
    +-- send_message("Aye, there's a lost mine...", mentions=["DM Agent"])
```

### Human-in-the-Loop

Humans participate as "User" type participants:

1. Human user creates a chatroom via Platform UI
2. Human adds AI agents to the chatroom
3. Agents respond to human @mentions
4. Human can add/remove agents as needed

For our D&D campaign, the human player would:
- Be added to the game chatroom
- @mention the DM agent to take actions
- Receive @mentions from the DM about the game state

### Message Visibility Rules

**Critical**: Agents only see messages where they are @mentioned.

- Agent A sends to Agent B: Agent A must @mention Agent B
- If Agent C is in the room but not @mentioned, Agent C won't see the message
- Events (thoughts, tool calls) are private to the creating agent

---

## Adapters for Our D&D System

### Best Fit: AnthropicAdapter or CrewAIAdapter

**AnthropicAdapter** (Recommended for NPCs):
```python
adapter = AnthropicAdapter(
    model="claude-sonnet-4-5-20250929",
    custom_section="NPC personality and behavior instructions",
    enable_execution_reporting=True,  # See tool calls in UI
)
```

**CrewAIAdapter** (Great for role-based agents):
```python
adapter = CrewAIAdapter(
    model="gpt-4o",
    role="Dungeon Master",
    goal="Create an immersive D&D experience for players",
    backstory="You are an experienced DM running Lost Mines of Phandelver...",
)
```

### Custom Adapter Pattern

For maximum control, create a custom adapter:

```python
from thenvoi.core.simple_adapter import SimpleAdapter
from thenvoi.core.types import PlatformMessage

class DMAdapter(SimpleAdapter[list[dict]]):
    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: list[dict],
        participants_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        # Custom DM logic here
        pass
```

---

## Architecture for D&D Campaign

### Proposed Agent Structure

```
+------------------+
|   DM Agent       |  <- Orchestrator (owner of game chatroom)
|   (Owner)        |
+------------------+
        |
        +-- Manages game state
        +-- Controls narrative
        +-- Invites/removes NPCs as needed
        +-- Resolves combat and skill checks
        |
+------------------+     +------------------+     +------------------+
|  NPC Agent 1     |     |  NPC Agent 2     |     |  AI Player 1     |
|  (Gundren)       |     |  (Sildar)        |     |  (Fighter)       |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        +-- Personality-driven   +-- Personality-driven   +-- Makes decisions
        +-- Responds to DM       +-- Responds to DM       +-- Takes actions
        +-- Stays in character   +-- Quest information    +-- Collaborates

+------------------+
|  Human Player    |
|  (User)          |
+------------------+
        |
        +-- Interacts via chat UI
        +-- @mentions DM for actions
        +-- Receives game narration
```

### Communication Flow

1. **Human Player** @mentions **DM Agent**: "I want to attack the goblin"
2. **DM Agent** processes action, rolls dice, updates state
3. **DM Agent** @mentions **Human Player** with result: "Roll a d20 for attack"
4. **Human Player** @mentions **DM Agent**: "I rolled a 17"
5. **DM Agent** @mentions **Human Player**: "Hit! Roll 1d8+3 for damage"
6. **DM Agent** @mentions **NPC Agent** if relevant: "@Gundren, the party saved you!"
7. **NPC Agent** responds in character

### Game State Management

The DM Agent should maintain game state including:
- Current location (Goblin Arrows, Cragmaw Hideout, etc.)
- Party status (HP, conditions, inventory)
- NPC states (alive, hostile, friendly)
- Quest progress

Options for state persistence:
1. **In-memory** (simplest for hackathon)
2. **JSON file** (persists across restarts)
3. **Context hydration** (Thenvoi stores conversation history)

---

## Implementation Recommendations for Hackathon

### Day 1: Foundation

1. **Set up Thenvoi platform accounts and agents**
   - Create DM Agent (external)
   - Create 2-3 NPC agents (Gundren, Sildar, Klarg)
   - Create 1-2 AI player agents

2. **Build minimal DM Agent**
   - Use AnthropicAdapter or CrewAIAdapter
   - Custom section with DM instructions
   - Basic game state (current scene, party info)

3. **Test basic communication**
   - Human joins chatroom
   - DM responds to human
   - NPC agents respond when summoned

### Day 2: Game Mechanics

1. **Implement dice rolling tool**
2. **Add combat system (simplified)**
3. **Implement skill check resolution**
4. **Build out Chapter 1 content (Goblin Arrows)**

### Day 3: Polish and Demo

1. **Add more NPC personalities**
2. **Test full gameplay loop**
3. **Handle edge cases**
4. **Prepare demo scenario**

### Scope Cuts for 3 Days

**Include:**
- Chapter 1: Goblin Arrows ambush
- Basic combat (attack rolls, damage)
- Skill checks (perception, stealth)
- 3-4 NPCs with personalities
- Human player interaction

**Defer:**
- Full dungeon mapping
- Complex spell systems
- Inventory management
- Experience/leveling
- Multiple chapters

---

## Key Code Patterns

### Agent Configuration (agent_config.yaml)

```yaml
dm_agent:
  agent_id: "uuid-from-platform"
  api_key: "api-key-from-platform"

gundren_npc:
  agent_id: "uuid-from-platform"
  api_key: "api-key-from-platform"

sildar_npc:
  agent_id: "uuid-from-platform"
  api_key: "api-key-from-platform"
```

### Environment Variables (.env)

```bash
THENVOI_REST_URL=https://api.thenvoi.com
THENVOI_WS_URL=wss://api.thenvoi.com/ws
ANTHROPIC_API_KEY=your-key-here
```

### Running Multiple Agents

Each agent runs in its own process:

```bash
# Terminal 1
python dm_agent.py

# Terminal 2
python gundren_agent.py

# Terminal 3
python sildar_agent.py
```

Or use Docker Compose for orchestration.

---

## Testing Approach

### Unit Testing with FakeAgentTools

```python
from thenvoi.testing import FakeAgentTools

async def test_dm_response():
    tools = FakeAgentTools()
    adapter = DMAdapter()

    await adapter.on_message(msg, tools, history, ...)

    # Verify what was sent
    assert len(tools.sent_messages) == 1
    assert "attack" in tools.sent_messages[0]["content"]
```

### Integration Testing

- Use test agents on the platform
- Create test chatrooms
- Verify multi-agent communication

---

## References

- **Thenvoi SDK Repository**: https://github.com/thenvoi/thenvoi-sdk-python
- **Thenvoi Platform**: https://platform.thenvoi.com
- **API Documentation**: https://docs.thenvoi.com (some pages 404)
- **SDK README**: Comprehensive examples and usage patterns
