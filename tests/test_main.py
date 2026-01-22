"""Tests for main module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.main import WORLD_STATE_PATH, main, reset_game_state


class TestResetGameState:
    """Tests for reset_game_state function."""

    def test_reset_deletes_existing_file(self, tmp_path, capsys):
        """Should delete world_state.json if it exists."""
        # Create a temporary file to act as world_state.json
        test_file = tmp_path / "world_state.json"
        test_file.write_text('{"test": "data"}')

        # Patch WORLD_STATE_PATH to point to our test file
        with patch("src.main.WORLD_STATE_PATH", test_file):
            reset_game_state()

        # File should be deleted
        assert not test_file.exists()

        # Confirmation message should be printed
        captured = capsys.readouterr()
        assert "[OK] Game state reset. Starting fresh!" in captured.out

    def test_reset_handles_missing_file(self, tmp_path, capsys):
        """Should not error if world_state.json doesn't exist."""
        # Point to a non-existent file
        test_file = tmp_path / "nonexistent.json"

        with patch("src.main.WORLD_STATE_PATH", test_file):
            # Should not raise an exception
            reset_game_state()

        # Confirmation message should still be printed
        captured = capsys.readouterr()
        assert "[OK] Game state reset. Starting fresh!" in captured.out


class TestMainNewGameFlag:
    """Tests for --new-game flag in main()."""

    def test_new_game_flag_resets_and_exits(self, tmp_path, capsys):
        """--new-game alone should reset state and exit."""
        test_file = tmp_path / "world_state.json"
        test_file.write_text('{"test": "data"}')

        with (
            patch("src.main.WORLD_STATE_PATH", test_file),
            patch.object(sys, "argv", ["main", "--new-game"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        # Should exit with code 0
        assert exc_info.value.code == 0

        # File should be deleted
        assert not test_file.exists()

        # Confirmation message should be printed
        captured = capsys.readouterr()
        assert "[OK] Game state reset. Starting fresh!" in captured.out

    def test_new_game_with_agent_resets_then_continues(self, tmp_path, capsys):
        """--new-game --agent should reset state then try to run agent."""
        test_file = tmp_path / "world_state.json"
        test_file.write_text('{"test": "data"}')

        with (
            patch("src.main.WORLD_STATE_PATH", test_file),
            patch.object(sys, "argv", ["main", "--new-game", "--agent", "dm"]),
            # Agent will fail due to missing config, which is expected
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        # Should exit with error code (agent not configured)
        assert exc_info.value.code == 1

        # But file should still be deleted (reset happens first)
        assert not test_file.exists()

        # Reset message should be printed
        captured = capsys.readouterr()
        assert "[OK] Game state reset. Starting fresh!" in captured.out


class TestWorldStatePath:
    """Tests for WORLD_STATE_PATH constant."""

    def test_world_state_path_is_correct(self):
        """WORLD_STATE_PATH should point to data/world_state.json."""
        # The path should end with data/world_state.json
        assert WORLD_STATE_PATH.name == "world_state.json"
        assert WORLD_STATE_PATH.parent.name == "data"
