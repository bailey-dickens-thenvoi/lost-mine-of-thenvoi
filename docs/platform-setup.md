# Thenvoi Platform Setup Guide

This guide walks you through setting up the agents on the Thenvoi platform for the Lost Mines of Phandelver D&D campaign.

## Prerequisites

- Access to the Thenvoi platform (https://platform.thenvoi.com)
- A Thenvoi account with permission to create agents
- An Anthropic API key

## Step 1: Create Agents on Platform

Create the following agents as **External** type on the Thenvoi platform:

| Agent Name | Display Name | Description | Role |
|------------|--------------|-------------|------|
| dm-agent | DM Agent | Dungeon Master orchestrator for Lost Mines campaign | Owner of game chatroom |
| npc-agent | NPC Agent | Generic NPC actor for portraying campaign characters | Member |
| thokk-fighter | Thokk | AI Player - Half-Orc Fighter party member | Member |
| lira-cleric | Lira | AI Player - Human Cleric party member | Member |

### Creating Each Agent

For each agent:

1. Go to https://platform.thenvoi.com
2. Navigate to the **Agents** section
3. Click **Create Agent**
4. Select **External** as the agent type
5. Fill in:
   - **Name**: Use the Display Name from the table above
   - **Description**: Use the Description from the table above
6. Click **Save**
7. **Important**: Copy and save the `agent_id` and `api_key` that are generated

## Step 2: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   # Thenvoi Platform URLs (usually don't need to change)
   THENVOI_REST_URL=https://api.thenvoi.com
   THENVOI_WS_URL=wss://api.thenvoi.com/ws

   # DM Agent Credentials
   DM_AGENT_ID=<uuid-from-platform>
   DM_API_KEY=<api-key-from-platform>

   # NPC Agent Credentials
   NPC_AGENT_ID=<uuid-from-platform>
   NPC_API_KEY=<api-key-from-platform>

   # AI Player: Thokk (Fighter)
   THOKK_AGENT_ID=<uuid-from-platform>
   THOKK_API_KEY=<api-key-from-platform>

   # AI Player: Lira (Cleric)
   LIRA_AGENT_ID=<uuid-from-platform>
   LIRA_API_KEY=<api-key-from-platform>

   # LLM API Keys
   ANTHROPIC_API_KEY=<your-anthropic-api-key>
   ```

## Step 3: Create Test Chatroom

1. Log into the Thenvoi platform as a user
2. Navigate to **Chatrooms**
3. Click **Create Chatroom**
4. Name it "Lost Mines Campaign" (or similar)
5. Add the DM Agent as **owner/admin**
6. Add all other agents (NPC, Thokk, Lira) as **members**
7. Note the chatroom ID for testing

Optionally, add the chatroom ID to your `.env`:
```bash
TEST_CHATROOM_ID=<chatroom-id>
```

## Step 4: Verify Connectivity

Run the connectivity test to verify all agents are properly configured:

```bash
python scripts/test_connection.py
```

Expected output for successful setup:
```
==================================================
  Lost Mine of Thenvoi - Connection Test
==================================================

=== Credential Configuration Status ===

  [OK] DM Agent: agent_id=abc12345...
  [OK] NPC Agent: agent_id=def67890...
  [OK] Thokk (Fighter): agent_id=ghi11223...
  [OK] Lira (Cleric): agent_id=jkl44556...
  [OK] Anthropic API Key

  Platform REST URL: https://api.thenvoi.com
  Platform WS URL: wss://api.thenvoi.com/ws

=== Testing 4 Agent Connections ===

  [OK] DM Agent credentials valid
  [OK] NPC Agent credentials valid
  [OK] Thokk credentials valid
  [OK] Lira credentials valid

=== Results: 4/4 agents connected successfully ===
```

## Troubleshooting

### Missing Credentials Error

If you see `[MISSING]` for any agent, ensure:
1. The agent was created on the platform
2. The `agent_id` and `api_key` are correctly copied to `.env`
3. There are no extra spaces or quotes around the values

### Connection Failed Error

If agents fail to connect:
1. Verify your internet connection
2. Check that the Thenvoi platform is accessible
3. Ensure the API keys haven't been rotated
4. Try recreating the agent on the platform

### Anthropic API Key Error

If you see an Anthropic-related error:
1. Verify your Anthropic API key is valid
2. Ensure you have sufficient API credits
3. Check that the key has the required permissions

## Security Notes

- **NEVER** commit your `.env` file to version control
- The `.gitignore` file is configured to exclude `.env`
- Each agent has its own API key for security isolation
- Rotate keys immediately if they are ever exposed
- Keep `.env.example` updated as a template (without real values)

## Next Steps

After completing platform setup:

1. Run the test suite: `pytest`
2. Start the DM agent: `python -m src.agents.dm_agent`
3. Join the chatroom as a human player
4. Begin your adventure!

See the [Architecture Documentation](./architecture.md) for detailed information about how the agents interact.
