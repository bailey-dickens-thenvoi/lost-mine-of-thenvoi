"""Tests for the dice rolling system."""

import pytest

from src.tools.dice import (
    DiceRollResult,
    check_hit,
    check_success,
    dice_tool,
    format_roll_result,
    parse_dice_notation,
    roll_ability_check,
    roll_attack,
    roll_damage,
    roll_dice,
    roll_initiative,
    roll_saving_throw,
)


class TestParseDiceNotation:
    """Tests for dice notation parsing."""

    def test_simple_d20(self):
        """Parse 1d20."""
        assert parse_dice_notation("1d20") == (1, 20, 0)

    def test_multiple_dice(self):
        """Parse 2d6."""
        assert parse_dice_notation("2d6") == (2, 6, 0)

    def test_positive_modifier(self):
        """Parse 1d20+5."""
        assert parse_dice_notation("1d20+5") == (1, 20, 5)

    def test_negative_modifier(self):
        """Parse 1d8-1."""
        assert parse_dice_notation("1d8-1") == (1, 8, -1)

    def test_multiple_dice_with_modifier(self):
        """Parse 2d6+3."""
        assert parse_dice_notation("2d6+3") == (2, 6, 3)

    def test_large_numbers(self):
        """Parse 10d10+20."""
        assert parse_dice_notation("10d10+20") == (10, 10, 20)

    def test_case_insensitive(self):
        """Parse D20 (uppercase)."""
        assert parse_dice_notation("1D20") == (1, 20, 0)

    def test_whitespace(self):
        """Parse with whitespace."""
        assert parse_dice_notation("  1d20+5  ") == (1, 20, 5)

    def test_invalid_notation(self):
        """Reject invalid notation."""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("invalid")

    def test_empty_string(self):
        """Reject empty string."""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("")

    def test_missing_d(self):
        """Reject notation without 'd'."""
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("20")


class TestRollDice:
    """Tests for the roll_dice function."""

    def test_basic_roll_structure(self):
        """Roll returns proper structure."""
        result = roll_dice("1d20", "test", "tester")

        assert "rolls" in result
        assert "modifier" in result
        assert "total" in result
        assert "purpose" in result
        assert "roller" in result
        assert result["purpose"] == "test"
        assert result["roller"] == "tester"

    def test_roll_range_d20(self):
        """d20 results should be 1-20."""
        for _ in range(100):
            result = roll_dice("1d20", "test", "tester")
            assert 1 <= result["rolls"][0] <= 20
            assert result["total"] == result["rolls"][0]

    def test_roll_range_d6(self):
        """d6 results should be 1-6."""
        for _ in range(100):
            result = roll_dice("1d6", "test", "tester")
            assert 1 <= result["rolls"][0] <= 6

    def test_multiple_dice(self):
        """2d6 should roll two dice."""
        result = roll_dice("2d6", "test", "tester")
        assert len(result["rolls"]) == 2
        assert all(1 <= r <= 6 for r in result["rolls"])
        assert result["total"] == sum(result["rolls"])

    def test_modifier_applied(self):
        """Modifier should be added to total."""

        def mock_roll(a, b):
            return 10

        result = roll_dice("1d20+5", "test", "tester", rand_func=mock_roll)
        assert result["rolls"] == [10]
        assert result["modifier"] == 5
        assert result["total"] == 15

    def test_negative_modifier(self):
        """Negative modifier should subtract from total."""

        def mock_roll(a, b):
            return 10

        result = roll_dice("1d20-3", "test", "tester", rand_func=mock_roll)
        assert result["total"] == 7

    def test_advantage_rolls_twice(self):
        """Advantage should roll twice and take higher."""
        calls = []

        def mock_roll(a, b):
            calls.append(1)
            return 10 if len(calls) == 1 else 15

        result = roll_dice("1d20", "test", "tester", advantage=True, rand_func=mock_roll)
        assert len(result["rolls"]) == 2
        assert result["rolls"] == [10, 15]
        assert result["kept_roll"] == 15
        assert result["total"] == 15
        assert result["advantage_used"] is True

    def test_disadvantage_rolls_twice(self):
        """Disadvantage should roll twice and take lower."""
        calls = []

        def mock_roll(a, b):
            calls.append(1)
            return 15 if len(calls) == 1 else 10

        result = roll_dice("1d20", "test", "tester", disadvantage=True, rand_func=mock_roll)
        assert len(result["rolls"]) == 2
        assert result["kept_roll"] == 10
        assert result["total"] == 10
        assert result["disadvantage_used"] is True

    def test_advantage_only_on_d20(self):
        """Advantage should only affect d20 rolls."""
        result = roll_dice("2d6", "test", "tester", advantage=True)
        assert len(result["rolls"]) == 2  # Still 2 dice, not 4
        assert result["advantage_used"] is False

    def test_advantage_and_disadvantage_cancel(self):
        """If both advantage and disadvantage, neither applies."""
        result = roll_dice("1d20", "test", "tester", advantage=True, disadvantage=True)
        assert len(result["rolls"]) == 1
        assert result["advantage_used"] is False
        assert result["disadvantage_used"] is False

    def test_critical_detection(self):
        """Natural 20 should be marked as critical."""

        def mock_roll(a, b):
            return 20

        result = roll_dice("1d20", "test", "tester", rand_func=mock_roll)
        assert result["critical"] is True
        assert result["fumble"] is False

    def test_fumble_detection(self):
        """Natural 1 should be marked as fumble."""

        def mock_roll(a, b):
            return 1

        result = roll_dice("1d20", "test", "tester", rand_func=mock_roll)
        assert result["fumble"] is True
        assert result["critical"] is False

    def test_critical_with_advantage(self):
        """Critical detection works with advantage."""
        calls = []

        def mock_roll(a, b):
            calls.append(1)
            return 10 if len(calls) == 1 else 20

        result = roll_dice("1d20", "test", "tester", advantage=True, rand_func=mock_roll)
        assert result["critical"] is True
        assert result["kept_roll"] == 20

    def test_no_critical_on_damage_dice(self):
        """Non-d20 rolls don't have criticals."""

        def mock_roll(a, b):
            return 6  # Max on d6, but not a critical

        result = roll_dice("1d6", "test", "tester", rand_func=mock_roll)
        assert result["critical"] is False


