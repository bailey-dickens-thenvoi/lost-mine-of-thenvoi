"""Pydantic models for D&D game state.

These models define the schema for world state, characters, enemies, and combat.
All state is serializable to JSON for persistence.
"""

from typing import Any

from pydantic import BaseModel, Field


class TurnState(BaseModel):
    """Controls which agent should respond to messages.

    This model is critical for preventing agent response cascades.
    The DM uses the set_turn tool to specify which agent should respond,
    and agents check this state before calling the LLM.
    """

    active_agent: str | None = Field(
        default=None,
        description="Agent ID that should respond: 'thokk', 'lira', 'npc', 'human', or None (DM only)",
    )
    mode: str = Field(
        default="dm_control",
        description="Current flow mode: dm_control, combat, exploration, free_form",
    )
    addressed_agents: list[str] = Field(
        default_factory=list,
        description="List of agent IDs being spoken TO (for free_form mode)",
    )
    turn_started_at: float | None = Field(
        default=None,
        description="Timestamp when turn was set (for staleness detection)",
    )

    def is_agent_turn(self, agent_id: str) -> bool:
        """Check if it's a specific agent's turn.

        Args:
            agent_id: The agent ID to check ('thokk', 'lira', 'npc')

        Returns:
            True if the agent should respond
        """
        # Direct match
        if self.active_agent == agent_id:
            return True

        # Free-form mode: respond if addressed
        if self.mode == "free_form" and agent_id in self.addressed_agents:
            return True

        return False

    def is_human_turn(self) -> bool:
        """Check if it's the human player's turn."""
        return self.active_agent == "human"


class CombatState(BaseModel):
    """State of the current combat encounter."""

    active: bool = Field(default=False, description="Whether combat is currently active")
    round: int = Field(default=0, description="Current round number (0 = not in combat)")
    turn_order: list[str] = Field(
        default_factory=list, description="Ordered list of combatant IDs by initiative"
    )
    current_turn_index: int = Field(default=0, description="Index into turn_order for current turn")
    combatants: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Combat-specific data for each combatant"
    )

    def get_current_combatant(self) -> str | None:
        """Get the ID of the combatant whose turn it is."""
        if not self.active or not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index % len(self.turn_order)]


class CharacterStats(BaseModel):
    """D&D 5e ability scores.

    Uses full names internally to avoid Python keyword conflicts,
    but accepts abbreviated names (str, int) when loading from JSON.
    """

    strength: int = Field(default=10, ge=1, le=30, alias="str")
    dexterity: int = Field(default=10, ge=1, le=30, alias="dex")
    constitution: int = Field(default=10, ge=1, le=30, alias="con")
    intelligence: int = Field(default=10, ge=1, le=30, alias="int")
    wisdom: int = Field(default=10, ge=1, le=30, alias="wis")
    charisma: int = Field(default=10, ge=1, le=30, alias="cha")

    model_config = {"populate_by_name": True}

    def get_modifier(self, stat: str) -> int:
        """Calculate ability modifier for a stat.

        Args:
            stat: Stat name (str/strength, dex/dexterity, etc.)
        """
        # Map abbreviations to full names
        stat_map = {
            "str": "strength",
            "dex": "dexterity",
            "con": "constitution",
            "int": "intelligence",
            "wis": "wisdom",
            "cha": "charisma",
        }
        full_name = stat_map.get(stat, stat)
        value = getattr(self, full_name, 10)
        return (value - 10) // 2


