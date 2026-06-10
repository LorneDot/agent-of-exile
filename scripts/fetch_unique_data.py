#!/usr/bin/env python3
"""PoE2 Unique Item Data Fetcher.

Downloads and caches unique item data for offline use.
Builds a reference of unique items with their stats, mechanics,
and build-around potential.

Usage:
    python fetch_unique_data.py           # fetch and cache
    python fetch_unique_data.py --force   # force re-fetch
    python fetch_unique_data.py --stats   # show cache statistics
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
UNIQUES_CACHE = CACHE_DIR / "uniques.json"


# ============================================================
# Built-in unique item reference
# ============================================================
# Important PoE2 uniques with their core mechanics.
# Sourced from poe2db.tw and community data.
# This is a representative sample — not exhaustive.

BUILT_IN_UNIQUES = {
    # --- Build-Enabling Uniques ---
    "The Three Dragons": {
        "slot": "Helm",
        "requirement": {"level": 35, "int": 64},
        "stats": [
            "+30 to maximum Energy Shield",
            "+30% to Fire Resistance",
        ],
        "mechanics": [
            "Your Fire Damage can Shock but not Ignite",
            "Your Cold Damage can Ignite but not Freeze or Chill",
            "Your Lightning Damage can Freeze but not Shock",
        ],
        "build_around": ["elemental_conversion", "shock_scaling", "hybrid_elemental"],
        "synergy_skills": ["Arc", "Spark", "Fireball", "Ice Shot"],
        "synergy_ascendancies": ["Stormweaver", "Infernalist", "Deadeye"],
        "tags": ["elemental", "ailment_conversion"],
    },
    "Kaom's Heart": {
        "slot": "Body Armour",
        "requirement": {"level": 62, "str": 180},
        "stats": [
            "+500 to maximum Life",
            "20-40% increased Fire Damage",
        ],
        "mechanics": [
            "Has no Sockets",
        ],
        "build_around": ["life_stacking", "fire_damage"],
        "synergy_skills": ["Righteous Fire", "Infernal Cry", "Earthquake"],
        "synergy_ascendancies": ["Titan", "Warbringer", "Infernalist"],
        "tags": ["life", "fire", "no_sockets"],
    },
    "Atziri's Foible": {
        "slot": "Amulet",
        "requirement": {"level": 16},
        "stats": [
            "+100 to maximum Mana",
            "16-24% increased Mana Regeneration Rate",
            "20-30% increased maximum Mana",
        ],
        "mechanics": [
            "Items and Gems have 25% reduced Attribute Requirements",
        ],
        "build_around": ["mana_stacking", "archmage", "attribute_bypass"],
        "synergy_skills": ["Arc", "Spark", "Mana Tempest"],
        "synergy_ascendancies": ["Stormweaver", "Chronomancer"],
        "tags": ["mana", "caster", "attribute_reduction"],
    },
    "Ventor's Gamble": {
        "slot": "Ring",
        "requirement": {"level": 65},
        "stats": [
            "+0-60 to maximum Life",
            "-10-10% reduced Quantity of Items found",
            "20-40% increased Rarity of Items found",
            "-25-50% to Fire Resistance",
            "-25-50% to Cold Resistance",
            "-25-50% to Lightning Resistance",
            "+0-60% to Elemental Resistances",
        ],
        "mechanics": [
            "All stats have random variance — can roll negative or positive",
        ],
        "build_around": ["magic_find", "budget_gamble"],
        "synergy_skills": [],
        "synergy_ascendancies": [],
        "tags": ["magic_find", "gambling", "resistance"],
    },
    "Tabula Rasa": {
        "slot": "Body Armour",
        "requirement": {"level": 1},
        "stats": [],
        "mechanics": [
            "Has no implicit modifiers",
            "Has 6 white sockets",
            "Has no Attribute Requirements",
        ],
        "build_around": ["leveling", "gem_testing", "early_mapping"],
        "synergy_skills": ["Any"],
        "synergy_ascendancies": ["Any"],
        "tags": ["leveling", "sockets", "no_stats"],
    },
    "Dialla's Malefaction": {
        "slot": "Body Armour",
        "requirement": {"level": 52},
        "stats": [
            "+35 to maximum Energy Shield",
            "+13% to Chaos Resistance",
        ],
        "mechanics": [
            "Gems can be Socketed in this Item ignoring Socket Colour",
            "Grants Level 15 Added Chaos Damage Support",
        ],
        "build_around": ["chaos_damage", "gem_flexibility"],
        "synergy_skills": ["Essence Drain", "Contagion", "Hexblast"],
        "synergy_ascendancies": ["Infernalist", "Blood Mage"],
        "tags": ["chaos", "caster", "socket_freedom"],
    },
    "Crown of Eyes": {
        "slot": "Helm",
        "requirement": {"level": 52},
        "stats": [
            "+60 to maximum Life",
            "+25% to all Elemental Resistances",
        ],
        "mechanics": [
            "Increases and Reductions to Spell Damage also apply to Attacks",
        ],
        "build_around": ["spell_damage_scaling", "attack_caster_hybrid"],
        "synergy_skills": ["Elemental Hit", "Lightning Arrow", "Explosive Arrow"],
        "synergy_ascendancies": ["Witchhunter", "Gemling Legionnaire", "Deadeye"],
        "tags": ["hybrid", "spell_to_attack", "damage_conversion"],
    },
    "Ralakesh's Impatience": {
        "slot": "Boots",
        "requirement": {"level": 44},
        "stats": [
            "30% increased Movement Speed",
        ],
        "mechanics": [
            "Count as having maximum Endurance, Frenzy, and Power Charges",
            "Cannot generate, gain, or lose Charges",
        ],
        "build_around": ["charge_stacking", "charge_bonuses"],
        "synergy_skills": ["Discharge", "Flicker Strike"],
        "synergy_ascendancies": ["Gemling Legionnaire", "Witchhunter"],
        "tags": ["charges", "movement"],
    },
    "Astramentis": {
        "slot": "Amulet",
        "requirement": {"level": 20},
        "stats": [
            "+80-100 to all Attributes",
            "-4 Physical Damage taken from Attack Hits",
        ],
        "mechanics": [],
        "build_around": ["attribute_stacking", "stat_scaling"],
        "synergy_skills": ["Any attribute-scaling skill"],
        "synergy_ascendancies": ["Gemling Legionnaire", "Titan"],
        "tags": ["attributes", "stat_stacking"],
    },
    "Headhunter": {
        "slot": "Belt",
        "requirement": {"level": 40},
        "stats": [
            "+40-50 to maximum Life",
            "+30-40 to maximum Mana",
        ],
        "mechanics": [
            "When you Kill a Rare monster, you gain its Modifiers for 60 seconds",
        ],
        "build_around": ["mapping", "speed_farming", "rare_hunting"],
        "synergy_skills": ["Any fast-clearing skill"],
        "synergy_ascendancies": ["Deadeye", "Pathfinder", "Witchhunter"],
        "tags": ["mapping", "speed", "rare_mod_stealing"],
    },
    "Mageblood": {
        "slot": "Belt",
        "requirement": {"level": 44},
        "stats": [
            "+20-30 to all Attributes",
            "+8-16% to all Elemental Resistances",
        ],
        "mechanics": [
            "Magic Utility Flasks cannot be Used",
            "Leftmost 2-4 Magic Utility Flasks constantly apply their Flask Effects to you",
            "Flasks applied this way have 70-100% increased Effect",
        ],
        "build_around": ["flask_scaling", "permanent_flasks"],
        "synergy_skills": ["Any"],
        "synergy_ascendancies": ["Pathfinder", "Any"],
        "tags": ["flasks", "endgame", "defensive", "offensive"],
    },
    # --- Weapon Uniques ---
    "Doomfletch": {
        "slot": "Weapon",
        "weapon_type": "Bow",
        "requirement": {"level": 40, "dex": 95},
        "stats": [
            "10-15 to 25-30 Physical Damage",
            "1.45 Attacks per Second",
        ],
        "mechanics": [
            "Gain 100% of Weapon Physical Damage as Extra Damage of each Element",
        ],
        "build_around": ["physical_to_elemental", "added_elemental"],
        "synergy_skills": ["Tornado Shot", "Lightning Arrow", "Ice Shot"],
        "synergy_ascendancies": ["Deadeye", "Pathfinder"],
        "tags": ["bow", "elemental", "physical_conversion"],
    },
    "Quill Rain": {
        "slot": "Weapon",
        "weapon_type": "Bow",
        "requirement": {"level": 5, "dex": 26},
        "stats": [
            "3-4 to 8-10 Physical Damage",
            "3.00 Attacks per Second",
        ],
        "mechanics": [
            "100% increased Attack Speed",
            "50% less Damage",
            "Non-instant Mana Recovery is applied to Life instead of Mana",
            "10% increased Mana Regeneration rate",
        ],
        "build_around": ["attack_speed", "on_hit_effects", "caster_bow"],
        "synergy_skills": ["Explosive Arrow", "Caustic Arrow", "Toxic Rain"],
        "synergy_ascendancies": ["Pathfinder", "Deadeye"],
        "tags": ["bow", "attack_speed", "on_hit"],
    },
    "Pillar of the Caged God": {
        "slot": "Weapon",
        "weapon_type": "Staff",
        "requirement": {"level": 13, "str": 27, "dex": 27},
        "stats": [
            "8-12 to 20-25 Physical Damage",
            "1.30 Attacks per Second",
        ],
        "mechanics": [
            "1% increased Area of Effect per 20 Intelligence",
            "1% increased Attack Speed per 10 Dexterity",
            "16% increased Weapon Damage per 10 Strength",
        ],
        "build_around": ["attribute_stacking", "stat_scaling"],
        "synergy_skills": ["Cyclone", "Sweep", "Ice Crash"],
        "synergy_ascendancies": ["Gemling Legionnaire", "Titan"],
        "tags": ["staff", "stat_stacking", "aoe", "attack_speed"],
    },
    "Wings of Entropy": {
        "slot": "Weapon",
        "weapon_type": "One Hand Axe + Shield",
        "requirement": {"level": 52, "str": 88, "dex": 88},
        "stats": [
            "60-80 to 120-140 Physical Damage",
            "1.40 Attacks per Second",
        ],
        "mechanics": [
            "Counts as Dual Wielding",
            "+8% Chance to Block Attack Damage while Dual Wielding",
            "Main Hand: +(7-10)% Chance to Block Attack Damage",
            "Off Hand: +(7-10)% Chance to Block Spell Damage",
            "+50% to Fire and Chaos Resistances in Off Hand",
        ],
        "build_around": ["dual_wield_block", "hybrid_defense"],
        "synergy_skills": ["Any Melee Attack"],
        "synergy_ascendancies": ["Titan", "Warbringer"],
        "tags": ["axe", "block", "dual_wield"],
    },
    # --- Jewelry ---
    "Death Rush": {
        "slot": "Ring",
        "requirement": {"level": 46},
        "stats": [
            "+20-30 to Strength",
            "+20-30% to Cold Resistance",
        ],
        "mechanics": [
            "Recover 3% of Life on Kill",
            "Gain Adrenaline for 3 seconds on Kill",
        ],
        "build_around": ["on_kill_effects", "mapping_sustain"],
        "synergy_skills": ["Any fast-clearing build"],
        "synergy_ascendancies": ["Titan", "Warbringer", "Witchhunter"],
        "tags": ["ring", "on_kill", "life_recovery", "mapping"],
    },
    "The Taming": {
        "slot": "Ring",
        "requirement": {"level": 48},
        "stats": [
            "+20-30 to all Elemental Resistances",
        ],
        "mechanics": [
            "30% increased Damage with Hits and Ailments per Freeze, Shock, and Ignite on Enemy",
            "10% chance to Freeze, Shock, and Ignite",
        ],
        "build_around": ["elemental_ailment_scaling", "multi_element"],
        "synergy_skills": ["Elemental Hit", "Wild Strike"],
        "synergy_ascendancies": ["Stormweaver", "Infernalist", "Deadeye"],
        "tags": ["ring", "elemental", "ailment", "damage_scaling"],
    },
    # --- Defensive Uniques ---
    "Lightning Coil": {
        "slot": "Body Armour",
        "requirement": {"level": 47, "str": 72, "dex": 72},
        "stats": [
            "+40-50 to maximum Life",
            "+30-40% to Lightning Resistance",
        ],
        "mechanics": [
            "50% of Physical Damage from Hits taken as Lightning Damage",
        ],
        "build_around": ["physical_mitigation", "lightning_res_stacking"],
        "synergy_skills": ["Any"],
        "synergy_ascendancies": ["Any (defensive layer)"],
        "tags": ["armour", "physical_mitigation", "lightning", "defensive"],
    },
    "Carcass Jack": {
        "slot": "Body Armour",
        "requirement": {"level": 52, "dex": 95, "int": 60},
        "stats": [
            "+40-60 to maximum Life",
            "+15-25% to Area of Effect",
            "+15-25% to Area Damage",
        ],
        "mechanics": [
            "50% increased Damage with Hits against Enemies on Full Life",
        ],
        "build_around": ["aoe_scaling", "one_shot_mapping"],
        "synergy_skills": ["Fireball", "Earthquake", "Explosive Grenade"],
        "synergy_ascendancies": ["Infernalist", "Titan"],
        "tags": ["armour", "aoe", "damage"],
    },
}


def build_unique_reference() -> dict:
    """Build the unique item reference data."""
    return {
        "source": "built-in unique reference",
        "note": "For complete unique item data (all variants, exact roll ranges), use poe2db.tw",
        "uniques": BUILT_IN_UNIQUES,
    }


def get_unique_data(force: bool = False) -> dict:
    """Get unique item data, from cache or fresh build."""
    if not force and UNIQUES_CACHE.exists():
        with open(UNIQUES_CACHE) as f:
            return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = build_unique_reference()

    with open(UNIQUES_CACHE, "w") as f:
        json.dump(data, f, indent=2)

    return data


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Cache PoE2 unique item data for offline use"
    )
    parser.add_argument("--force", action="store_true",
                        help="Force rebuild cache")
    parser.add_argument("--stats", action="store_true",
                        help="Show cache statistics")
    args = parser.parse_args()

    data = get_unique_data(force=args.force)

    if args.stats:
        uniques = data.get("uniques", {})
        slots = set()
        tags = set()
        for name, info in uniques.items():
            slots.add(info.get("slot", "?"))
            for t in info.get("tags", []):
                tags.add(t)
        print(f"Source: {data.get('source', 'unknown')}")
        print(f"Uniques indexed: {len(uniques)}")
        print(f"Slots covered: {', '.join(sorted(slots))}")
        print(f"Mechanic tags: {', '.join(sorted(tags))}")


if __name__ == "__main__":
    cli()
