"""Testing utilities for Lost Mine of Thenvoi.

This package provides:
- MockThenvoiPlatform: Simulates the Thenvoi platform for local testing
- AgentTestHarness: Orchestrates agents for integration testing
- FakeAgentTools: Mock implementation of AgentToolsProtocol
"""

from src.testing.mock_platform import MockThenvoiPlatform, MockMessage
from src.testing.harness import AgentTestHarness
from src.testing.fake_tools import FakeAgentTools

__all__ = [
    "MockThenvoiPlatform",
    "MockMessage",
    "AgentTestHarness",
    "FakeAgentTools",
]
