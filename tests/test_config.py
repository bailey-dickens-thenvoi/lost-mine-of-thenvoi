"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from src.config import AgentCredentials, Settings, get_settings


class TestAgentCredentials:
    """Tests for AgentCredentials class."""

    def test_empty_credentials_not_configured(self):
        """Empty credentials should not be considered configured."""
        creds = AgentCredentials(agent_id="", api_key="")
        assert not creds.is_configured()

    def test_partial_credentials_not_configured(self):
        """Partial credentials should not be considered configured."""
        creds = AgentCredentials(agent_id="abc123", api_key="")
        assert not creds.is_configured()

        creds = AgentCredentials(agent_id="", api_key="secret")
        assert not creds.is_configured()

    def test_full_credentials_configured(self):
        """Full credentials should be considered configured."""
        creds = AgentCredentials(agent_id="abc123", api_key="secret")
        assert creds.is_configured()


class TestSettings:
    """Tests for Settings class."""

    def test_default_urls(self):
        """Default URLs should be set correctly."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear cache to get fresh settings
            get_settings.cache_clear()
            settings = Settings(_env_file=None)

            assert settings.thenvoi_rest_url == "https://app.thenvoi.com"
            assert settings.thenvoi_ws_url == "wss://app.thenvoi.com/api/v1/socket/websocket"

    def test_url_trailing_slash_removed(self):
        """URLs should have trailing slashes removed."""
        with patch.dict(
            os.environ,
            {
                "THENVOI_REST_URL": "https://api.example.com/",
                "THENVOI_WS_URL": "wss://api.example.com/ws/",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.thenvoi_rest_url == "https://api.example.com"
            assert settings.thenvoi_ws_url == "wss://api.example.com/ws"

    def test_get_credentials_methods(self):
        """Credential getter methods should return proper objects."""
        with patch.dict(
            os.environ,
            {
                "DM_AGENT_ID": "dm-id",
                "DM_API_KEY": "dm-key",
                "NPC_AGENT_ID": "npc-id",
                "NPC_API_KEY": "npc-key",
                "THOKK_AGENT_ID": "thokk-id",
                "THOKK_API_KEY": "thokk-key",
                "LIRA_AGENT_ID": "lira-id",
                "LIRA_API_KEY": "lira-key",
            },
            clear=True,
        ):
            settings = Settings()

            dm = settings.get_dm_credentials()
            assert dm.agent_id == "dm-id"
            assert dm.api_key == "dm-key"
            assert dm.is_configured()

            npc = settings.get_npc_credentials()
            assert npc.agent_id == "npc-id"
            assert npc.is_configured()

            thokk = settings.get_thokk_credentials()
            assert thokk.agent_id == "thokk-id"
            assert thokk.is_configured()

            lira = settings.get_lira_credentials()
            assert lira.agent_id == "lira-id"
            assert lira.is_configured()

    def test_validate_required_credentials_all_missing(self):
        """Should report all missing credentials when none are configured."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            missing = settings.validate_required_credentials()

            assert "dm" in missing
            assert "npc" in missing
            assert "thokk" in missing
            assert "lira" in missing

    def test_validate_required_credentials_partial(self):
        """Should report only missing credentials."""
        with patch.dict(
            os.environ,
            {
                "DM_AGENT_ID": "dm-id",
                "DM_API_KEY": "dm-key",
            },
            clear=True,
        ):
            settings = Settings(_env_file=None)
            missing = settings.validate_required_credentials()

            assert "dm" not in missing
            assert "npc" in missing
            assert "thokk" in missing
            assert "lira" in missing

    def test_validate_required_credentials_specific_agents(self):
        """Should validate only specified agents."""
        with patch.dict(
            os.environ,
            {
                "DM_AGENT_ID": "dm-id",
                "DM_API_KEY": "dm-key",
            },
            clear=True,
        ):
            settings = Settings(_env_file=None)

            # Only check DM
            missing = settings.validate_required_credentials(["dm"])
            assert missing == []

            # Check DM and NPC
            missing = settings.validate_required_credentials(["dm", "npc"])
            assert missing == ["npc"]

    def test_is_anthropic_configured(self):
        """Should correctly detect Anthropic configuration."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert not settings.is_anthropic_configured()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.is_anthropic_configured()


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_caches_result(self):
        """get_settings should return the same instance."""
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_clear_reloads_settings(self):
        """Clearing cache should reload settings."""
        get_settings.cache_clear()
        settings1 = get_settings()

        get_settings.cache_clear()
        settings2 = get_settings()

        # They should be equal but not the same object
        assert settings1 is not settings2
