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
      "name": "Vex",
      "class": "Rogue",
      "race": "Lightfoot Halfling",
      "background": "Criminal",
      "level": 1,
      "hp": 9,
      "max_hp": 9,
      "ac": 14,
      "stats": {"str": 8, "dex": 17, "con": 12, "int": 13, "wis": 12, "cha": 14},
      "proficiency_bonus": 2,
      "saving_throws": ["dex", "int"],
      "skills": ["acrobatics", "deception", "investigation", "perception", "sleight_of_hand", "stealth"],
      "conditions": [],
      "inventory": ["shortsword", "shortbow", "quiver (20 arrows)", "leather armor", "two daggers", "thieves tools", "burglar's pack"],
      "features": ["Sneak Attack (1d6)", "Expertise (Stealth, Thieves' Tools)", "Thieves' Cant"],
      "racial_traits": ["Lucky", "Brave", "Halfling Nimbleness", "Naturally Stealthy"]
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

## Party Composition

The party consists of three Level 1 adventurers with complementary roles:

### Vex (Human Player) - Lightfoot Halfling Rogue

**Role in Party**: Scout, skill monkey, ranged damage dealer, Sneak Attack striker

```json
{
  "name": "Vex",
  "class": "Rogue",
  "race": "Lightfoot Halfling",
  "background": "Criminal",
  "level": 1,
  "hp": 9,
  "max_hp": 9,
  "ac": 14,
  "stats": {
    "str": 8, "dex": 17, "con": 12,
    "int": 13, "wis": 12, "cha": 14
  },
  "proficiency_bonus": 2,
  "saving_throws": ["dex", "int"],
  "skills": ["acrobatics", "deception", "investigation", "perception", "sleight_of_hand", "stealth"],
  "equipment": ["shortsword", "shortbow", "quiver (20 arrows)", "leather armor", "two daggers", "thieves tools", "burglar's pack"],
  "features": ["Sneak Attack (1d6)", "Expertise (Stealth, Thieves' Tools)", "Thieves' Cant"],
  "racial_traits": ["Lucky", "Brave", "Halfling Nimbleness", "Naturally Stealthy"]
}
```

**Combat Stats**:
- Shortsword Attack: +5 to hit, 1d6+3 piercing (+ 1d6 Sneak Attack if conditions met)
- Shortbow Attack: +5 to hit, 1d6+3 piercing, range 80/320 (+ 1d6 Sneak Attack)
- Dagger Attack: +5 to hit, 1d4+3 piercing, thrown range 20/60