class TestFormatRollResult:
    """Tests for roll result formatting."""

    def test_basic_format(self):
        """Format basic roll."""
        result = {
            "rolls": [15],
            "modifier": 5,
            "total": 20,
            "purpose": "Attack Roll",
            "roller": "Vex",
            "advantage_used": False,
            "disadvantage_used": False,
            "critical": False,
            "fumble": False,
            "kept_roll": None,
        }
        formatted = format_roll_result(result)
        assert "Attack Roll" in formatted
        assert "Vex" in formatted
        assert "[15]" in formatted
        assert "+ 5" in formatted
        assert "= 20" in formatted

    def test_format_with_advantage(self):
        """Format roll with advantage."""
        result = {
            "rolls": [8, 17],
            "modifier": 4,
            "total": 21,
            "purpose": "Stealth Check",
            "roller": "Vex",
            "advantage_used": True,
            "disadvantage_used": False,
            "critical": False,
            "fumble": False,
            "kept_roll": 17,
        }
        formatted = format_roll_result(result)
        assert "(advantage)" in formatted
        assert "(took 17)" in formatted

    def test_format_critical(self):
        """Format critical hit."""
        result = {
            "rolls": [20],
            "modifier": 5,
            "total": 25,
            "purpose": "Attack Roll",
            "roller": "Thokk",
            "advantage_used": False,
            "disadvantage_used": False,
            "critical": True,
            "fumble": False,
            "kept_roll": None,
        }
        formatted = format_roll_result(result)
        assert "CRITICAL HIT!" in formatted

    def test_format_fumble(self):
        """Format fumble."""
        result = {
            "rolls": [1],
            "modifier": 5,
            "total": 6,
            "purpose": "Attack Roll",
            "roller": "Goblin",
            "advantage_used": False,
            "disadvantage_used": False,
            "critical": False,
            "fumble": True,
            "kept_roll": None,
        }
        formatted = format_roll_result(result)
        assert "FUMBLE!" in formatted

    def test_format_negative_modifier(self):
        """Format with negative modifier."""
        result = {
            "rolls": [10],
            "modifier": -2,
            "total": 8,
            "purpose": "Strength Check",
            "roller": "Vex",
            "advantage_used": False,
            "disadvantage_used": False,
            "critical": False,
            "fumble": False,
            "kept_roll": None,
        }
        formatted = format_roll_result(result)
        assert "- 2" in formatted

    def test_format_multiple_dice(self):
        """Format multiple dice roll."""
        result = {
            "rolls": [4, 6, 3],
            "modifier": 3,
            "total": 16,
            "purpose": "Damage",
            "roller": "Thokk",
            "advantage_used": False,
            "disadvantage_used": False,
            "critical": False,
            "fumble": False,
            "kept_roll": None,
        }
        formatted = format_roll_result(result)
        assert "[4, 6, 3]" in formatted