class CharacterState(BaseModel):
    """State of a player character (human or AI)."""

    name: str = Field(description="Character's display name")
    character_class: str = Field(description="D&D class (Fighter, Rogue, Cleric, etc.)")
    race: str = Field(default="Human", description="Character race")
    background: str = Field(default="", description="Character background")
    level: int = Field(default=1, ge=1, le=20)
    hp: int = Field(description="Current hit points")
    max_hp: int = Field(description="Maximum hit points")
    ac: int = Field(description="Armor class")
    stats: CharacterStats = Field(default_factory=CharacterStats)
    proficiency_bonus: int = Field(default=2, description="Proficiency bonus based on level")
    saving_throws: list[str] = Field(
        default_factory=list, description="Stats the character is proficient in for saves"
    )
    skills: list[str] = Field(default_factory=list, description="Skills the character is proficient in")
    conditions: list[str] = Field(default_factory=list, description="Active conditions (poisoned, etc.)")
    inventory: list[str] = Field(default_factory=list, description="Items carried")
    features: list[str] = Field(default_factory=list, description="Class features and abilities")
    racial_traits: list[str] = Field(default_factory=list, description="Racial abilities")
    spell_slots: dict[str, int] = Field(default_factory=dict, description="Available spell slots by level")
    spells_known: dict[str, list[str]] = Field(
        default_factory=dict, description="Known spells by category"
    )

    @property
    def is_alive(self) -> bool:
        """Check if character is alive (HP > 0)."""
        return self.hp > 0

    @property
    def is_unconscious(self) -> bool:
        """Check if character is unconscious (HP = 0 but not dead)."""
        return self.hp == 0


class NPCState(BaseModel):
    """State of a non-player character."""

    name: str = Field(description="NPC's display name")
    state: str = Field(
        default="alive", description="Current state: alive, dead, captured, freed, unknown"
    )
    location: str = Field(default="unknown", description="Current location")
    disposition: str = Field(
        default="neutral", description="Attitude toward party: friendly, hostile, neutral"
    )
    notes: str = Field(default="", description="Additional notes about this NPC")


class EnemyState(BaseModel):
    """State of an enemy combatant."""

    name: str = Field(default="Enemy", description="Enemy's display name")
    hp: int = Field(description="Current hit points")
    max_hp: int = Field(description="Maximum hit points")
    ac: int = Field(description="Armor class")
    state: str = Field(default="alive", description="Current state: alive, dead, fled")
    damage_immunities: list[str] = Field(default_factory=list)
    damage_resistances: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)
    notes: str = Field(default="", description="Additional notes")

    @property
    def is_alive(self) -> bool:
        """Check if enemy is alive and in combat."""
        return self.state == "alive" and self.hp > 0


class NarrativeProgress(BaseModel):
    """Tracks story progression flags."""

    # Chapter 1: Goblin Arrows
    wagon_discovered: bool = Field(default=False)
    horses_found_dead: bool = Field(default=False)
    ambush_triggered: bool = Field(default=False)
    goblins_defeated: bool = Field(default=False)
    goblin_trail_found: bool = Field(default=False)
    hideout_entered: bool = Field(default=False)
    sildar_rescued: bool = Field(default=False)
    klarg_defeated: bool = Field(default=False)

    # Generic flags for custom progress
    custom_flags: dict[str, bool] = Field(default_factory=dict)

    def set_flag(self, flag: str, value: bool = True) -> None:
        """Set a progress flag by name."""
        if hasattr(self, flag):
            setattr(self, flag, value)
        else:
            self.custom_flags[flag] = value

    def get_flag(self, flag: str) -> bool:
        """Get a progress flag by name."""
        if hasattr(self, flag) and flag != "custom_flags":
            return getattr(self, flag)
        return self.custom_flags.get(flag, False)


class WorldState(BaseModel):
    """Complete world state for the campaign.

    This is the single source of truth for all game data.
    It is serialized to JSON for persistence between sessions.
    """

    game_id: str = Field(default="lost-mines-001", description="Unique game identifier")
    current_chapter: int = Field(default=1, ge=1, description="Current chapter number")
    current_scene: str = Field(default="intro", description="Current scene identifier")
    narrative_progress: NarrativeProgress = Field(default_factory=NarrativeProgress)
    combat: CombatState = Field(default_factory=CombatState)
    turn_state: TurnState = Field(
        default_factory=TurnState,
        description="Controls which agent should respond to messages",
    )
    characters: dict[str, CharacterState] = Field(
        default_factory=dict, description="Player characters by ID"
    )
    npcs: dict[str, NPCState] = Field(default_factory=dict, description="NPCs by ID")
    enemies: dict[str, EnemyState] = Field(
        default_factory=dict, description="Current enemies by ID"
    )
    session_notes: list[str] = Field(
        default_factory=list, description="Notes from the current session"
    )
