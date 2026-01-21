# Lost Mine of Thenvoi - System Architecture

## Overview

This document describes the architecture for running a playable D&D campaign (Lost Mines of Phandelver) as a multi-agent system on the Thenvoi platform.

---

## System Components

```
+====================================================================================+
|                              THENVOI PLATFORM                                       |
|  +------------------------------------------------------------------------------+  |
|  |                           GAME CHATROOM                                      |  |
|  |                                                                              |  |
|  |   +------------------+                                                       |  |
|  |   |   DM AGENT       |  <-- Orchestrator (room owner)                       |  |
|  |   |   (Owner)        |      - Maintains world state (JSON file)             |  |
|  |   |                  |      - Rolls ALL dice (players have no tools)        |  |
|  |   |   Tools:         |      - Manages turn order                            |  |
|  |   |   - roll_dice    |      - Controls narrative flow                       |  |
|  |   |   - world_state  |      - @mentions players for their turns             |  |
|  |   +--------+---------+                                                       |  |
|  |            |                                                                 |  |
|  |            | @mentions to coordinate                                         |  |
|  |            |                                                                 |  |
|  |   +--------v---------+     +------------------+     +------------------+     |  |
|  |   |  NPC AGENT       |     |  AI PLAYER 1     |     |  AI PLAYER 2     |     |  |
|  |   |  (Generic)       |     |  (Fighter)       |     |  (Cleric)        |     |  |
|  |   |                  |     |                  |     |                  |     |  |
|  |   |  Personality:    |     |  Character:      |     |  Character:      |     |  |
|  |   |  Injected per    |     |  Pre-generated   |     |  Pre-generated   |     |  |
|  |   |  scene by DM     |     |  stats/abilities |     |  stats/abilities |     |  |
|  |   +------------------+     +------------------+     +------------------+     |  |
|  |                                                                              |  |
|  |   +------------------+                                                       |  |
|  |   |  HUMAN PLAYER    |  <-- Interacts via Platform UI                       |  |
|  |   |  (User)          |      - NO tools (cannot roll dice)                   |  |
|  |   |                  |      - Declares actions in natural language          |  |
|  |   |                  |      - DM rolls on their behalf                      |  |
|  |   +------------------+                                                       |  |
|  |                                                                              |  |
|  +------------------------------------------------------------------------------+  |
+====================================================================================+
                    |
                    | World State Persistence
                    v
        +------------------------+
        |   world_state.json     |
        |   - combat_state       |
        |   - narrative_progress |
        |   - npc_states         |
        |   - character_stats    |
        +------------------------+
```

---

## World State Management

### State File Structure (`world_state.json`)

```json
{
  "game_id": "lost-mines-001",
  "current_chapter": 1,
  "current_scene": "goblin_ambush",
  "narrative_progress": {
    "wagon_discovered": false,
    "goblins_defeated": false,
    "trail_found": false,
    "hideout_entered": false
  },
  "combat": {
    "active": false,
    "round": 0,
    "turn_order": [],
    "current_turn_index": 0,
    "combatants": {}
  },
  "characters": {
    "human_player": {
      "name": "Adventurer",
      "class": "Rogue",
      "level": 1,
      "hp": 10,
      "max_hp": 10,
      "ac": 14,
      "stats": {"str": 10, "dex": 16, "con": 12, "int": 14, "wis": 10, "cha": 12},
      "conditions": [],
      "inventory": ["shortsword", "shortbow", "leather armor", "thieves tools"]
    },
    "ai_fighter": {
      "name": "Thokk",
      "class": "Fighter",
      "level": 1,
      "hp": 12,
      "max_hp": 12,
      "ac": 16,
      "stats": {"str": 16, "dex": 14, "con": 14, "int": 8, "wis": 12, "cha": 10},
      "conditions": [],
      "inventory": ["longsword", "shield", "chain mail", "handaxe"]
    },
    "ai_cleric": {
      "name": "Lira",
      "class": "Cleric",
      "level": 1,
      "hp": 10,
      "max_hp": 10,
      "ac": 16,
      "stats": {"str": 14, "dex": 10, "con": 12, "int": 10, "wis": 16, "cha": 12},
      "conditions": [],
      "inventory": ["mace", "shield", "scale mail", "holy symbol"]
    }
  },
  "npcs": {
    "gundren": {
      "state": "captured",
      "location": "cragmaw_castle",
      "disposition": "friendly"
    },
    "sildar": {
      "state": "captured",
      "location": "cragmaw_hideout",
      "disposition": "friendly"
    }
  },
  "enemies": {
    "goblin_1": {"hp": 7, "max_hp": 7, "ac": 15, "state": "alive"},
    "goblin_2": {"hp": 7, "max_hp": 7, "ac": 15, "state": "alive"},
    "goblin_3": {"hp": 7, "max_hp": 7, "ac": 15, "state": "alive"},
    "goblin_4": {"hp": 7, "max_hp": 7, "ac": 15, "state": "alive"}
  }
}
```