class TestCheckHit:
    """Tests for hit checking."""

    def test_hit_equals_ac(self):
        """Attack equals AC should hit."""
        assert check_hit(15, 15) is True

    def test_hit_exceeds_ac(self):
        """Attack exceeds AC should hit."""
        assert check_hit(18, 15) is True

    def test_miss_below_ac(self):
        """Attack below AC should miss."""
        assert check_hit(14, 15) is False

    def test_critical_always_hits(self):
        """Critical hit always hits regardless of AC."""
        assert check_hit(5, 25, is_critical=True) is True


class TestCheckSuccess:
    """Tests for save/check success."""

    def test_success_meets_dc(self):
        """Meeting DC should succeed."""
        assert check_success(15, 15) is True

    def test_success_exceeds_dc(self):
        """Exceeding DC should succeed."""
        assert check_success(18, 15) is True

    def test_failure_below_dc(self):
        """Below DC should fail."""
        assert check_success(14, 15) is False

    def test_natural_20_always_succeeds(self):
        """Natural 20 always succeeds."""
        assert check_success(10, 25, is_natural_20=True) is True

    def test_natural_1_always_fails(self):
        """Natural 1 always fails."""
        assert check_success(25, 10, is_natural_1=True) is False


class TestConvenienceFunctions:
    """Tests for convenience roll functions."""

    def test_roll_initiative(self):
        """Roll initiative with DEX modifier."""

        def mock_roll(a, b):
            return 15

        result = roll_initiative("Vex", 3, rand_func=mock_roll)
        assert result["purpose"] == "Initiative"
        assert result["roller"] == "Vex"
        assert result["total"] == 18

    def test_roll_attack(self):
        """Roll attack with bonus."""

        def mock_roll(a, b):
            return 15

        result = roll_attack("Thokk", 5, rand_func=mock_roll)
        assert result["purpose"] == "Attack Roll"
        assert result["total"] == 20

    def test_roll_damage(self):
        """Roll damage."""

        def mock_roll(a, b):
            return 4

        result = roll_damage("Thokk", "1d8+3", "slashing", rand_func=mock_roll)
        assert "Slashing Damage" in result["purpose"]
        assert result["total"] == 7

    def test_roll_damage_critical(self):
        """Critical damage doubles dice."""

        def mock_roll(a, b):
            return 4

        result = roll_damage("Thokk", "1d8+3", "slashing", is_critical=True, rand_func=mock_roll)
        assert len(result["rolls"]) == 2  # Doubled from 1 to 2
        assert result["total"] == 11  # (4 + 4) + 3

    def test_roll_ability_check(self):
        """Roll ability check."""

        def mock_roll(a, b):
            return 12

        result = roll_ability_check("Vex", "Stealth", 7, rand_func=mock_roll)
        assert "Stealth Check" in result["purpose"]
        assert result["total"] == 19

    def test_roll_saving_throw(self):
        """Roll saving throw."""

        def mock_roll(a, b):
            return 10

        result = roll_saving_throw("Lira", "WIS", 5, rand_func=mock_roll)
        assert "WIS Save" in result["purpose"]
        assert result["total"] == 15


class TestDiceTool:
    """Tests for the dice_tool function."""

    def test_tool_returns_formatted_string(self):
        """Tool should return formatted string."""
        result = dice_tool("1d20+5", "Attack Roll", "Vex")
        assert isinstance(result, str)
        assert "Attack Roll" in result
        assert "Vex" in result

    def test_tool_handles_error(self):
        """Tool should return error message for invalid notation."""
        result = dice_tool("invalid", "test", "tester")
        assert "Error" in result


class TestDiceRollResult:
    """Tests for DiceRollResult dataclass."""

    def test_to_dict(self):
        """DiceRollResult should convert to dict."""
        result = DiceRollResult(
            rolls=[15],
            modifier=5,
            total=20,
            purpose="Attack Roll",
            roller="Vex",
            advantage_used=False,
            disadvantage_used=False,
            critical=False,
            fumble=False,
            notation="1d20+5",
        )
        d = result.to_dict()
        assert d["rolls"] == [15]
        assert d["total"] == 20
        assert d["notation"] == "1d20+5"
