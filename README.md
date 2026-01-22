# Lost Mine of Thenvoi

A playable Dungeons & Dragons campaign (Lost Mine of Phandelver) powered by multi-agent AI on the Thenvoi platform.

## Overview

This project implements a D&D 5e campaign as a collaborative multi-agent system where:

- **DM Agent**: Orchestrates the game, manages narrative, combat, and world state
- **AI Player Agents**: Automated party members (Thokk the Fighter, Lira the Cleric)
- **Human Player**: Participates via the Thenvoi platform chat interface

## Quick Start

### Prerequisites

- Python 3.11 or higher
- A Thenvoi platform account (https://app.thenvoi.com)
- An Anthropic API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/bailey-dickens-thenvoi/lost-mine-of-thenvoi.git
   cd lost-mine-of-thenvoi
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. Copy the environment template and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Verify configuration:
   ```bash
   python -m src.main --check
   ```

### Creating Agents on Thenvoi Platform

1. Go to https://app.thenvoi.com
2. Create 3 "External" type agents:
   - **DM Agent**: Dungeon Master orchestrator
   - **Thokk**: Half-Orc Fighter player
   - **Lira**: Human Cleric player
3. Copy each agent's `agent_id` and `api_key` to your `.env` file

### Running the Game

Each agent runs in its own terminal:

```bash
# Terminal 1 - DM Agent
python -m src.main --agent dm

# Terminal 2 - Thokk (Fighter)
python -m src.main --agent thokk

# Terminal 3 - Lira (Cleric)
python -m src.main --agent lira
```

Then join the chatroom as a human player via the Thenvoi platform UI.

#### Command Line Options

- `--agent <name>`: Specify which agent to run (dm, thokk, lira)
- `--new-game`: Reset game state to start a fresh campaign
- `--debug`: Enable verbose logging for troubleshooting
- `--check`: Verify configuration without starting the agent

## Project Structure

```
lost-mine-of-thenvoi/
├── src/
│   ├── agents/          # Agent implementations
│   ├── tools/           # Custom agent tools (dice, world state)
│   ├── game/            # D&D game mechanics
│   ├── content/         # Campaign content
│   ├── config.py        # Configuration management
│   └── main.py          # Entry point
├── data/                # Game state files
├── tests/               # Test suite
├── docs/                # Documentation
└── pyproject.toml       # Project configuration
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
ruff check .
ruff format .
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed system design.

## The Party

| Character | Race | Class | Player Type |
|-----------|------|-------|-------------|
| Vex | Lightfoot Halfling | Rogue | Human Player |
| Thokk | Half-Orc | Fighter | AI Agent |
| Lira | Human | Cleric (Life) | AI Agent |

## Campaign: Lost Mines of Phandelver

Chapter 1: Goblin Arrows
- Escort mission to Phandalin
- Goblin ambush encounter
- Cragmaw Hideout dungeon

## License

MIT