### State Operations

The DM agent has a `world_state` tool with these operations:

| Operation | Description |
|-----------|-------------|
| `get_state(path)` | Get value at JSON path (e.g., "combat.active") |
| `set_state(path, value)` | Set value at JSON path |
| `update_hp(entity, delta)` | Modify HP (positive = heal, negative = damage) |
| `start_combat(combatants)` | Initialize combat with turn order |
| `end_combat()` | Clean up combat state |
| `advance_turn()` | Move to next combatant in turn order |
| `save()` | Persist state to JSON file |
| `load()` | Load state from JSON file |

---

## Dice Rolling System

**Critical Design Decision**: Only the DM agent can roll dice. Human players and AI players declare their intended actions, and the DM rolls for them.

### Why DM Rolls Everything

1. **Human players cannot use tools** - Thenvoi platform limitation
2. **Consistency** - All rolls go through one system
3. **Game integrity** - DM can apply modifiers, advantage/disadvantage
4. **Narrative control** - DM can describe roll outcomes dramatically

### Dice Tool Implementation

```python
@tool
def roll_dice(
    dice_notation: str,
    purpose: str,
    roller: str,
    advantage: bool = False,
    disadvantage: bool = False
) -> dict:
    """
    Roll dice in D&D notation.

    Args:
        dice_notation: Standard notation like "1d20", "2d6+3", "1d20+5"
        purpose: What the roll is for (e.g., "attack roll", "damage", "perception check")
        roller: Who is making the roll (e.g., "human_player", "ai_fighter", "goblin_1")
        advantage: Roll twice, take higher (for d20 rolls)
        disadvantage: Roll twice, take lower (for d20 rolls)

    Returns:
        {
            "rolls": [14, 8],  # Individual die results
            "modifier": 5,
            "total": 19,
            "purpose": "attack roll",
            "roller": "human_player",
            "advantage_used": false,
            "critical": false,  # Natural 20
            "fumble": false     # Natural 1
        }
    """
```

### Roll Flow

```
Human Player: "@DM I want to attack the goblin with my shortsword"
                    |
                    v
DM Agent: [Uses roll_dice tool]
          roll_dice("1d20+5", "attack roll", "human_player")
                    |
                    v
DM Agent: "@Human Player, you swing your shortsword at the goblin!
           Rolling attack: [15] + 5 = 20 vs AC 15... Hit!
           Rolling damage: [4] + 3 = 7 piercing damage.
           The goblin staggers from the blow!"
                    |
                    v
DM Agent: [Uses world_state tool]
          update_hp("goblin_1", -7)
```

---

## Turn Order System

### Combat Initialization

When combat starts:

1. DM rolls initiative for ALL combatants (players + enemies)
2. Turn order is sorted by initiative (highest first)
3. State is updated with turn order array

```python
def start_combat(combatants: list[str]) -> None:
    """
    Initialize combat with the given combatants.

    1. Roll initiative for each combatant
    2. Sort by initiative (descending)
    3. Store turn order in state
    """
    initiatives = []
    for combatant in combatants:
        # Get DEX modifier from character/enemy stats
        dex_mod = get_dex_modifier(combatant)
        roll = roll_dice(f"1d20+{dex_mod}", "initiative", combatant)
        initiatives.append((combatant, roll["total"]))

    # Sort by initiative, highest first
    turn_order = [c[0] for c in sorted(initiatives, key=lambda x: -x[1])]

    state.set("combat.active", True)
    state.set("combat.turn_order", turn_order)
    state.set("combat.current_turn_index", 0)
    state.set("combat.round", 1)
```

### Turn Execution Flow

```
+-------------------+
| Combat Starts     |
| DM rolls all      |
| initiatives       |
+--------+----------+
         |
         v
+-------------------+
| Current Turn:     |
| Check whose turn  |
| from turn_order   |
+--------+----------+
         |
    +----+----+
    |         |
    v         v
+-------+  +--------+
| Human |  | AI or  |
| Player|  | Enemy  |
+---+---+  +----+---+
    |           |
    v           v
+-------+  +--------+
| DM    |  | Agent  |
| waits |  | or DM  |
| for   |  | acts   |
| input |  +----+---+
+---+---+       |
    |           |
    v           v
+-------------------+
| DM resolves       |
| action with rolls |
+--------+----------+
         |
         v
+-------------------+
| DM advances turn  |
| advance_turn()    |
+--------+----------+
         |
         v
+-------------------+
| Check for combat  |
| end conditions    |
+--------+----------+
         |
    +----+----+
    |         |
    v         v
  END      CONTINUE
  combat   to next turn
```

### DM Turn Prompting

