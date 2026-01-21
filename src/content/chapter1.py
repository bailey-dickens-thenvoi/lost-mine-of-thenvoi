"""Chapter 1: Goblin Arrows - Lost Mines of Phandelver.

This module defines the scenes, encounters, and narrative content for
Chapter 1 of the campaign, including:
- The road to Phandalin (intro)
- Goblin ambush encounter
- Post-ambush exploration
- (Stretch) Cragmaw Hideout dungeon

Each scene has description text, available triggers, and state transitions.
"""

from __future__ import annotations

from typing import Any


# Scene definitions for Chapter 1
SCENES: dict[str, dict[str, Any]] = {
    "intro": {
        "name": "The Road to Phandalin",
        "chapter": 1,
        "description": """The party has been traveling for about half a day along the High Road south from Neverwinter before turning east onto the Triboar Trail. The wagon of mining supplies rattles along the rutted path, wheels creaking with each bump.

Around midday, the trail bends around a thicket of dense trees. As you round the corner, you spot something alarming ahead: two dead horses sprawled across the road, their bodies blocking the way forward. Black-feathered arrows protrude from their flanks, and flies buzz lazily around the carcasses.

The horses look like they've been dead for about a day. The empty saddlebags have been torn open and looted.""",
        "dm_notes": """This is the opening scene. Let the party investigate before triggering combat.

KEY INFORMATION:
- These are Gundren and Sildar's horses
- Goblins are hiding in the woods, waiting to ambush
- If party is cautious (Perception DC 10), they spot the goblins
- If party charges in, goblins get surprise round

SKILL CHECK OPTIONS:
- Investigation DC 10: Recognize the horses as those Gundren described
- Perception DC 10: Notice movement in the underbrush (goblins hiding)
- Survival DC 10: Notice the trail leading into the forest

TRIGGER AMBUSH when:
- Party approaches horses without checking for danger
- Party spends too long investigating (3+ rounds)
- Player explicitly says they're moving forward""",
        "triggers": {
            "investigate_horses": {
                "skill": "investigation",
                "dc": 10,
                "success_text": "You recognize these horses - they match the description Gundren gave of his and Sildar's mounts. Whatever happened here, it happened to your employers.",
                "fail_text": "The horses are clearly dead, killed by arrows, but you can't determine much more than that.",
            },
            "search_area": {
                "skill": "perception",
                "dc": 10,
                "success_text": "You notice subtle movement in the underbrush about 30 feet off the road. Something - or several somethings - are hiding in the forest on both sides of the trail.",
                "fail_text": "The forest seems quiet. Perhaps too quiet...",
            },
            "find_trail": {
                "skill": "survival",
                "dc": 10,
                "success_text": "You spot a trail leading north into the forest - a mix of goblin footprints and drag marks, as if something heavy was hauled this way.",
                "fail_text": "The ground is too disturbed by the ambush to make out any clear trail.",
            },
        },
        "combat_trigger": "goblin_ambush",
        "next_scene": "goblin_ambush",
    },

    "goblin_ambush": {
        "name": "Goblin Ambush!",
        "chapter": 1,
        "description": """Arrows whistle from the treeline! Cackling voices cry out in Goblin as four small, ugly humanoids burst from the underbrush, scimitars raised!

The goblins wear crude leather armor and have yellowish-green skin. Their eyes gleam with malicious cunning as they attack!

=== COMBAT INITIATED ===""",
        "dm_notes": """GOBLIN TACTICS:
1. Start with surprise round if party didn't spot them (Perception DC 10)
2. Goblins use shortbows from 30ft if possible
3. Switch to scimitars if enemies close to melee
4. ONE goblin flees toward the hideout when 2+ goblins are killed
   - This gives the party a way to follow them
5. Remaining goblins fight to the death

ENEMY POSITIONS:
- goblin_1 and goblin_2: North side of road (30ft)
- goblin_3 and goblin_4: South side of road (30ft)

INITIATIVE: Roll for all goblins and party members
GOBLIN INITIATIVE MODIFIER: +2 (DEX)

GOBLIN ATTACKS:
- Scimitar: +4 to hit, 1d6+2 slashing
- Shortbow: +4 to hit, 1d6+2 piercing, range 80/320

On VICTORY: Transition to 'after_ambush'
On DEFEAT: Party is captured (not killed) - goblins take them to hideout""",
        "combat": True,
        "enemies": ["goblin_1", "goblin_2", "goblin_3", "goblin_4"],
        "enemy_type": "goblin",
        "goblin_tactics": "Use shortbows from range. One flees when 2+ goblins fall, heading toward the hideout. Others fight to the death.",
        "surprise_condition": "Party didn't pass Perception DC 10 in intro scene",
        "victory_scene": "after_ambush",
        "defeat_scene": "party_captured",
        "progress_flags": ["ambush_triggered"],
    },

    "after_ambush": {
        "name": "After the Ambush",
        "chapter": 1,
        "description": """The last goblin falls, and silence returns to the forest - broken only by the chirping of birds and the rustle of leaves.

The goblin bodies carry little of value: a few copper pieces, crude weapons, and... you notice one of them has a leather pouch containing a small amount of gold (15 gp total) and what appears to be a crude map drawn on bark.

Looking around, you can see the underbrush is trampled in one direction - a clear trail leading north into the forest. The drag marks you noticed earlier head in the same direction.""",
        "dm_notes": """EXPLORATION OPTIONS:
1. Search bodies (Investigation DC 12):
   - Find crude map showing goblin hideout location
   - Find 15 gp total on the goblins
   - Find a human-made leather pouch (belonged to Sildar)

2. Find trail (Survival DC 10):
   - Trail leads to Cragmaw Hideout
   - About 5 miles through forest
   - Takes ~2 hours to follow carefully

3. Return to wagon:
   - Wagon is undamaged
   - Can leave it hidden or take it to Phandalin

NARRATIVE FLAGS TO SET:
- goblins_defeated: true
- goblin_trail_found: if they pass Survival check

NEXT STEPS:
- If they follow trail: 'goblin_trail' scene
- If they go to Phandalin first: 'phandalin' scene (stretch)""",
        "triggers": {
            "search_bodies": {
                "skill": "investigation",
                "dc": 12,
                "success_text": "Among the goblin belongings, you find a crude map scratched on bark showing a cave entrance with goblin drawings. One goblin has a leather pouch that looks human-made - inside is 15 gold pieces. This pouch likely belonged to one of the ambush victims.",
                "fail_text": "You find a few copper pieces and crude weapons, nothing of particular interest.",
            },
            "find_trail": {
                "skill": "survival",
                "dc": 10,
                "success_text": "The trail is easy to follow now - goblin footprints and drag marks lead north into the forest. Someone, or something, was dragged this way. The trail looks like it's been used regularly.",
                "fail_text": "The forest floor is disturbed, but you can't quite make out a clear path.",
            },
            "check_wagon": {
                "skill": None,  # No check needed
                "dc": 0,
                "success_text": "The wagon is intact and undamaged. Whatever the goblins wanted, it wasn't the mining supplies.",
                "fail_text": None,
            },
        },
        "progress_flags": ["goblins_defeated"],
        "next_scene": "goblin_trail",
    },

    "goblin_trail": {
        "name": "Following the Trail",
        "chapter": 1,
        "description": """The trail winds through dense forest, following a stream that trickles through the underbrush. After about two hours of careful travel, the trees begin to thin and you spot a large cave entrance in a hillside ahead.

A stream flows out of the cave mouth, which is about 15 feet wide and 10 feet high. Dense undergrowth conceals the area, but you can make out what appears to be a well-worn path leading inside.

As you watch, you notice two goblins stationed near the cave entrance, poorly hidden behind some bushes. They seem bored and inattentive.""",
        "dm_notes": """CRAGMAW HIDEOUT ENTRANCE

GOBLIN SENTRIES:
- 2 goblins hiding (poorly) in bushes
- Passive Perception 9 - easy to surprise
- If alerted, one runs inside to warn others

APPROACH OPTIONS:
1. Stealth approach (Stealth DC 9 to surprise)
2. Distraction (various creative options)
3. Direct assault (sentries get 1 round to react)

NEXT: Combat with sentries, then 'hideout_entrance' scene""",
        "triggers": {
            "stealth_approach": {
                "skill": "stealth",
                "dc": 9,
                "success_text": "You move silently through the underbrush, getting within striking distance of the goblin sentries without being noticed.",
                "fail_text": "A twig snaps underfoot! The goblins' heads whip toward the sound.",
            },
            "scout_ahead": {
                "skill": "perception",
                "dc": 12,
                "success_text": "You spot additional details: the cave entrance has a small pool of water just inside, and you can hear the distant sound of wolves howling from within.",
                "fail_text": "You can't make out much more detail from this distance.",
            },
        },
        "combat_trigger": "hideout_sentries",
        "progress_flags": ["goblin_trail_found"],
        "next_scene": "hideout_entrance",
    },

    "hideout_entrance": {
        "name": "Cragmaw Hideout - Entrance",
        "chapter": 1,
        "description": """With the sentries dealt with, you stand at the mouth of the goblin hideout. The stream emerges from a dark opening in the hillside, flowing past your feet. The air smells of damp stone and something unpleasant - a mix of wet fur and rotting meat.

The cave mouth is about 15 feet wide and 10 feet high. Just inside, you can see the stream flowing through a larger cavern. The sound of growling echoes from somewhere deeper within - wolves, by the sound of it.

To the right of the stream, a rough passage leads deeper into the hill.""",
        "dm_notes": """HIDEOUT LAYOUT:
1. Entrance cave (you are here)
2. Wolf kennel (3 wolves tied up)
3. Steep passage up to Klarg's chamber
4. Bridge over the stream
5. Klarg's chamber (boss fight)
6. Side chamber (Sildar held here)

WOLF KENNEL:
- 3 wolves chained, AC 13, HP 11 each
- Attack: Bite +4 (2d4+2 piercing)
- If released, they attack nearest creature
- Goblins can release them as an action

DECISIONS:
- Go right: Wolf kennel
- Follow stream: Bridge area
- Climb: Steep passage to upper area""",
        "progress_flags": ["hideout_entered"],
        "next_scene": "wolf_kennel",
    },

    "klarg_chamber": {
        "name": "Klarg's Chamber",
        "chapter": 1,
        "description": """The passage opens into a larger chamber, roughly 30 feet square. Supplies are piled in one corner - crates, barrels, and stolen goods. A large fire pit dominates the center of the room, its smoke rising through a natural chimney.

A massive bugbear stands by the fire, easily 7 feet tall with coarse brown fur and a toothy grin. A wolf - larger than normal - lounges at his feet. Two goblins attend him, one fanning him with a crude fan while the other sorts through stolen items.

\"Who dares enter Klarg's domain?\" the bugbear bellows, reaching for a heavy morningstar.""",
        "dm_notes": """BOSS FIGHT: KLARG

KLARG (Bugbear):
- AC 16, HP 27
- Attack: Morningstar +4 (2d8+2 bludgeoning)
- Surprise Attack: +2d6 damage if target surprised

RIPPER (Klarg's Wolf):
- AC 13, HP 11
- Attack: Bite +4 (2d4+2 piercing)
- Pack Tactics: Advantage if ally within 5ft of target

2 GOBLINS (as normal)

KLARG'S TACTICS:
1. Opens with surprise attack if possible
2. Targets the most threatening-looking party member
3. Orders goblins to protect him
4. Fights to the death (too proud to flee)

NEGOTIATION OPTION:
- Klarg can be bribed (Persuasion DC 15)
- Or intimidated (Intimidation DC 15)
- Yeemik (goblin second-in-command) wants Klarg dead and will help party if asked

VICTORY:
- Sildar can be found in side chamber
- Stolen supplies include 2 healing potions
- Progress flag: klarg_defeated""",
        "combat": True,
        "enemies": ["klarg", "ripper", "goblin_5", "goblin_6"],
        "victory_scene": "sildar_rescue",
        "progress_flags": [],
    },

    "sildar_rescue": {
        "name": "Sildar Rescued",
        "chapter": 1,
        "description": """With Klarg defeated, you hear a weak voice from a side chamber: \"Hello? Is someone there? Please... I need help.\"

Following the voice, you find a human man in his fifties, bound and bruised but alive. He wears the tattered remains of fine clothes, and despite his condition, carries himself with dignity.

\"Thank the gods,\" he breathes. \"I am Sildar Hallwinter of the Lords' Alliance. Those goblins... they took me and my companion Gundren. But Gundren was taken somewhere else - to 'Cragmaw Castle,' I heard them say. Something about the 'Black Spider' wanting him.\"

He looks at you with desperate hope. \"Can you help me? Can you help find Gundren?\"""",
        "dm_notes": """SILDAR HALLWINTER RESCUED

SILDAR'S INFORMATION:
1. He and Gundren were ambushed on the road
2. Gundren was taken to Cragmaw Castle (location unknown)
3. Someone called 'the Black Spider' ordered the kidnapping
4. Gundren has a map to Wave Echo Cave
5. Sildar was kept alive for ransom

SILDAR'S REQUEST:
- Help him get to Phandalin
- Help find Gundren
- He will pay 50 gp for escort to Phandalin
- He can provide information about Phandalin

PROGRESS FLAGS:
- sildar_rescued: true

CHAPTER 1 COMPLETE when:
- goblins_defeated
- sildar_rescued OR klarg_defeated

LEADS TO CHAPTER 2:
- Deliver wagon to Phandalin
- Investigate Cragmaw Castle
- Learn about the Black Spider""",
        "progress_flags": ["sildar_rescued"],
        "chapter_end": True,
        "next_chapter": 2,
    },

    "party_captured": {
        "name": "Captured!",
        "chapter": 1,
        "description": """Darkness closes in as the last of your party falls. The goblins cackle with glee, binding your unconscious forms with rough rope.

You awaken sometime later in a dark cave, stripped of your weapons and equipment. The sounds of goblin voices echo from somewhere nearby, along with... the sound of a man groaning in pain.

You're not alone in this prison, it seems. And you're still alive. The goblins must have plans for you...""",
        "dm_notes": """PARTY DEFEATED - NOT A GAME OVER

The goblins don't kill the party - they're worth more alive as prisoners or slaves.

SITUATION:
- Party is in Cragmaw Hideout, prisoner area
- Stripped of weapons and equipment (nearby)
- Sildar is in the same chamber
- Can attempt escape

ESCAPE OPTIONS:
1. Untie bonds (Dexterity DC 12)
2. Distract guards (various methods)
3. Sildar helps if they're kind to him

This gives party a second chance and introduces Sildar earlier.""",
        "progress_flags": ["party_captured"],
        "alternate_path": True,
    },
}


