"""Tests for AI Player Agents."""

import pytest

from src.agents.player_agent import (
    AIPlayerAdapter,
    ClericAdapter,
    FighterAdapter,
    LIRA_CHARACTER,
    THOKK_CHARACTER,
    AI_PLAYER_PROMPT,
    FIGHTER_COMBAT_PRIORITIES,
    FIGHTER_PERSONALITY,
    CLERIC_COMBAT_PRIORITIES,
    CLERIC_PERSONALITY,
    build_player_system_prompt,
)


class TestCharacterData:
    """Tests for character data definitions."""

    def test_thokk_has_required_fields(self):
        """Thokk should have all required character fields."""
        assert THOKK_CHARACTER["name"] == "Thokk"
        assert THOKK_CHARACTER["race"] == "Half-Orc"
        assert THOKK_CHARACTER["character_class"] == "Fighter"
        assert "stats" in THOKK_CHARACTER
        assert THOKK_CHARACTER["stats"]["str"] == 16
        assert THOKK_CHARACTER["hp"] == 12
        assert THOKK_CHARACTER["ac"] == 16

    def test_thokk_has_features(self):
        """Thokk should have fighter features."""
        features = THOKK_CHARACTER["features"]
        feature_text = " ".join(features).lower()
        assert "second wind" in feature_text
        assert "fighting style" in feature_text

    def test_lira_has_required_fields(self):
        """Lira should have all required character fields."""
        assert LIRA_CHARACTER["name"] == "Lira"
        assert LIRA_CHARACTER["race"] == "Human"
        assert LIRA_CHARACTER["character_class"] == "Cleric (Life Domain)"
        assert "stats" in LIRA_CHARACTER
        assert LIRA_CHARACTER["stats"]["wis"] == 16
        assert LIRA_CHARACTER["hp"] == 10
        assert LIRA_CHARACTER["ac"] == 16

    def test_lira_has_spells(self):
        """Lira should have cleric spells."""
        spells = LIRA_CHARACTER["spells"]
        assert "cantrips" in spells
        assert "1st_level_prepared" in spells

        cantrips_text = " ".join(spells["cantrips"]).lower()
        assert "sacred flame" in cantrips_text

        spells_text = " ".join(spells["1st_level_prepared"]).lower()
        assert "cure wounds" in spells_text
        assert "healing word" in spells_text


class TestSystemPromptTemplate:
    """Tests for the AI player system prompt template."""

    def test_prompt_has_placeholders(self):
        """Template should have all necessary placeholders."""
        assert "{name}" in AI_PLAYER_PROMPT
        assert "{race}" in AI_PLAYER_PROMPT
        assert "{character_class}" in AI_PLAYER_PROMPT
        assert "{personality_section}" in AI_PLAYER_PROMPT
        assert "{combat_priorities}" in AI_PLAYER_PROMPT

    def test_prompt_has_action_format(self):
        """Template should explain action format."""
        assert "Attack" in AI_PLAYER_PROMPT
        assert "Spell" in AI_PLAYER_PROMPT
        assert "Help" in AI_PLAYER_PROMPT

    def test_prompt_mentions_send_message(self):
        """Template should require send_message tool."""
        assert "send_message" in AI_PLAYER_PROMPT

    def test_prompt_mentions_dm_rolls_dice(self):
        """Template should clarify DM rolls dice."""
        assert "DM" in AI_PLAYER_PROMPT
        assert "roll" in AI_PLAYER_PROMPT.lower()

    def test_prompt_lists_party_members(self):
        """Template should list party members."""
        assert "Vex" in AI_PLAYER_PROMPT
        assert "Thokk" in AI_PLAYER_PROMPT
        assert "Lira" in AI_PLAYER_PROMPT


class TestFighterPrompts:
    """Tests for Fighter-specific prompts."""

    def test_fighter_priorities_focus_on_protection(self):
        """Fighter priorities should emphasize protection."""
        assert "protect" in FIGHTER_COMBAT_PRIORITIES.lower()
        assert "wounded" in FIGHTER_COMBAT_PRIORITIES.lower()

    def test_fighter_priorities_mention_second_wind(self):
        """Fighter priorities should mention Second Wind."""
        assert "Second Wind" in FIGHTER_COMBAT_PRIORITIES

    def test_fighter_personality_is_direct(self):
        """Fighter personality should be direct."""
        assert "direct" in FIGHTER_PERSONALITY.lower()
        assert "short" in FIGHTER_PERSONALITY.lower()

    def test_fighter_has_example_phrases(self):
        """Fighter personality should include example phrases."""
        assert "I'll handle this" in FIGHTER_PERSONALITY


class TestClericPrompts:
    """Tests for Cleric-specific prompts."""

    def test_cleric_priorities_focus_on_healing(self):
        """Cleric priorities should emphasize healing."""
        assert "heal" in CLERIC_COMBAT_PRIORITIES.lower()
        assert "alive" in CLERIC_COMBAT_PRIORITIES.lower()

    def test_cleric_priorities_mention_bless(self):
        """Cleric priorities should mention Bless spell."""
        assert "Bless" in CLERIC_COMBAT_PRIORITIES

    def test_cleric_priorities_mention_spell_slots(self):
        """Cleric priorities should discuss spell slot management."""
        assert "spell slot" in CLERIC_COMBAT_PRIORITIES.lower()

    def test_cleric_personality_is_compassionate(self):
        """Cleric personality should be compassionate."""
        assert "compassion" in CLERIC_PERSONALITY.lower()

    def test_cleric_has_example_phrases(self):
        """Cleric personality should include example phrases."""
        assert "light" in CLERIC_PERSONALITY.lower() or "heal" in CLERIC_PERSONALITY.lower()