The DM agent @mentions the appropriate entity for their turn:

```python
def prompt_next_turn():
    """Announce whose turn it is and prompt for action."""
    current = state.get("combat.turn_order")[state.get("combat.current_turn_index")]
    round_num = state.get("combat.round")

    if current.startswith("goblin") or current.startswith("enemy"):
        # DM controls enemies - take action immediately
        return take_enemy_turn(current)
    elif current == "human_player":
        # @mention the human player
        return f"@Human Player - Round {round_num}, your turn! What do you do?"
    else:
        # @mention the AI player agent
        agent_name = get_agent_name(current)
        return f"@{agent_name} - Round {round_num}, your turn! What do you do?"
```

---

## Generic NPC Agent Design

### Concept

Instead of creating separate agents for each NPC, we use ONE generic NPC agent that receives personality injection from the DM.

### How It Works

1. **DM determines which NPC should speak** based on narrative context
2. **DM @mentions the NPC agent** with context about which character to play
3. **NPC agent responds in character** based on the injected personality

### Message Format from DM to NPC

```
@NPC Agent [PLAY AS: Gundren Rockseeker]
[PERSONALITY: Gruff dwarf merchant. Speaks with dwarven accent. Excited about
rediscovering Wave Echo Cave. Protective of his brothers. Currently in distress
as he's been captured by goblins.]
[CONTEXT: The party just rescued you from the Cragmaw Hideout. You're grateful
but worried about your map and your brother Nundro.]
[SCENE: The party is asking about the mine and what happened to you.]

Party: "Gundren, what happened? Who captured you?"
```

### NPC Agent System Prompt

```
You are a versatile NPC actor for a D&D campaign. When the DM @mentions you:

1. Read the [PLAY AS] tag to know which character you are
2. Read the [PERSONALITY] tag to understand how to act
3. Read the [CONTEXT] tag to understand the situation
4. Read the [SCENE] tag to understand what's happening

Respond in character as that NPC. Stay in character. Don't break the fourth wall.
Keep responses concise (2-4 sentences) unless the scene calls for more.

If you don't have enough information to respond in character, ask the DM for
clarification by @mentioning them.
```

### NPC Data Storage

NPCs are defined in a separate file for easy reference:

```json
{
  "gundren_rockseeker": {
    "name": "Gundren Rockseeker",
    "race": "Dwarf",
    "occupation": "Merchant/Prospector",
    "personality": "Gruff but kind-hearted. Speaks with dwarven accent...",
    "goals": "Rediscover Wave Echo Cave, protect his brothers",
    "knowledge": ["Location of Wave Echo Cave", "History of Phandelver's Pact"],
    "current_state": "captured"
  },
  "sildar_hallwinter": {
    "name": "Sildar Hallwinter",
    "race": "Human",
    "occupation": "Warrior/Lords' Alliance member",
    "personality": "Noble and honorable. Speaks formally...",
    "goals": "Find Iarno Albrek, establish order in Phandalin",
    "knowledge": ["Lords' Alliance contacts", "Iarno's disappearance"],
    "current_state": "captured"
  }
}
```

---

## Message Flow Diagrams

### Exploration Phase

```
Human Player                    DM Agent                    AI Players
     |                              |                            |
     |  "I search the wagon"        |                            |
     |----------------------------->|                            |
     |                              |                            |
     |                        [roll_dice("1d20+4",               |
     |                         "investigation", "human")]        |
     |                              |                            |
     |                        [update world_state]               |
     |                              |                            |
     |  "You rolled 18! You find..." |                           |
     |<-----------------------------|                            |
     |                              |                            |
     |                              |   "@AI Fighter, you notice |
     |                              |    tracks leading north"   |
     |                              |--------------------------->|
     |                              |                            |
     |                              |   "Thokk points north.     |
     |                              |    'Goblin tracks. Fresh.'"|
     |                              |<---------------------------|
```

### Combat Phase