# Enemy definitions for Chapter 1 encounters
CHAPTER1_ENEMIES: dict[str, dict[str, Any]] = {
    "goblin": {
        "name": "Goblin",
        "type": "goblin",
        "hp": 7,
        "max_hp": 7,
        "ac": 15,
        "attack_bonus": 4,
        "damage": "1d6+2",
        "damage_type": "slashing",
        "attacks": [
            {"name": "Scimitar", "bonus": 4, "damage": "1d6+2", "type": "slashing"},
            {"name": "Shortbow", "bonus": 4, "damage": "1d6+2", "type": "piercing", "range": "80/320"},
        ],
        "skills": {"stealth": 6},
        "special": "Nimble Escape: Disengage or Hide as bonus action",
    },
    "wolf": {
        "name": "Wolf",
        "type": "wolf",
        "hp": 11,
        "max_hp": 11,
        "ac": 13,
        "attack_bonus": 4,
        "damage": "2d4+2",
        "damage_type": "piercing",
        "attacks": [
            {"name": "Bite", "bonus": 4, "damage": "2d4+2", "type": "piercing"},
        ],
        "special": "Pack Tactics: Advantage if ally within 5ft of target",
    },
    "klarg": {
        "name": "Klarg",
        "type": "bugbear",
        "hp": 27,
        "max_hp": 27,
        "ac": 16,
        "attack_bonus": 4,
        "damage": "2d8+2",
        "damage_type": "bludgeoning",
        "attacks": [
            {"name": "Morningstar", "bonus": 4, "damage": "2d8+2", "type": "bludgeoning"},
            {"name": "Javelin", "bonus": 2, "damage": "1d6+2", "type": "piercing", "range": "30/120"},
        ],
        "special": "Surprise Attack: +2d6 damage on first hit against surprised target",
    },
}


