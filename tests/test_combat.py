"""Tests for the combat system."""

import tempfile
from pathlib import Path

import pytest

from src.game.combat import (
    ENEMY_STATS,
    WEAPONS,
    advance_turn,
    check_combat_end,
    end_combat,
    get_attack_bonus,
    get_combat_status,
    get_current_combatant,
    get_damage_dice,
    resolve_attack,
    start_combat,
)
from src.tools.world_state import WorldStateManager, reset_world_state_manager


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state manager before each test."""
    reset_world_state_manager()
    yield
    reset_world_state_manager()


@pytest.fixture
def temp_state_file():
    """Create a unique temp file for each test."""
    import uuid
    path = Path(tempfile.gettempdir()) / f"test_combat_{uuid.uuid4()}.json"
    yield str(path)
    if path.exists():
        path.unlink()


@pytest.fixture
def state_manager(temp_state_file):
    """Create a WorldStateManager with temp file."""
    return WorldStateManager(temp_state_file, auto_save=True)


class TestWeaponsAndEnemies:
    """Tests for weapon and enemy stat definitions."""

    def test_weapons_have_required_fields(self):
        """All weapons should have damage, ability, and damage_type."""
        for weapon_name, weapon in WEAPONS.items():
            assert "damage" in weapon, f"{weapon_name} missing damage"
            assert "ability" in weapon, f"{weapon_name} missing ability"
            assert "damage_type" in weapon, f"{weapon_name} missing damage_type"

    def test_enemies_have_required_fields(self):
        """All enemies should have required stat fields."""
        for enemy_type, stats in ENEMY_STATS.items():
            assert "name" in stats, f"{enemy_type} missing name"
            assert "hp" in stats, f"{enemy_type} missing hp"
            assert "ac" in stats, f"{enemy_type} missing ac"
            assert "attack_bonus" in stats, f"{enemy_type} missing attack_bonus"
            assert "damage" in stats, f"{enemy_type} missing damage"

    def test_goblin_stats(self):
        """Goblin stats should match D&D 5e."""
        goblin = ENEMY_STATS["goblin"]
        assert goblin["hp"] == 7
        assert goblin["ac"] == 15


class TestStartCombat:
    """Tests for combat initialization."""

    def test_start_combat_creates_enemies(self, state_manager):
        """Should create enemy entities in world state."""
        result = start_combat(
            party=["human_player", "ai_fighter"],
            enemies=["goblin_1", "goblin_2"],
            state_manager=state_manager,
            enemy_type="goblin",
        )

        assert result.success
        assert state_manager.get_enemy("goblin_1") is not None
        assert state_manager.get_enemy("goblin_2") is not None

    def test_start_combat_rolls_initiative(self, state_manager):
        """Should roll initiative for all combatants."""
        result = start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        assert result.success
        assert len(result.turn_order) == 2
        for combatant in result.turn_order:
            assert combatant.initiative > 0

    def test_start_combat_sorts_by_initiative(self, state_manager):
        """Turn order should be sorted by initiative (highest first)."""
        # Run multiple times to verify sorting
        for _ in range(5):
            result = start_combat(
                party=["human_player", "ai_fighter"],
                enemies=["goblin_1"],
                state_manager=state_manager,
            )

            initiatives = [c.initiative for c in result.turn_order]
            assert initiatives == sorted(initiatives, reverse=True)

            # Reset for next iteration
            end_combat(state_manager)

    def test_start_combat_updates_state(self, state_manager):
        """Should update combat state."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        assert state_manager.get("combat.active") is True
        assert state_manager.get("combat.round") == 1
        assert len(state_manager.get("combat.turn_order")) == 2

    def test_start_combat_announcement(self, state_manager):
        """Should return formatted announcement."""
        result = start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        assert "COMBAT BEGINS" in result.announcement
        assert "TURN ORDER" in result.announcement
        assert "Round 1" in result.announcement