```
DM Agent                    Human Player              AI Fighter              AI Cleric
    |                            |                        |                       |
    | [start_combat()]           |                        |                       |
    | [roll initiatives]         |                        |                       |
    |                            |                        |                       |
    | "Combat! Turn order:       |                        |                       |
    |  1. Goblin 1 (18)          |                        |                       |
    |  2. Thokk (15)             |                        |                       |
    |  3. Human (12)             |                        |                       |
    |  4. Lira (10)              |                        |                       |
    |  5. Goblin 2 (8)"          |                        |                       |
    |---------------------------->------------------------->----------------------->
    |                            |                        |                       |
    | [DM takes goblin turn]     |                        |                       |
    | [roll attack vs Thokk]     |                        |                       |
    |                            |                        |                       |
    | "Goblin shoots at Thokk.   |                        |                       |
    |  [14]+4=18 vs AC 16. Hit!  |                        |                       |
    |  [5]+2=7 damage."          |                        |                       |
    |---------------------------->------------------------->----------------------->
    |                            |                        |                       |
    | "@AI Fighter, your turn!"  |                        |                       |
    |----------------------------------------------->     |                       |
    |                            |                        |                       |
    |                            |   "Thokk charges       |                       |
    |                            |    Goblin 1 and        |                       |
    |                            |    swings his sword!"  |                       |
    |<-----------------------------------------------|    |                       |
    |                            |                        |                       |
    | [roll attack for Thokk]    |                        |                       |
    | "Thokk: [17]+5=22. Hit!    |                        |                       |
    |  [7]+3=10 damage.          |                        |                       |
    |  Goblin 1 is slain!"       |                        |                       |
    |---------------------------->------------------------->----------------------->
    |                            |                        |                       |
    | "@Human Player, your turn!"|                        |                       |
    |--->                        |                        |                       |
    |                            |                        |                       |
    |    "I shoot my shortbow    |                        |                       |
    |     at Goblin 2"           |                        |                       |
    |<---------------------------|                        |                       |
    |                            |                        |                       |
    | [roll attack for human]    |                        |                       |
    | ...                        |                        |                       |
```

---

## Agent Implementations Summary

### DM Agent

| Aspect | Implementation |
|--------|----------------|
| Adapter | `AnthropicAdapter` with custom DM system prompt |
| Tools | `roll_dice`, `world_state`, platform tools |
| State | Maintains world_state.json |
| Role | Room owner, orchestrator |

### NPC Agent (Generic)

| Aspect | Implementation |
|--------|----------------|
| Adapter | `AnthropicAdapter` with NPC actor system prompt |
| Tools | Platform tools only |
| State | Stateless - personality injected per message |
| Role | Room member |

### AI Player Agents

| Aspect | Implementation |
|--------|----------------|
| Adapter | `AnthropicAdapter` with character system prompt |
| Tools | Platform tools only |
| State | Character sheet in system prompt |
| Role | Room member |

---

## File Structure

```
lost-mine-of-thenvoi/
+-- src/
|   +-- agents/
|   |   +-- __init__.py
|   |   +-- dm_agent.py          # DM orchestrator
|   |   +-- npc_agent.py         # Generic NPC actor
|   |   +-- player_agent.py      # AI player template
|   |
|   +-- tools/
|   |   +-- __init__.py
|   |   +-- dice.py              # Dice rolling tool
|   |   +-- world_state.py       # State management tool
|   |
|   +-- game/
|   |   +-- __init__.py
|   |   +-- combat.py            # Combat system
|   |   +-- characters.py        # Character definitions
|   |   +-- npcs.py              # NPC definitions
|   |
|   +-- content/
|   |   +-- __init__.py
|   |   +-- chapter1.py          # Goblin Arrows content
|   |   +-- scenes.py            # Scene definitions
|   |
|   +-- config.py                # Configuration loading
|   +-- main.py                  # Entry point
|
+-- data/
|   +-- world_state.json         # Persistent game state
|   +-- characters.json          # Pre-generated characters
|   +-- npcs.json                # NPC definitions
|
+-- tests/
|   +-- test_dice.py
|   +-- test_combat.py
|   +-- test_world_state.py
|
+-- docs/
|   +-- architecture.md          # This document
|   +-- thenvoi-research-summary.md
|
+-- .env.example                 # Environment template
+-- pyproject.toml               # Project configuration
+-- README.md
```

---

## Implementation Phases

### Day 1: Foundation (8 hours)

- [x] Project setup (structure, dependencies)
- [ ] World state manager implementation
- [ ] Dice rolling tool
- [ ] Basic DM agent (can respond, roll dice, update state)
- [ ] Test DM agent in isolation

### Day 2: Agents & Combat (8 hours)

- [ ] Combat system (turn order, initiative, attack resolution)
- [ ] NPC agent (generic, personality injection)
- [ ] AI player agents (2 characters)
- [ ] Integration testing (all agents in one room)

### Day 3: Content & Demo (8 hours)

- [ ] Chapter 1: Goblin Arrows scene content
- [ ] End-to-end playtest
- [ ] Bug fixes and polish
- [ ] Demo scenario preparation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Thenvoi API issues | Have local mock for testing |
| Complex combat bugs | Simplify to basic attack/damage only |
| Turn order confusion | DM always explicitly announces turns |
| NPC personality drift | Keep personality prompts short and focused |
| State corruption | Regular state saves, simple JSON structure |

---

## Success Criteria

**Minimum Viable Demo:**
1. Human player can join chatroom and interact with DM
2. DM can narrate the Goblin Arrows ambush scene
3. Combat works with turn order and dice rolls
4. At least one NPC interaction (Sildar rescue)
5. Game state persists across sessions