def get_scene(scene_id: str) -> dict[str, Any] | None:
    """Get a scene definition by ID.

    Args:
        scene_id: The scene identifier

    Returns:
        Scene definition dict or None if not found
    """
    return SCENES.get(scene_id)


def get_scene_description(scene_id: str) -> str:
    """Get just the description text for a scene.

    Args:
        scene_id: The scene identifier

    Returns:
        Scene description or empty string if not found
    """
    scene = SCENES.get(scene_id)
    if scene:
        return scene.get("description", "")
    return ""


def get_scene_dm_notes(scene_id: str) -> str:
    """Get the DM notes for a scene.

    Args:
        scene_id: The scene identifier

    Returns:
        DM notes or empty string if not found
    """
    scene = SCENES.get(scene_id)
    if scene:
        return scene.get("dm_notes", "")
    return ""


def get_scene_triggers(scene_id: str) -> dict[str, dict[str, Any]]:
    """Get available triggers for a scene.

    Args:
        scene_id: The scene identifier

    Returns:
        Dict of trigger definitions
    """
    scene = SCENES.get(scene_id)
    if scene:
        return scene.get("triggers", {})
    return {}


def get_enemy_stats(enemy_type: str) -> dict[str, Any] | None:
    """Get enemy stats by type.

    Args:
        enemy_type: The enemy type (e.g., 'goblin', 'klarg')

    Returns:
        Enemy stats dict or None if not found
    """
    return CHAPTER1_ENEMIES.get(enemy_type)