class TestBuildPlayerSystemPrompt:
    """Tests for system prompt building."""

    def test_builds_fighter_prompt(self):
        """Should build a complete prompt for the Fighter."""
        prompt = build_player_system_prompt(
            THOKK_CHARACTER,
            FIGHTER_PERSONALITY,
            FIGHTER_COMBAT_PRIORITIES,
        )

        assert "Thokk" in prompt
        assert "Half-Orc" in prompt
        assert "Fighter" in prompt
        assert "Second Wind" in prompt
        assert "I'll handle this" in prompt

    def test_builds_cleric_prompt(self):
        """Should build a complete prompt for the Cleric."""
        prompt = build_player_system_prompt(
            LIRA_CHARACTER,
            CLERIC_PERSONALITY,
            CLERIC_COMBAT_PRIORITIES,
        )

        assert "Lira" in prompt
        assert "Human" in prompt
        assert "Cleric" in prompt
        assert "cure wounds" in prompt.lower()
        assert "sacred flame" in prompt.lower()

    def test_includes_stats(self):
        """Prompt should include character stats."""
        prompt = build_player_system_prompt(
            THOKK_CHARACTER,
            FIGHTER_PERSONALITY,
            FIGHTER_COMBAT_PRIORITIES,
        )

        assert "STR 16" in prompt
        assert "AC: 16" in prompt

    def test_includes_skills(self):
        """Prompt should include character skills."""
        prompt = build_player_system_prompt(
            THOKK_CHARACTER,
            FIGHTER_PERSONALITY,
            FIGHTER_COMBAT_PRIORITIES,
        )

        assert "athletics" in prompt.lower()
        assert "intimidation" in prompt.lower()

    def test_includes_equipment(self):
        """Prompt should include character equipment."""
        prompt = build_player_system_prompt(
            THOKK_CHARACTER,
            FIGHTER_PERSONALITY,
            FIGHTER_COMBAT_PRIORITIES,
        )

        assert "longsword" in prompt.lower()
        assert "shield" in prompt.lower()


class TestAIPlayerAdapter:
    """Tests for AIPlayerAdapter class."""

    def test_creates_with_character(self):
        """Should create adapter with character data."""
        adapter = AIPlayerAdapter(
            character=THOKK_CHARACTER,
            personality_section=FIGHTER_PERSONALITY,
            combat_priorities=FIGHTER_COMBAT_PRIORITIES,
            agent_id="thokk",
        )

        assert adapter.character == THOKK_CHARACTER
        assert adapter.agent_id == "thokk"

    def test_stores_system_prompt(self):
        """Should have a system prompt set."""
        adapter = AIPlayerAdapter(
            character=THOKK_CHARACTER,
            personality_section=FIGHTER_PERSONALITY,
            combat_priorities=FIGHTER_COMBAT_PRIORITIES,
            agent_id="thokk",
        )

        # The system prompt should be set in the parent class
        assert adapter.system_prompt is not None
        assert "Thokk" in adapter.system_prompt


class TestFighterAdapter:
    """Tests for FighterAdapter class."""

    def test_uses_thokk_character(self):
        """Should use Thokk's character data."""
        adapter = FighterAdapter()
        assert adapter.character["name"] == "Thokk"

    def test_has_fighter_system_prompt(self):
        """Should have Fighter-specific system prompt."""
        adapter = FighterAdapter()
        assert "Thokk" in adapter.system_prompt
        assert "Fighter" in adapter.system_prompt
        assert "Second Wind" in adapter.system_prompt

    def test_enables_execution_reporting(self):
        """Should have execution reporting enabled."""
        adapter = FighterAdapter()
        assert adapter.enable_execution_reporting is True


class TestClericAdapter:
    """Tests for ClericAdapter class."""

    def test_uses_lira_character(self):
        """Should use Lira's character data."""
        adapter = ClericAdapter()
        assert adapter.character["name"] == "Lira"

    def test_has_cleric_system_prompt(self):
        """Should have Cleric-specific system prompt."""
        adapter = ClericAdapter()
        assert "Lira" in adapter.system_prompt
        assert "Cleric" in adapter.system_prompt
        assert "heal" in adapter.system_prompt.lower()

    def test_enables_execution_reporting(self):
        """Should have execution reporting enabled."""
        adapter = ClericAdapter()
        assert adapter.enable_execution_reporting is True


class TestAdapterDistinctPersonalities:
    """Tests to ensure adapters have distinct personalities."""

    def test_fighter_and_cleric_have_different_prompts(self):
        """Fighter and Cleric should have different system prompts."""
        fighter = FighterAdapter()
        cleric = ClericAdapter()

        assert fighter.system_prompt != cleric.system_prompt

    def test_fighter_prompt_more_aggressive(self):
        """Fighter prompt should emphasize combat."""
        fighter = FighterAdapter()
        prompt_lower = fighter.system_prompt.lower()

        # Count combat-related words
        combat_words = ["attack", "fight", "protect", "threat", "damage"]
        combat_count = sum(1 for w in combat_words if w in prompt_lower)
        assert combat_count >= 3

    def test_cleric_prompt_more_supportive(self):
        """Cleric prompt should emphasize support."""
        cleric = ClericAdapter()
        prompt_lower = cleric.system_prompt.lower()

        # Count support-related words
        support_words = ["heal", "cure", "bless", "alive", "support"]
        support_count = sum(1 for w in support_words if w in prompt_lower)
        assert support_count >= 3