**Sneak Attack Conditions** (1d6 extra damage):
- Advantage on the attack roll, OR
- An ally is within 5 feet of the target (and you don't have disadvantage)

**Racial Abilities**:
- **Lucky**: Reroll natural 1s on attack rolls, ability checks, or saving throws
- **Brave**: Advantage on saving throws against being frightened
- **Halfling Nimbleness**: Move through the space of larger creatures
- **Naturally Stealthy**: Can hide behind creatures at least one size larger

**Personality for Roleplay**:
- **Trait**: "I always have a plan for what to do when things go wrong."
- **Ideal**: "Freedom. Chains are meant to be broken, as are those who would forge them."
- **Bond**: "I'm trying to pay off an old debt I owe to a generous benefactor."
- **Flaw**: "When I see something valuable, I can't think about anything but how to steal it."

**Tactical Guidance for Human Player**:
1. Stay behind Thokk (the Fighter) to trigger Sneak Attack
2. Use shortbow at range for safer damage dealing
3. Use Stealth checks to scout ahead for the party
4. In melee, shortsword + Sneak Attack for burst damage
5. Use the Lucky trait to reroll critical failures

---

### Thokk (AI Player) - Half-Orc Fighter

**Role in Party**: Front-line tank, high damage melee, intimidation

```json
{
  "name": "Thokk",
  "class": "Fighter",
  "race": "Half-Orc",
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
  "features": ["Fighting Style: Defense (+1 AC)", "Second Wind (1d10+1 HP, bonus action, 1/rest)"],
  "racial_traits": ["Darkvision", "Menacing", "Relentless Endurance", "Savage Attacks"]
}
```

**Combat Stats**:
- Longsword Attack: +5 to hit, 1d8+3 slashing
- Handaxe Attack: +5 to hit, 1d6+3 slashing, thrown range 20/60

**Key Abilities**:
- **Second Wind**: Regain 1d10+1 HP as a bonus action (once per short rest)
- **Relentless Endurance**: Drop to 1 HP instead of 0 (once per long rest)
- **Savage Attacks**: Extra damage die on critical hits with melee weapons

**Personality**: Direct and practical. Solves problems with strength. Loyal to allies. Few words, decisive action.

---

### Lira (AI Player) - Human Cleric (Life Domain)

**Role in Party**: Healer, support buffer, secondary melee, divine magic

```json
{
  "name": "Lira",
  "class": "Cleric (Life Domain)",
  "race": "Human",
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
  "features": ["Spellcasting", "Divine Domain: Life", "Disciple of Life (+2+spell level HP when healing)"],
  "spells": {
    "cantrips": ["sacred flame", "spare the dying", "guidance"],
    "1st_level_prepared": ["bless", "cure wounds", "healing word", "shield of faith"],
    "domain_spells": ["bless", "cure wounds"]
  },
  "spell_slots": {"1st": 2}
}
```

**Combat Stats**:
- Mace Attack: +4 to hit, 1d6+2 bludgeoning
- Sacred Flame: DEX save DC 13, 1d8 radiant (cantrip, no attack roll)

**Key Spells**:
- **Cure Wounds**: Touch, 1d8+5 HP (includes Disciple of Life bonus)
- **Healing Word**: 60 ft, 1d4+5 HP, bonus action (includes Disciple of Life)
- **Bless**: 3 creatures, +1d4 to attack rolls and saving throws, concentration
- **Shield of Faith**: +2 AC to one creature, concentration

**Personality**: Compassionate and wise. Seeks peaceful solutions but will fight to protect innocents. References her faith naturally.

---

### Party Synergy

| Situation | Tactic |
|-----------|--------|
| **Start of Combat** | Lira casts Bless on all three party members |
| **Ranged Combat** | Vex uses shortbow with Sneak Attack, Lira uses Sacred Flame |
| **Melee Combat** | Thokk engages enemies, Vex flanks for Sneak Attack, Lira supports |
| **Healing Needed** | Lira uses Healing Word (bonus action) to keep fighting |
| **Emergency** | Thokk uses Second Wind, Lira uses Cure Wounds on critical ally |
| **Scouting** | Vex uses Stealth (+7) to scout ahead safely |
| **Social** | Vex uses Deception/Sleight of Hand, Lira uses Persuasion |

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

## Edge Cases and Protocol Details

This section addresses specific edge cases in the multi-agent coordination.

### Turn Notification Protocol

**Problem**: How does the human player know it is their turn?

**Solution**: The DM uses a consistent, information-rich turn prompt format:

```
@Human Player - ROUND {round_num}, YOUR TURN!

STATUS:
- Your HP: {hp}/{max_hp}
- Allies: Thokk ({thokk_hp} HP), Lira ({lira_hp} HP)
- Enemies: {enemy_status_list}

The {last_action_description}.

What do you do?
```

**Example**:
```
@Human Player - ROUND 2, YOUR TURN!

STATUS:
- Your HP: 8/10
- Allies: Thokk (5 HP, wounded), Lira (10 HP)
- Enemies: Goblin 1 (dead), Goblin 2 (wounded), Goblin 3 (healthy)

Goblin 2 just missed Lira with its scimitar.

What do you do?
```

**Implementation**: The `prompt_next_turn()` function must gather this status from world_state.

### NPC Personality Injection Protocol

**Problem**: How does the NPC agent know which personality to use?

**Solution**: The DM always uses a structured message format with required tags. The NPC agent validates these tags.

**Required Tags** (in order):
1. `[PLAY AS: {name}]` - Required, identifies the character
2. `[PERSONALITY: {traits}]` - Required, describes how to act
3. `[CONTEXT: {situation}]` - Required, current narrative situation
4. `[SCENE: {description}]` - Required, what is happening now

**NPC Validation Logic**:
```python
def parse_dm_message(message: str) -> dict | None:
    """Parse DM message for NPC acting instructions."""
    required_tags = ["PLAY AS", "PERSONALITY", "CONTEXT", "SCENE"]
    result = {}

    for tag in required_tags:
        pattern = rf'\[{tag}:\s*(.+?)\]'
        match = re.search(pattern, message, re.DOTALL)
        if not match:
            return None  # Missing required tag
        result[tag.lower().replace(" ", "_")] = match.group(1).strip()

    return result

# In NPC agent's response logic:
parsed = parse_dm_message(dm_message)
if parsed is None:
    # Fallback: ask DM for clarification
    send_message("@DM Agent I need character instructions. Please include [PLAY AS], [PERSONALITY], [CONTEXT], and [SCENE] tags.")
```

### Combat End Protocol

**Problem**: What happens when combat ends?

**Solution**: The DM follows a specific protocol when combat ends:

```
COMBAT END CHECKLIST:
1. Detect end condition (all enemies dead/fled OR party retreat)
2. Call end_combat() to clear combat state
3. Set narrative_progress flags (e.g., "goblins_defeated": true)
4. Announce victory/outcome to ALL participants
5. Describe the aftermath (loot, bodies, etc.)
6. Handle any unconscious party members
7. Prompt for next actions or transition to next scene
```

**End Combat Message Format**:
```
@Human Player @Thokk @Lira

=== COMBAT ENDS ===

{Victory/Retreat description}

AFTERMATH:
- {character} is unconscious and needs healing
- Enemies defeated: {list}
- You may search the area or continue

{Loot available if any}

What do you do?
```

**Unconscious Character Handling**:
- Characters at 0 HP are unconscious (not dead)
- They cannot take actions until healed to 1+ HP
- The Cleric (Lira) should prioritize healing them
- If Lira is down, prompt human about healing potions

### Scene Advancement Protocol

**Problem**: How does the DM know when to advance the story?

**Solution**: The DM checks `narrative_progress` flags and scene completion conditions.

**Scene Completion Conditions**:
```python
SCENE_COMPLETION = {
    "intro": {
        "required_flags": [],  # No flags required
        "completion_triggers": [
            "party_approaches_horses",
            "party_investigates_area",
            "ambush_triggered"  # Any of these
        ],
        "next_scene": "goblin_ambush"
    },
    "goblin_ambush": {
        "required_flags": ["ambush_triggered"],
        "completion_triggers": ["goblins_defeated", "party_fled"],
        "next_scene": "after_ambush"
    },
    "after_ambush": {
        "required_flags": ["goblins_defeated"],
        "completion_triggers": ["trail_found", "proceed_to_phandalin"],
        "next_scene": "goblin_trail"  # or "phandalin"
    }
}
```

**DM Story Advancement Logic**:
```
AFTER RESOLVING EACH ACTION:
1. Check if action sets any narrative_progress flags
2. Check current scene's completion_triggers
3. If a trigger is satisfied:
   a. Save state
   b. Update current_scene
   c. Load and narrate new scene description
   d. Prompt players for actions in new scene
```

**DM System Prompt Addition**:
```
## Story Advancement Rules

After resolving player actions, check if the story should advance:

1. COMBAT VICTORY: Set "{enemies}_defeated" flag, transition to aftermath scene
2. KEY DISCOVERY: Set discovery flags (e.g., "trail_found"), offer new options
3. NPC INTERACTION: Update NPC state, reveal relevant information
4. LOCATION CHANGE: Update current_scene, describe new location

Always narrate transitions dramatically. Don't just say "you move to the next area."
```

### Broadcast Message Protocol

**Problem**: When the DM narrates to everyone, they must @mention all participants.

**Solution**: Use platform's `get_participants()` tool to build mention list.

```python
async def broadcast_to_all(content: str, tools: AgentToolsProtocol):
    """Send a message to all participants in the room."""
    participants = await tools.get_participants()
    # Filter to get player names (exclude self)
    player_names = [p["name"] for p in participants if p["name"] != "DM Agent"]
    mention_string = " ".join(f"@{name}" for name in player_names)

    await tools.send_message(
        content=f"{mention_string}\n\n{content}",
        mentions=player_names
    )
```

**When to Broadcast vs. Target**:
| Situation | Action |
|-----------|--------|
| Scene narration | Broadcast to all |
| Combat announcement | Broadcast to all |
| Turn prompt | Target single player |
| NPC invocation | Target NPC Agent only |
| Action result | Broadcast to all |
| Private information | Target specific player |

### Error Recovery Protocols

**Problem**: What happens if something goes wrong?

**Agent Crash Recovery**:
1. World state is saved after every significant action
2. Agents can be restarted and will rejoin the chatroom
3. DM can re-prompt the current turn holder
4. Combat state persists in world_state.json

**Human Player AFK Handling**:
```
IF human player doesn't respond within 60 seconds:
1. DM sends reminder: "@Human Player - Still your turn! What would you like to do?"
2. After another 60 seconds: DM may have AI suggest an action
3. After 3 minutes: DM may take a defensive action on their behalf
   "Your character takes the Dodge action, staying alert."
```

**Tool Call Failure**:
```
IF a tool call fails:
1. Log the error
2. Inform the player: "Something went wrong with that action. Let me try again."
3. Retry once
4. If still failing: "Technical difficulties. Let's assume [reasonable outcome]."
```

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
