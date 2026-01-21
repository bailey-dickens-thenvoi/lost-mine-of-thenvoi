"""Configuration management for Lost Mine of Thenvoi.

This module provides typed configuration loading from environment variables
using pydantic-settings. All agent credentials and platform URLs are validated
at startup.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentCredentials(BaseSettings):
    """Credentials for a single Thenvoi agent."""

    agent_id: str = ""
    api_key: str = ""

    def is_configured(self) -> bool:
        """Check if this agent has valid credentials."""
        return bool(self.agent_id and self.api_key)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or a .env file.
    The .env file should be in the project root directory.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Thenvoi Platform URLs
    thenvoi_rest_url: str = Field(
        default="https://api.thenvoi.com",
        description="Thenvoi REST API base URL",
    )
    thenvoi_ws_url: str = Field(
        default="wss://api.thenvoi.com/ws",
        description="Thenvoi WebSocket URL",
    )

    # DM Agent Credentials
    dm_agent_id: str = Field(default="", description="DM Agent UUID from Thenvoi platform")
    dm_api_key: str = Field(default="", description="DM Agent API key from Thenvoi platform")

    # NPC Agent Credentials
    npc_agent_id: str = Field(default="", description="NPC Agent UUID from Thenvoi platform")
    npc_api_key: str = Field(default="", description="NPC Agent API key from Thenvoi platform")

    # AI Player: Thokk (Fighter)
    thokk_agent_id: str = Field(default="", description="Thokk Agent UUID from Thenvoi platform")
    thokk_api_key: str = Field(default="", description="Thokk Agent API key from Thenvoi platform")

    # AI Player: Lira (Cleric)
    lira_agent_id: str = Field(default="", description="Lira Agent UUID from Thenvoi platform")
    lira_api_key: str = Field(default="", description="Lira Agent API key from Thenvoi platform")

    # LLM API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude models")

    # Optional: Test Chatroom
    test_chatroom_id: Optional[str] = Field(
        default=None,
        description="Optional test chatroom ID for development",
    )

    @field_validator("thenvoi_rest_url", "thenvoi_ws_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URLs don't have trailing slashes."""
        return v.rstrip("/")

    def get_dm_credentials(self) -> AgentCredentials:
        """Get DM agent credentials."""
        return AgentCredentials(agent_id=self.dm_agent_id, api_key=self.dm_api_key)

    def get_npc_credentials(self) -> AgentCredentials:
        """Get NPC agent credentials."""
        return AgentCredentials(agent_id=self.npc_agent_id, api_key=self.npc_api_key)

    def get_thokk_credentials(self) -> AgentCredentials:
        """Get Thokk (Fighter) agent credentials."""
        return AgentCredentials(agent_id=self.thokk_agent_id, api_key=self.thokk_api_key)

    def get_lira_credentials(self) -> AgentCredentials:
        """Get Lira (Cleric) agent credentials."""
        return AgentCredentials(agent_id=self.lira_agent_id, api_key=self.lira_api_key)

    def validate_required_credentials(self, agents: list[str] | None = None) -> list[str]:
        """Validate that required agent credentials are configured.

        Args:
            agents: List of agent names to validate. If None, validates all agents.
                   Valid names: 'dm', 'npc', 'thokk', 'lira'

        Returns:
            List of missing/unconfigured agent names.
        """
        credential_map = {
            "dm": self.get_dm_credentials(),
            "npc": self.get_npc_credentials(),
            "thokk": self.get_thokk_credentials(),
            "lira": self.get_lira_credentials(),
        }

        if agents is None:
            agents = list(credential_map.keys())

        missing = []
        for agent in agents:
            if agent in credential_map and not credential_map[agent].is_configured():
                missing.append(agent)

        return missing

    def is_anthropic_configured(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Uses lru_cache to ensure settings are only loaded once.
    Call get_settings.cache_clear() to reload settings.
    """
    return Settings()


# Convenience alias
settings = get_settings()
