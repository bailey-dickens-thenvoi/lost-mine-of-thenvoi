# Live Demo Checklist

This document provides checklists and procedures for running a live demo of the Lost Mines of Thenvoi D&D campaign system.

## Pre-Demo Checklist

### Platform Setup
- [ ] All agents registered on Thenvoi platform (see [Platform Setup Guide](./platform-setup.md))
  - [ ] DM Agent (owner)
  - [ ] NPC Agent (member)
  - [ ] Thokk - Fighter (member)
  - [ ] Lira - Cleric (member)
- [ ] `.env` file configured with all credentials
- [ ] Anthropic API key configured and has sufficient credits
- [ ] Test chatroom created on platform
- [ ] All agents added to chatroom

### System Verification
- [ ] All tests pass: `pytest tests/`
- [ ] Connection test passes: `python scripts/test_connection.py`
- [ ] Demo scenario runs: `python scripts/demo_scenario.py --fast`

### State Reset
- [ ] Delete `data/world_state.json` to reset game state
- [ ] Verify state resets to Chapter 1 intro on next run

### Environment
- [ ] Stable internet connection
- [ ] Browser open to platform.thenvoi.com
- [ ] Terminal ready for agent processes
- [ ] Screen sharing configured (if presenting remotely)

## During Demo Checklist

### Startup Sequence
1. [ ] Start DM Agent: `python -m src.agents.dm_agent`
2. [ ] Start NPC Agent: `python -m src.agents.npc_agent`
3. [ ] Start Thokk Agent: `python -m src.agents.player_agent thokk`
4. [ ] Start Lira Agent: `python -m src.agents.player_agent lira`
5. [ ] Verify all agents appear online in chatroom

### Demo Flow
- [ ] Human player joins chatroom
- [ ] DM responds to initial greeting
- [ ] DM narrates intro scene (dead horses)
- [ ] Human player can investigate (DM rolls dice)
- [ ] Combat triggers (goblin ambush)
- [ ] Turn order announced
- [ ] AI players (Thokk, Lira) take their turns
- [ ] Human player takes turn
- [ ] DM resolves actions with dice rolls
- [ ] Combat ends when goblins defeated
- [ ] Post-combat narration
- [ ] (Optional) NPC interaction (Sildar)

### Things to Watch For
- [ ] DM uses dice rolls properly
- [ ] Turn order cycles correctly
- [ ] HP tracking works
- [ ] AI players make reasonable decisions
- [ ] NPC stays in character when invoked
- [ ] Game state persists between messages

## Recovery Procedures

### Agent Crashes

If an agent stops responding:

1. Check terminal for error messages
2. Stop the agent process (Ctrl+C)
3. Restart the agent:
   ```bash
   python -m src.agents.dm_agent  # or appropriate agent
   ```
4. The agent will reconnect to the chatroom
5. DM can re-prompt the current turn if needed

### Stuck Combat

If combat gets stuck:

1. Check world state:
   ```python
   from src.tools.world_state import get_world_state_manager
   manager = get_world_state_manager()
   print(manager.get("combat.active"))
   print(manager.get("combat.turn_order"))
   print(manager.get("combat.current_turn_index"))
   ```

2. Force advance turn:
   ```python
   from src.game.combat import advance_turn
   advance_turn(manager)
   ```

3. Force end combat:
   ```python
   from src.game.combat import end_combat
   end_combat(manager, "enemies_defeated")
   ```

### Reset Game State

To start fresh:

```bash
# Delete the state file
rm data/world_state.json

# Or reset via Python
python -c "
from src.tools.world_state import reset_world_state_manager, get_world_state_manager
reset_world_state_manager()
manager = get_world_state_manager()
print('State reset to:', manager.get('current_scene'))
"
```

### Connection Issues

If agents can't connect to platform:

1. Check `.env` file has correct credentials
2. Verify internet connection
3. Check platform status at https://platform.thenvoi.com
4. Try running connection test: `python scripts/test_connection.py`
5. If persistent, try recreating agents on platform

## Offline Demo Alternative

If platform connectivity fails, use the demo scenario script:

```bash
# Run the offline demo
python scripts/demo_scenario.py

# Or fast mode without delays
python scripts/demo_scenario.py --fast
```

This runs a scripted version of Chapter 1 using the mock platform, demonstrating the game logic without requiring actual platform connectivity.

## Demo Script (Talking Points)

### Introduction (30 seconds)
"This is Lost Mines of Thenvoi - a playable D&D campaign powered by AI agents. We have a DM agent that runs the game, NPC agents that play characters, and AI party members. A human player can join and play alongside them."

### Show Agent Architecture (1 minute)
"The DM agent is the orchestrator. It rolls all dice, manages game state, and coordinates the other agents using @mentions. Players can't roll their own dice - they declare actions and the DM resolves them."

### Live Demo (5-7 minutes)
1. Show the intro narration
2. Have human player investigate horses
3. Trigger combat, show turn order
4. Let AI players take turns
5. Have human attack a goblin
6. End combat, show aftermath

### Conclusion (30 seconds)
"This demonstrates multi-agent collaboration for interactive storytelling. The same architecture could power other narrative games, training simulations, or any application needing coordinated AI agents with human-in-the-loop."

## Backup Plans

### If Demo Completely Fails
1. Show the offline demo script running
2. Walk through the code architecture
3. Show the test suite passing as proof of functionality
4. Present the slides with screenshots

### If Partially Working
1. Focus on what IS working
2. Explain what should happen for broken parts
3. Show relevant test cases that verify the functionality
4. Offer to share a recording of a successful demo later

## Post-Demo

- [ ] Stop all agent processes
- [ ] Note any issues encountered
- [ ] Reset game state if needed for future demos
- [ ] Thank the audience for their time