class TestTurnManagement:
    """Tests for turn order management."""

    def test_get_current_combatant(self, state_manager):
        """Should return current combatant ID."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        current = get_current_combatant(state_manager)
        turn_order = state_manager.get("combat.turn_order")
        assert current == turn_order[0]

    def test_get_current_combatant_not_in_combat(self, state_manager):
        """Should return None when not in combat."""
        assert get_current_combatant(state_manager) is None

    def test_advance_turn(self, state_manager):
        """Should advance to next combatant."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        turn_order = state_manager.get("combat.turn_order")
        first = turn_order[0]
        second = turn_order[1]

        assert get_current_combatant(state_manager) == first

        result = advance_turn(state_manager)
        assert result is not None
        assert result.combatant_id == second
        assert get_current_combatant(state_manager) == second

    def test_advance_turn_round_rollover(self, state_manager):
        """Should increment round when cycling back to start."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # We have 2 combatants, so:
        # Initial: index 0, round 1
        # After 1st advance: index 1, round 1
        # After 2nd advance: index 0, round 2 (rollover)
        advance_turn(state_manager)  # Move to second combatant
        result = advance_turn(state_manager)  # Back to first (index 0), new round

        # The third advance goes back to index 0, triggering new round
        assert result.round_number == 2
        assert result.is_new_round

    def test_advance_turn_skips_dead(self, state_manager):
        """Should skip dead combatants after they're killed."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1", "goblin_2"],
            state_manager=state_manager,
        )

        # Get turn order
        turn_order = state_manager.get("combat.turn_order")

        # Kill goblin_1
        state_manager.update_hp("goblin_1", -100)

        # Find where goblin_1 is in turn order
        if "goblin_1" in turn_order:
            # Advance until just before goblin_1's position
            current = get_current_combatant(state_manager)
            advances = 0
            while current != "goblin_1" and advances < 10:
                result = advance_turn(state_manager)
                if result:
                    current = result.combatant_id
                    # If we were supposed to land on goblin_1 but didn't, it was skipped
                    if advances > 0:
                        assert current != "goblin_1", "Dead goblin_1 should have been skipped"
                advances += 1


