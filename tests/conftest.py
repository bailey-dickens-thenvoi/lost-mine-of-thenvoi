"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import patch

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def clean_settings_cache():
    """Clear settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_env_empty():
    """Fixture that clears all environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def mock_env_full():
    """Fixture that provides complete environment configuration."""
    env = {
        "THENVOI_REST_URL": "https://api.thenvoi.com",
        "THENVOI_WS_URL": "wss://api.thenvoi.com/ws",
        "DM_AGENT_ID": "dm-agent-id",
        "DM_API_KEY": "dm-api-key",
        "NPC_AGENT_ID": "npc-agent-id",
        "NPC_API_KEY": "npc-api-key",
        "THOKK_AGENT_ID": "thokk-agent-id",
        "THOKK_API_KEY": "thokk-api-key",
        "LIRA_AGENT_ID": "lira-agent-id",
        "LIRA_API_KEY": "lira-api-key",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "TEST_CHATROOM_ID": "test-chatroom-id",
    }
    with patch.dict(os.environ, env, clear=True):
        yield env
