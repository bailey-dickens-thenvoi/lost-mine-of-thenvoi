"""Tests for platform setup and connectivity.

These tests verify the configuration validation and credential checking
functionality without requiring actual platform connectivity.
"""

import pytest

from src.config import Settings, AgentCredentials


class TestAgentCredentials:
    """Tests for AgentCredentials class."""

    def test_empty_credentials_not_configured(self):
        """Empty credentials should report as not configured."""
        creds = AgentCredentials(agent_id="", api_key="")
        assert not creds.is_configured()

    def test_partial_credentials_not_configured(self):
        """Partial credentials should report as not configured."""
        creds1 = AgentCredentials(agent_id="some-id", api_key="")
        assert not creds1.is_configured()

        creds2 = AgentCredentials(agent_id="", api_key="some-key")
        assert not creds2.is_configured()

    def test_complete_credentials_configured(self):
        """Complete credentials should report as configured."""
        creds = AgentCredentials(
            agent_id="test-agent-id",
            api_key="test-api-key"
        )
        assert creds.is_configured()


class TestSettingsValidation:
    """Tests for Settings validation methods."""

    def test_validate_required_credentials_all_missing(self):
        """Should return all agents when none are configured."""
        # Create settings with no credentials
        settings = Settings(
            dm_agent_id="",
            dm_api_key="",
            npc_agent_id="",
            npc_api_key="",
            thokk_agent_id="",
            thokk_api_key="",
            lira_agent_id="",
            lira_api_key="",
        )

        missing = settings.validate_required_credentials()
        assert "dm" in missing
        assert "npc" in missing
        assert "thokk" in missing
        assert "lira" in missing

    def test_validate_required_credentials_partial(self):
        """Should return only missing agents when some are configured."""
        settings = Settings(
            dm_agent_id="dm-id",
            dm_api_key="dm-key",
            npc_agent_id="",
            npc_api_key="",
            thokk_agent_id="thokk-id",
            thokk_api_key="thokk-key",
            lira_agent_id="",
            lira_api_key="",
        )

        missing = settings.validate_required_credentials()
        assert "dm" not in missing
        assert "npc" in missing
        assert "thokk" not in missing
        assert "lira" in missing

    def test_validate_required_credentials_all_configured(self):
        """Should return empty list when all are configured."""
        settings = Settings(
            dm_agent_id="dm-id",
            dm_api_key="dm-key",
            npc_agent_id="npc-id",
            npc_api_key="npc-key",
            thokk_agent_id="thokk-id",
            thokk_api_key="thokk-key",
            lira_agent_id="lira-id",
            lira_api_key="lira-key",
        )

        missing = settings.validate_required_credentials()
        assert len(missing) == 0

    def test_validate_specific_agents(self):
        """Should validate only specified agents."""
        settings = Settings(
            dm_agent_id="dm-id",
            dm_api_key="dm-key",
            npc_agent_id="",
            npc_api_key="",
            thokk_agent_id="",
            thokk_api_key="",
            lira_agent_id="",
            lira_api_key="",
        )

        # Only check DM - should be configured
        missing = settings.validate_required_credentials(["dm"])
        assert len(missing) == 0

        # Check DM and NPC - NPC should be missing
        missing = settings.validate_required_credentials(["dm", "npc"])
        assert "dm" not in missing
        assert "npc" in missing

    def test_is_anthropic_configured(self):
        """Should check Anthropic API key configuration."""
        settings_no_key = Settings(anthropic_api_key="")
        assert not settings_no_key.is_anthropic_configured()

        settings_with_key = Settings(anthropic_api_key="sk-test-key")
        assert settings_with_key.is_anthropic_configured()

    def test_url_validation_strips_trailing_slash(self):
        """URLs should have trailing slashes stripped."""
        settings = Settings(
            thenvoi_rest_url="https://api.thenvoi.com/",
            thenvoi_ws_url="wss://api.thenvoi.com/ws/",
        )
        assert settings.thenvoi_rest_url == "https://api.thenvoi.com"
        assert settings.thenvoi_ws_url == "wss://api.thenvoi.com/ws"

    def test_get_agent_credentials_methods(self):
        """Credential getter methods should return proper AgentCredentials."""
        settings = Settings(
            dm_agent_id="dm-id",
            dm_api_key="dm-key",
            npc_agent_id="npc-id",
            npc_api_key="npc-key",
            thokk_agent_id="thokk-id",
            thokk_api_key="thokk-key",
            lira_agent_id="lira-id",
            lira_api_key="lira-key",
        )

        dm = settings.get_dm_credentials()
        assert dm.agent_id == "dm-id"
        assert dm.api_key == "dm-key"
        assert dm.is_configured()

        npc = settings.get_npc_credentials()
        assert npc.agent_id == "npc-id"
        assert npc.api_key == "npc-key"

        thokk = settings.get_thokk_credentials()
        assert thokk.agent_id == "thokk-id"
        assert thokk.api_key == "thokk-key"

        lira = settings.get_lira_credentials()
        assert lira.agent_id == "lira-id"
        assert lira.api_key == "lira-key"


class TestCredentialCheckFunction:
    """Tests for the check_credentials helper function."""

    def test_check_credentials_import(self):
        """Should be able to import the check_credentials function."""
        # Import from scripts module
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

        from test_connection import check_credentials
        assert callable(check_credentials)