class TestAttackResolution:
    """Tests for attack mechanics."""

    def test_get_attack_bonus_character(self, state_manager):
        """Should calculate attack bonus for characters."""
        # ai_fighter has STR 16 (+3) and proficiency +2
        bonus = get_attack_bonus("ai_fighter", "longsword", state_manager)
        assert bonus == 5  # +3 STR + 2 proficiency

    def test_get_attack_bonus_enemy(self, state_manager):
        """Should use predefined attack bonus for enemies."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        bonus = get_attack_bonus("goblin_1", "scimitar", state_manager)
        assert bonus == 4  # Goblin attack bonus

    def test_get_damage_dice_character(self, state_manager):
        """Should calculate damage dice for characters."""
        # ai_fighter uses longsword (1d8) with STR +3
        damage, damage_type = get_damage_dice("ai_fighter", "longsword", state_manager)
        assert "1d8" in damage
        assert "+3" in damage
        assert damage_type == "slashing"

    def test_get_damage_dice_enemy(self, state_manager):
        """Should use predefined damage for enemies."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        damage, damage_type = get_damage_dice("goblin_1", "scimitar", state_manager)
        assert damage == "1d6+2"

    def test_resolve_attack_hit(self, state_manager):
        """Should resolve a hitting attack."""
        start_combat(
            party=["ai_fighter"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # Run multiple attacks to likely get a hit
        hit_count = 0
        for _ in range(20):
            enemy = state_manager.get_enemy("goblin_1")
            if not enemy or enemy.hp <= 0:
                # Reset enemy
                state_manager.state.enemies["goblin_1"].hp = 7

            result = resolve_attack(
                attacker_id="ai_fighter",
                target_id="goblin_1",
                weapon="longsword",
                state_manager=state_manager,
            )

            if result.hit:
                hit_count += 1
                assert result.damage > 0
                assert result.target_hp_after < result.target_hp_before

        # Should have hit at least once in 20 tries
        assert hit_count > 0

    def test_resolve_attack_miss(self, state_manager):
        """Should handle misses correctly."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # Run attacks until we get a miss
        for _ in range(50):
            enemy = state_manager.get_enemy("goblin_1")
            if not enemy or enemy.hp <= 0:
                state_manager.state.enemies["goblin_1"].hp = 7

            result = resolve_attack(
                attacker_id="human_player",
                target_id="goblin_1",
                weapon="shortsword",
                state_manager=state_manager,
            )

            if not result.hit:
                assert result.damage == 0
                assert result.target_hp_after == result.target_hp_before
                assert "miss" in result.narrative.lower()
                break

    def test_resolve_attack_defeats_target(self, state_manager):
        """Should mark target as defeated at 0 HP."""
        start_combat(
            party=["ai_fighter"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # Damage goblin to near death
        state_manager.update_hp("goblin_1", -6)

        # Attack until we kill it
        for _ in range(20):
            enemy = state_manager.get_enemy("goblin_1")
            if not enemy or enemy.hp <= 0:
                break

            result = resolve_attack(
                attacker_id="ai_fighter",
                target_id="goblin_1",
                weapon="longsword",
                state_manager=state_manager,
            )

            if result.target_defeated:
                assert result.target_hp_after == 0
                assert "down" in result.narrative.lower() or "falls" in result.narrative.lower()
                break

    def test_resolve_attack_narrative(self, state_manager):
        """Attack should return narrative text with attacker name."""
        start_combat(
            party=["ai_fighter"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        result = resolve_attack(
            attacker_id="ai_fighter",
            target_id="goblin_1",
            weapon="longsword",
            state_manager=state_manager,
        )

        assert result.narrative
        assert "Thokk" in result.narrative  # ai_fighter's name
        # Target name appears in most narratives except fumbles
        if not result.fumble:
            assert "Goblin" in result.narrative


class TestCombatEnd:
    """Tests for combat end conditions."""

    def test_check_combat_end_enemies_dead(self, state_manager):
        """Should detect when all enemies are dead."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # Kill the goblin
        state_manager.update_hp("goblin_1", -100)

        result = check_combat_end(state_manager)
        assert result is not None
        assert result.reason == "enemies_defeated"
        assert "Victory" in result.narrative

    def test_check_combat_end_party_down(self, state_manager):
        """Should detect when all party members are down."""
        start_combat(
            party=["human_player", "ai_fighter", "ai_cleric"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        # Down all party members
        state_manager.update_hp("human_player", -100)
        state_manager.update_hp("ai_fighter", -100)
        state_manager.update_hp("ai_cleric", -100)

        result = check_combat_end(state_manager)
        assert result is not None
        assert result.reason == "party_defeated"

    def test_check_combat_end_ongoing(self, state_manager):
        """Should return None when combat should continue."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        result = check_combat_end(state_manager)
        assert result is None

    def test_end_combat_clears_state(self, state_manager):
        """Should clear combat state."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        end_combat(state_manager)

        assert state_manager.get("combat.active") is False
        assert state_manager.get("combat.round") == 0
        assert state_manager.get("combat.turn_order") == []

    def test_end_combat_removes_dead_enemies(self, state_manager):
        """Should remove dead enemies from state."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        state_manager.update_hp("goblin_1", -100)
        end_combat(state_manager, reason="enemies_defeated")

        assert state_manager.get_enemy("goblin_1") is None


class TestCombatStatus:
    """Tests for combat status display."""

    def test_get_combat_status_not_in_combat(self, state_manager):
        """Should indicate not in combat."""
        status = get_combat_status(state_manager)
        assert "Not in combat" in status

    def test_get_combat_status_shows_party(self, state_manager):
        """Should show party member status."""
        start_combat(
            party=["human_player", "ai_fighter"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        status = get_combat_status(state_manager)
        assert "PARTY" in status
        assert "Vex" in status
        assert "Thokk" in status

    def test_get_combat_status_shows_enemies(self, state_manager):
        """Should show enemy status."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        status = get_combat_status(state_manager)
        assert "ENEMIES" in status
        assert "Goblin" in status

    def test_get_combat_status_shows_round(self, state_manager):
        """Should show current round."""
        start_combat(
            party=["human_player"],
            enemies=["goblin_1"],
            state_manager=state_manager,
        )

        status = get_combat_status(state_manager)
        assert "Round 1" in status