def format_scene_context(scene_id: str, include_dm_notes: bool = True) -> str:
    """Format complete scene context for the DM.

    Args:
        scene_id: The scene identifier
        include_dm_notes: Whether to include DM notes

    Returns:
        Formatted scene context string
    """
    scene = SCENES.get(scene_id)
    if not scene:
        return f"Scene not found: {scene_id}"

    lines = [
        f"## Scene: {scene['name']}",
        f"Chapter: {scene.get('chapter', 1)}",
        "",
        "### Description (read to players)",
        scene.get("description", ""),
        "",
    ]

    # Add triggers
    triggers = scene.get("triggers", {})
    if triggers:
        lines.append("### Available Skill Checks")
        for trigger_name, trigger in triggers.items():
            if trigger.get("skill"):
                lines.append(f"- {trigger_name}: {trigger['skill'].upper()} DC {trigger['dc']}")
        lines.append("")

    # Add combat info
    if scene.get("combat"):
        lines.append("### Combat Encounter")
        lines.append(f"Enemies: {', '.join(scene.get('enemies', []))}")
        if scene.get("goblin_tactics"):
            lines.append(f"Tactics: {scene['goblin_tactics']}")
        lines.append("")

    # Add DM notes
    if include_dm_notes and scene.get("dm_notes"):
        lines.append("### DM Notes")
        lines.append(scene["dm_notes"])
        lines.append("")

    return "\n".join(lines)
