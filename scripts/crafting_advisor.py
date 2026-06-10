#!/usr/bin/env python3
"""PoE2 Crafting Advisor.

Advises on crafting strategy for specific gear slots, accounting for:
- Item base types and their implicits
- iLvl breakpoints for mod tiers
- Available prefix/affix pools per slot
- Socket crafting (rune sockets)
- Optimal crafting method for each goal

Sources:
  - poe2db.tw → Mods, Items, Crafting
  - GGG patch notes and in-game mechanics
  - Community-verified crafting data

Usage:
    python crafting_advisor.py --slot "Body Armour" --base "Expert Chain Mail"
    python crafting_advisor.py --slot "Weapon" --type "Crossbow" --desired-mods "flat_phys increased_phys attack_speed"
    python crafting_advisor.py --slot "Ring" --desired-mods "life fire_res cold_res lightning_res"
    python crafting_advisor.py --item "Two-Stone Ring" --ilvl 82 --goal "capped ele res + life"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
CRAFTING_CACHE = CACHE_DIR / "crafting-data.json"
MODS_CACHE = CACHE_DIR / "mods-data.json"


# ============================================================
# Item base data — sourced from poe2db.tw / in-game
# ============================================================

# Item bases by slot with their implicits and base requirements
ITEM_BASES: dict[str, list[dict]] = {
    "Body Armour": [
        {"name": "Chain Mail", "type": "Armour", "req_level": 1,
         "implicits": [], "base_armour": 45, "base_evasion": 0, "base_es": 0},
        {"name": "Plate Vest", "type": "Armour", "req_level": 10,
         "implicits": [], "base_armour": 72, "base_evasion": 0, "base_es": 0},
        {"name": "Scale Mail", "type": "Armour/Evasion", "req_level": 15,
         "implicits": [], "base_armour": 43, "base_evasion": 43, "base_es": 0},
        {"name": "Brigandine", "type": "Armour/Evasion", "req_level": 25,
         "implicits": [], "base_armour": 62, "base_evasion": 62, "base_es": 0},
        {"name": "Full Plate", "type": "Armour", "req_level": 32,
         "implicits": [], "base_armour": 98, "base_evasion": 0, "base_es": 0},
        {"name": "Vaal Raiment", "type": "Energy Shield", "req_level": 38,
         "implicits": [], "base_armour": 0, "base_evasion": 0, "base_es": 72},
        {"name": "Expert Chain Mail", "type": "Armour", "req_level": 45,
         "implicits": [], "base_armour": 120, "base_evasion": 0, "base_es": 0},
        {"name": "Expert Scale Mail", "type": "Armour/Evasion", "req_level": 50,
         "implicits": [], "base_armour": 80, "base_evasion": 80, "base_es": 0},
        {"name": "Expert Full Plate", "type": "Armour", "req_level": 55,
         "implicits": [], "base_armour": 160, "base_evasion": 0, "base_es": 0},
        {"name": "Advanced Vaal Raiment", "type": "Energy Shield", "req_level": 60,
         "implicits": [], "base_armour": 0, "base_evasion": 0, "base_es": 110},
        {"name": "Expert Brigandine", "type": "Armour/Evasion", "req_level": 62,
         "implicits": [], "base_armour": 100, "base_evasion": 100, "base_es": 0},
    ],
    "Helm": [
        {"name": "Iron Hat", "type": "Armour", "req_level": 1,
         "implicits": [], "base_armour": 10},
        {"name": "Soldier Helmet", "type": "Armour", "req_level": 20,
         "implicits": [], "base_armour": 22},
        {"name": "Great Helm", "type": "Armour", "req_level": 35,
         "implicits": [], "base_armour": 35},
        {"name": "Expert Soldier Helmet", "type": "Armour", "req_level": 50,
         "implicits": [], "base_armour": 48},
        {"name": "Expert Great Helm", "type": "Armour", "req_level": 60,
         "implicits": [], "base_armour": 62},
    ],
    "Gloves": [
        {"name": "Iron Gauntlets", "type": "Armour", "req_level": 1,
         "implicits": [], "base_armour": 8},
        {"name": "Plate Gauntlets", "type": "Armour", "req_level": 22,
         "implicits": [], "base_armour": 18},
        {"name": "Expert Plate Gauntlets", "type": "Armour", "req_level": 50,
         "implicits": [], "base_armour": 30},
    ],
    "Boots": [
        {"name": "Iron Greaves", "type": "Armour", "req_level": 1,
         "implicits": [], "base_armour": 8},
        {"name": "Plate Greaves", "type": "Armour", "req_level": 22,
         "implicits": [], "base_armour": 18},
        {"name": "Expert Plate Greaves", "type": "Armour", "req_level": 50,
         "implicits": [], "base_armour": 30},
    ],
    "Ring": [
        {"name": "Iron Ring", "implicits": ["Adds 1 to 4 Physical Damage to Attacks"],
         "req_level": 1},
        {"name": "Gold Ring", "implicits": ["6% increased Rarity of Items found"],
         "req_level": 8},
        {"name": "Sapphire Ring", "implicits": ["+20-30% to Cold Resistance"],
         "req_level": 8},
        {"name": "Topaz Ring", "implicits": ["+20-30% to Lightning Resistance"],
         "req_level": 8},
        {"name": "Ruby Ring", "implicits": ["+20-30% to Fire Resistance"],
         "req_level": 8},
        {"name": "Two-Stone Ring", "implicits": ["+12-16% to Fire and Cold Resistances"],
         "req_level": 20},
        {"name": "Amethyst Ring", "implicits": ["+7-13% to Chaos Resistance"],
         "req_level": 30},
        {"name": "Diamond Ring", "implicits": ["+10-20% Global Critical Strike Chance"],
         "req_level": 45},
    ],
    "Amulet": [
        {"name": "Paua Amulet", "implicits": ["20-30% increased Mana Regeneration Rate"],
         "req_level": 1},
        {"name": "Amber Amulet", "implicits": ["+10-20 to Strength"],
         "req_level": 5},
        {"name": "Jade Amulet", "implicits": ["+10-20 to Dexterity"],
         "req_level": 5},
        {"name": "Lapis Amulet", "implicits": ["+10-20 to Intelligence"],
         "req_level": 5},
        {"name": "Citrine Amulet", "implicits": ["+12-16 to Strength and Dexterity"],
         "req_level": 16},
        {"name": "Agate Amulet", "implicits": ["+12-16 to Strength and Intelligence"],
         "req_level": 16},
        {"name": "Turquoise Amulet", "implicits": ["+12-16 to Dexterity and Intelligence"],
         "req_level": 16},
        {"name": "Onyx Amulet", "implicits": ["+10-16 to all Attributes"],
         "req_level": 24},
    ],
    "Belt": [
        {"name": "Leather Belt", "implicits": ["+20-30 to maximum Life"],
         "req_level": 1},
        {"name": "Heavy Belt", "implicits": ["+15-25 to maximum Life"],
         "req_level": 12},
        {"name": "Chain Belt", "implicits": ["+12-20% increased Flask Charges gained"],
         "req_level": 24},
        {"name": "Stygian Vise", "implicits": ["Has 1 Abyssal Socket"],
         "req_level": 60},
    ],
    "Weapon": [],  # Handled by weapon-specific tables
}


# Weapon-specific item data
WEAPON_BASES: dict[str, list[dict]] = {
    "Crossbow": [
        {"name": "Makeshift Crossbow", "req_level": 1, "base_dmg_min": 12, "base_dmg_max": 35,
         "base_aps": 1.55, "implicits": []},
        {"name": "Siege Crossbow", "req_level": 20, "base_dmg_min": 24, "base_dmg_max": 72,
         "base_aps": 1.45, "implicits": []},
        {"name": "Advanced Siege Crossbow", "req_level": 45, "base_dmg_min": 38, "base_dmg_max": 115,
         "base_aps": 1.40, "implicits": []},
        {"name": "Expert Siege Crossbow", "req_level": 62, "base_dmg_min": 52, "base_dmg_max": 158,
         "base_aps": 1.40, "implicits": []},
    ],
    "Bow": [
        {"name": "Short Bow", "req_level": 1, "base_dmg_min": 10, "base_dmg_max": 28,
         "base_aps": 1.50, "implicits": []},
        {"name": "Long Bow", "req_level": 20, "base_dmg_min": 18, "base_dmg_max": 52,
         "base_aps": 1.40, "implicits": []},
        {"name": "Advanced Long Bow", "req_level": 45, "base_dmg_min": 30, "base_dmg_max": 84,
         "base_aps": 1.35, "implicits": []},
        {"name": "Expert Long Bow", "req_level": 62, "base_dmg_min": 44, "base_dmg_max": 120,
         "base_aps": 1.35, "implicits": []},
    ],
    "One Hand Mace": [
        {"name": "Club", "req_level": 1, "base_dmg_min": 8, "base_dmg_max": 22,
         "base_aps": 1.45, "implicits": []},
        {"name": "Morning Star", "req_level": 24, "base_dmg_min": 18, "base_dmg_max": 48,
         "base_aps": 1.35, "implicits": []},
        {"name": "Advanced Morning Star", "req_level": 48, "base_dmg_min": 28, "base_dmg_max": 72,
         "base_aps": 1.30, "implicits": []},
    ],
    "Staff": [
        {"name": "Wooden Staff", "req_level": 1, "base_dmg_min": 6, "base_dmg_max": 18,
         "base_aps": 1.30, "implicits": []},
        {"name": "Quarterstaff", "req_level": 20, "base_dmg_min": 14, "base_dmg_max": 40,
         "base_aps": 1.40, "implicits": []},
        {"name": "Advanced Quarterstaff", "req_level": 45, "base_dmg_min": 24, "base_dmg_max": 66,
         "base_aps": 1.35, "implicits": []},
        {"name": "Gothic Staff", "req_level": 38, "base_dmg_min": 18, "base_dmg_max": 54,
         "base_aps": 1.20, "implicits": ["+18% Chance to Block Attack Damage while wielding a Staff"]},
    ],
    "Shield": [
        {"name": "Buckler", "req_level": 1, "base_armour": 12, "base_block": 24,
         "implicits": []},
        {"name": "Tower Shield", "req_level": 25, "base_armour": 48, "base_block": 28,
         "implicits": ["3% additional Physical Damage Reduction"]},
        {"name": "Advanced Tower Shield", "req_level": 50, "base_armour": 80, "base_block": 30,
         "implicits": ["5% additional Physical Damage Reduction"]},
    ],
}


# ============================================================
# iLvl breakpoint data — mod tier thresholds
# ============================================================

# Mod tiers unlock at specific iLvl thresholds
# Source: poe2db.tw → Mods, community data mining
ILVL_BREAKPOINTS = {
    "life_flat": {1: (3, 9), 20: (10, 19), 40: (20, 29), 60: (30, 44), 75: (45, 59), 82: (60, 79), 85: (80, 100)},
    "life_percent": {20: (3, 5), 45: (4, 6), 68: (5, 8), 82: (7, 10)},
    "es_flat": {1: (3, 9), 20: (10, 19), 40: (20, 29), 60: (30, 44), 75: (45, 59)},
    "es_percent": {20: (3, 6), 45: (5, 8), 68: (6, 10)},
    "armour_flat": {1: (5, 14), 20: (15, 29), 40: (30, 49), 60: (50, 69), 75: (70, 99)},
    "armour_percent": {1: (4, 10), 30: (8, 16), 55: (12, 20), 75: (16, 28)},
    "evasion_flat": {1: (5, 14), 20: (15, 29), 40: (30, 49), 60: (50, 69), 75: (70, 99)},
    "evasion_percent": {1: (4, 10), 30: (8, 16), 55: (12, 20), 75: (16, 28)},
    "flat_phys": {1: (1, 2), 15: (3, 5), 30: (5, 8), 45: (8, 12), 60: (10, 15), 75: (13, 19), 82: (16, 24)},
    "increased_phys": {1: (20, 40), 20: (35, 55), 40: (50, 75), 60: (65, 94), 75: (80, 109), 82: (100, 129)},
    "attack_speed": {1: (5, 8), 20: (7, 10), 40: (9, 13), 60: (11, 15), 75: (13, 17), 82: (15, 19)},
    "flat_elemental": {1: (1, 3), 15: (4, 7), 30: (6, 10), 45: (9, 14), 60: (12, 18), 75: (16, 24)},
    "spell_damage": {1: (5, 10), 20: (8, 15), 40: (12, 20), 60: (16, 25), 75: (20, 30)},
    "resistance": {1: (6, 11), 15: (10, 15), 30: (13, 19), 45: (16, 24), 60: (20, 30), 75: (24, 35), 82: (30, 42)},
    "attribute": {1: (5, 10), 20: (8, 13), 40: (12, 17), 60: (16, 21), 75: (20, 26), 82: (24, 30)},
    "movement_speed": {1: (5, 10), 30: (10, 15), 55: (15, 20), 75: (20, 25), 82: (25, 35)},
    "crit_chance": {1: (5, 10), 30: (8, 15), 55: (12, 20), 75: (16, 25)},
    "crit_multiplier": {1: (8, 15), 30: (12, 20), 55: (16, 28), 75: (22, 35)},
    "spirit": {1: (5, 10), 30: (8, 15), 55: (12, 20), 75: (16, 25), 82: (20, 30)},
    "rarity": {1: (4, 8), 20: (6, 10), 40: (8, 14), 60: (10, 16)},
}

# Which mods are prefixes vs suffixes
# Source: poe2db.tw mod categories
PREFIX_MODS = {
    "life_flat", "es_flat", "armour_flat", "evasion_flat",
    "flat_phys", "increased_phys", "flat_elemental", "spell_damage",
    "life_percent", "es_percent", "armour_percent", "evasion_percent",
    "spirit", "rarity",
}

SUFFIX_MODS = {
    "resistance", "attribute", "attack_speed", "movement_speed",
    "crit_chance", "crit_multiplier",
}


# ============================================================
# Mod availability per equipment slot
# ============================================================

# Which mods can roll on which slot
# Source: poe2db.tw → Mods
SLOT_MODS: dict[str, set[str]] = {
    "Body Armour": {"life_flat", "life_percent", "es_flat", "es_percent",
                    "armour_flat", "armour_percent", "evasion_flat", "evasion_percent",
                    "resistance", "attribute", "rarity", "spirit"},
    "Helm": {"life_flat", "es_flat", "armour_flat", "evasion_flat",
             "resistance", "attribute", "rarity", "spirit",
             "crit_chance", "crit_multiplier"},
    "Gloves": {"life_flat", "armour_flat", "evasion_flat", "es_flat",
               "resistance", "attribute", "attack_speed", "flat_phys",
               "flat_elemental", "rarity"},
    "Boots": {"life_flat", "armour_flat", "evasion_flat", "es_flat",
              "resistance", "attribute", "movement_speed", "rarity"},
    "Ring": {"life_flat", "es_flat", "resistance", "attribute",
             "flat_phys", "flat_elemental", "rarity", "crit_chance",
             "crit_multiplier", "spirit"},
    "Amulet": {"life_flat", "es_flat", "resistance", "attribute",
               "spirit", "rarity", "crit_chance", "crit_multiplier",
               "flat_phys", "flat_elemental", "spell_damage"},
    "Belt": {"life_flat", "armour_flat", "es_flat",
             "resistance", "attribute", "rarity"},
    "Weapon": {"flat_phys", "increased_phys", "flat_elemental", "attack_speed",
               "crit_chance", "crit_multiplier", "attribute", "spell_damage"},
    "Shield": {"life_flat", "es_flat", "armour_flat", "armour_percent",
               "resistance", "attribute", "spell_damage", "rarity"},
}


# ============================================================
# Crafting methods and cost estimates
# ============================================================

@dataclass
class CraftStep:
    """A single step in a crafting process."""
    step: int
    action: str
    currency: str
    cost_estimate: str  # in chaos orb equivalents
    notes: str = ""


@dataclass
class CraftingPlan:
    """Complete crafting plan for an item."""
    slot: str
    base_item: str
    target_ilvl: int
    desired_mods: list[str]
    steps: list[CraftStep] = field(default_factory=list)
    total_cost_estimate: str = ""
    alternatives: list[str] = field(default_factory=list)

    def format(self) -> str:
        lines = [
            f"=== Crafting Plan: {self.slot} ({self.base_item}) ===",
            f"Target iLvl: {self.target_ilvl}",
            f"Desired mods: {', '.join(self.desired_mods)}",
            "",
            "--- Steps ---",
        ]
        for step in self.steps:
            lines.append(
                f"  {step.step}. {step.action}"
            )
            lines.append(f"     Currency: {step.currency}")
            lines.append(f"     Est. cost: {step.cost_estimate}")
            if step.notes:
                lines.append(f"     Note: {step.notes}")

        lines.append(f"\nTotal estimated cost: {self.total_cost_estimate}")

        if self.alternatives:
            lines.append("\n--- Alternatives ---")
            for alt in self.alternatives:
                lines.append(f"  • {alt}")

        return "\n".join(lines)


def get_best_ilvl(mod_name: str, desired_tier: int = 1) -> int:
    """Get the minimum iLvl needed for a mod to reach a given tier.

    Tier 1 = best (highest iLvl requirement).
    """
    tiers = ILVL_BREAKPOINTS.get(mod_name, {1: (1, 1)})
    sorted_ilvls = sorted(tiers.keys(), reverse=True)

    if desired_tier > len(sorted_ilvls):
        desired_tier = len(sorted_ilvls)

    return sorted_ilvls[-desired_tier] if desired_tier <= len(sorted_ilvls) else max(sorted_ilvls)


def get_mod_tier_ranges(mod_name: str) -> list[tuple[int, str]]:
    """Get all tier ranges for a mod."""
    tiers = ILVL_BREAKPOINTS.get(mod_name, {1: (1, 1)})
    result = []
    for i, ilvl in enumerate(sorted(tiers.keys(), reverse=True), 1):
        lo, hi = tiers[ilvl]
        result.append((i, f"iLvl {ilvl}+: {lo}-{hi}"))
    return result


def slot_has_mod(slot: str, mod: str) -> bool:
    """Check if a mod can roll on a given slot."""
    allowed = SLOT_MODS.get(slot, set())
    return mod in allowed


def get_base_for_slot(slot: str, base_type: Optional[str] = None) -> Optional[dict]:
    """Find the best base item for a slot/type combo."""
    bases = ITEM_BASES.get(slot, [])
    if not bases:
        # Check weapon bases
        if base_type:
            weapon_bases = WEAPON_BASES.get(base_type, [])
            if weapon_bases:
                return weapon_bases[-1]  # highest level base
    if base_type and bases:
        for base in reversed(bases):  # highest level first
            if base.get("type", "") == base_type:
                return base
    if bases:
        return bases[-1]  # default to highest level base
    return None


def plan_crafting(
    slot: str,
    base_item: Optional[str] = None,
    desired_mods: Optional[list[str]] = None,
    target_ilvl: int = 82,
    budget: str = "medium",
    base_type: Optional[str] = None,
) -> CraftingPlan:
    """Generate a crafting plan for a gear slot.

    Args:
        slot: Equipment slot (e.g. "Body Armour", "Ring")
        base_item: Specific base item name
        desired_mods: List of mod IDs (e.g. ["life_flat", "resistance", "resistance"])
        target_ilvl: Item level to target
        budget: "low", "medium", or "high"
        base_type: Item type (Armour, Armour/Evasion, Energy Shield)
    """
    desired_mods = desired_mods or []

    # Validate slot
    if slot not in SLOT_MODS and slot not in WEAPON_BASES and slot not in ITEM_BASES:
        return CraftingPlan(
            slot=slot, base_item=base_item or "unknown",
            target_ilvl=target_ilvl, desired_mods=desired_mods,
            total_cost_estimate="N/A",
            alternatives=[f"Slot '{slot}' not recognized. Available: {sorted(set(list(SLOT_MODS.keys()) + list(WEAPON_BASES.keys())))}"],
        )

    # Validate mods
    invalid = [m for m in desired_mods if m not in ILVL_BREAKPOINTS]
    unslottable = [m for m in desired_mods if not slot_has_mod(slot, m)]
    if unslottable:
        return CraftingPlan(
            slot=slot, base_item=base_item or "unknown",
            target_ilvl=target_ilvl, desired_mods=desired_mods,
            total_cost_estimate="N/A",
            alternatives=[f"Mod(s) cannot roll on {slot}: {', '.join(unslottable)}. "
                          f"Available mods: {', '.join(sorted(SLOT_MODS.get(slot, set())))}"],
        )

    # Find base item
    base = get_base_for_slot(slot, base_type or base_item)
    base_name = base_item or (base["name"] if base else "any")

    # Determine required iLvl for desired mods
    req_ilvls = []
    for mod in desired_mods:
        req_ilvl = get_best_ilvl(mod, desired_tier=2)  # aim for at least T2
        req_ilvls.append(req_ilvl)

    recommended_ilvl = max(req_ilvls) if req_ilvls else target_ilvl
    recommended_ilvl = max(recommended_ilvl, target_ilvl)

    # Build crafting steps
    steps = []
    total_cost = 0

    # Map mods to prefix/suffix counts
    prefixes = [m for m in desired_mods if m in PREFIX_MODS]
    suffixes = [m for m in desired_mods if m in SUFFIX_MODS]
    num_prefixes = len(prefixes)
    num_suffixes = len(suffixes)

    # Step 1: Acquire base
    if base and base.get("req_level", 0) <= recommended_ilvl:
        base_cost = max(1, base.get("req_level", 0) // 10)
        steps.append(CraftStep(1, f"Acquire {base['name']} base (iLvl {recommended_ilvl}+)",
                               "Trade or drop", f"{base_cost}c",
                               f"Implicit: {', '.join(base.get('implicits', ['none']))}"))
    else:
        steps.append(CraftStep(1, f"Acquire any {slot} base (iLvl {recommended_ilvl}+)",
                               "Trade or drop", "1-5c"))

    # Step 2: Quality
    quality_currency = {
        "Body Armour": "Armourer's Scrap", "Helm": "Armourer's Scrap",
        "Gloves": "Armourer's Scrap", "Boots": "Armourer's Scrap",
        "Shield": "Armourer's Scrap",
        "Weapon": "Blacksmith's Whetstone",
    }
    qc = quality_currency.get(slot, "Armourer's Scrap")
    steps.append(CraftStep(2, f"Quality to 20% with {qc}", qc, "1c",
                           "20 scraps — check vendor for scrap conversions"))

    # Step 3: Craft based on complexity
    if num_prefixes + num_suffixes <= 2 and budget == "low":
        # Simple: transmute → aug → regal
        steps.append(CraftStep(3, "Transmute to magic (hope for 1 desired mod)",
                               "Orb of Transmutation", "trivial"))
        steps.append(CraftStep(4, f"Augmentation for {num_prefixes + num_suffixes - 1} more desired mod",
                               "Orb of Augmentation", "trivial",
                               "If miss, scour and retry (Orb of Scouring = 1c)"))
        steps.append(CraftStep(5, "Regal to rare — pray for usable 3rd mod",
                               "Regal Orb", "1c"))
        total_cost = 3

    elif num_prefixes + num_suffixes <= 4 and budget in ("low", "medium"):
        # Medium: essence → regal → exalt
        essence_type = "Greed" if "life_flat" in desired_mods else \
                       "Zeal" if "attack_speed" in desired_mods else \
                       "Sorrow" if "flat_elemental" in desired_mods else \
                       "Contempt" if "flat_phys" in desired_mods else "Greed"
        steps.append(CraftStep(3, f"Essence of {essence_type} to guarantee 1 desired mod as magic",
                               f"Essence of {essence_type}", "2-5c",
                               "Use Screaming or higher tier for better rolls"))
        steps.append(CraftStep(4, f"Augmentation for 2nd desired mod (if needed)",
                               "Orb of Augmentation", "trivial"))
        steps.append(CraftStep(5, "Regal to rare",
                               "Regal Orb", "1c"))
        if num_prefixes + num_suffixes > 3:
            steps.append(CraftStep(6, f"Exalted Orb(s) — slam and pray for remaining mods",
                                   "Exalted Orb", f"{num_prefixes + num_suffixes - 3}x1-2c each"))
        total_cost = 8

    else:
        # High budget: essence spamming → meta-crafting
        steps.append(CraftStep(3, "Essence spam until 2-3 desired mods roll as magic",
                               "Greater Essence + Orb of Scouring", "10-30c",
                               "Use Greater Essence for guaranteed high-tier mod"))
        steps.append(CraftStep(4, "Regal to rare",
                               "Regal Orb", "1c"))
        steps.append(CraftStep(5, "Exalted Orb slams for remaining mods",
                               "Exalted Orb", "2-5c each",
                               "If bad mod hits, consider Annulment (Orb of Annulment ~3c)"))
        steps.append(CraftStep(6, "If prefixes/suffixes fill with bad mods: Annul + restart",
                               "Orb of Annulment", "3c per attempt",
                               "Annul removes one random mod — 1/3 or 1/6 chance to hit the bad one"))
        if budget == "high":
            steps.append(CraftStep(7, "Divine orb to max roll ranges on desired mods",
                                   "Divine Orb", "3-5c each",
                                   "Only worth if rolls are bottom-tier within their range"))
        total_cost = 50

    # Socket crafting (for items with rune sockets)
    if slot in ("Body Armour", "Helm", "Gloves", "Boots", "Shield"):
        steps.append(CraftStep(len(steps) + 1, "Add rune sockets via Jeweller's Orb",
                               "Artificer's Orb", "1c",
                               "Most items can have 1-2 rune sockets. Add Iron/Cold/Lightning Runes."))

    # Alternatives
    alternatives = []
    alternatives.append("Trade: check poe2 trade site — often cheaper to buy finished item")
    alternatives.append(f"Rog crafting (Expedition): great for {slot} with life+resists")
    if "resistance" in desired_mods:
        alternatives.append("Harvest crafting: guaranteed resistance swaps (fire↔cold↔lightning)")

    return CraftingPlan(
        slot=slot,
        base_item=base_name,
        target_ilvl=recommended_ilvl,
        desired_mods=desired_mods,
        steps=steps,
        total_cost_estimate=f"~{total_cost}c",
        alternatives=alternatives,
    )


def analyze_item_for_crafting(item: dict) -> str:
    """Analyze an existing item and suggest crafting improvements.

    Args:
        item: Item dict from PoE2 API (fetch_character output)
    """
    name = item.get("name", "") or item.get("typeLine", "Unknown")
    slot = item.get("inventoryId", "Unknown")
    ilvl = item.get("ilvl", 0)
    rarity = item.get("frameType", 0)
    rarity_str = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique"}.get(rarity, "?")

    lines = [
        f"--- {slot}: {name} ({rarity_str}, iLvl {ilvl}) ---",
    ]

    # Parse explicit mods
    explicit_mods = item.get("explicitMods", [])
    if explicit_mods:
        lines.append("Current explicit mods:")
        for mod in explicit_mods:
            lines.append(f"  • {mod}")

    # Parse implicits
    implicits = item.get("implicitMods", [])
    if implicits:
        lines.append("Implicits:")
        for imp in implicits:
            lines.append(f"  • {imp}")

    # Check sockets
    sockets = item.get("sockets", [])
    rune_sockets = [s for s in sockets if s.get("socketType") == "Rune"]
    if rune_sockets:
        socketed_items = item.get("socketedItems", [])
        lines.append(f"Rune sockets: {len(rune_sockets)} ({len(socketed_items)} filled)")
        for si in socketed_items:
            lines.append(f"  • {si.get('typeLine', '?')}")

    # Suggestions based on rarity
    lines.append("")
    if rarity == 0:  # Normal
        lines.append("[SUGGESTION] Normal item — transmute + aug + regal to get started")
    elif rarity == 1:  # Magic
        lines.append("[SUGGESTION] Magic item — regal + exalt to reach rare with 4-6 mods")
    elif rarity == 2:  # Rare
        # Check for missing life/ES/resists
        mod_text = " ".join(explicit_mods).lower()
        if "life" not in mod_text and "energy shield" not in mod_text:
            lines.append(f"[WARNING] No life or ES on {slot} — prioritize this for survivability")
        if "resistance" not in mod_text and "resist" not in mod_text:
            lines.append(f"[WARNING] No resistances on {slot} — consider replacing")
        if not explicit_mods or len(explicit_mods) < 4:
            lines.append(f"[SUGGESTION] Only {len(explicit_mods)} explicit mods — exalt slam or recraft")

    # iLvl check
    if ilvl < 50:
        lines.append(f"[INFO] Low iLvl ({ilvl}) — cannot roll high-tier mods. Replace with iLvl 75+ base.")

    return "\n".join(lines)


def list_mod_tiers(mod_name: Optional[str] = None) -> str:
    """List all mod tier breakpoints, optionally filtered by mod name."""
    lines = ["=== Mod Tier Breakpoints ===", ""]

    if mod_name:
        if mod_name in ILVL_BREAKPOINTS:
            lines.append(f"{mod_name}:")
            for tier_num, (lo, hi) in get_mod_tier_ranges(mod_name):
                lines.append(f"  T{tier_num}: {lo}-{hi}")
        else:
            lines.append(f"Unknown mod: {mod_name}")
            lines.append(f"Available: {', '.join(sorted(ILVL_BREAKPOINTS.keys()))}")
    else:
        for name in sorted(ILVL_BREAKPOINTS.keys()):
            tiers = ILVL_BREAKPOINTS[name]
            best_ilvl = max(tiers.keys())
            best_range = tiers[best_ilvl]
            prefix = "P" if name in PREFIX_MODS else "S" if name in SUFFIX_MODS else "?"
            lines.append(f"  [{prefix}] {name}: best at iLvl {best_ilvl}+ ({best_range[0]}-{best_range[1]})")

    return "\n".join(lines)


def list_bases(slot: Optional[str] = None) -> str:
    """List available base items, optionally filtered by slot."""
    lines = ["=== Item Bases ===", ""]

    if slot:
        bases = ITEM_BASES.get(slot, [])
        weapon_bases = WEAPON_BASES.get(slot, [])
        if bases:
            lines.append(f"--- {slot} ---")
            for b in bases:
                defs = b.get("base_armour", 0) or b.get("base_dmg_min", 0)
                lines.append(f"  {b['name']} (Lv.{b.get('req_level', '?')})")
                if b.get("implicits"):
                    for imp in b["implicits"]:
                        lines.append(f"    Implicit: {imp}")
        elif weapon_bases:
            lines.append(f"--- {slot} (Weapon) ---")
            for b in weapon_bases:
                lines.append(f"  {b['name']} (Lv.{b.get('req_level', '?')})")
                lines.append(f"    {b.get('base_dmg_min', 0)}-{b.get('base_dmg_max', 0)} phys, {b.get('base_aps', 0)} APS")
        else:
            lines.append(f"No bases found for slot: {slot}")
    else:
        for s in sorted(ITEM_BASES.keys()):
            lines.append(f"{s}: {len(ITEM_BASES[s])} bases")
        for s in sorted(WEAPON_BASES.keys()):
            lines.append(f"{s} (Weapon): {len(WEAPON_BASES[s])} bases")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Crafting Advisor — plan crafting for gear slots",
    )
    parser.add_argument("--slot", help="Equipment slot (e.g. 'Body Armour', 'Ring')")
    parser.add_argument("--base", help="Specific base item name")
    parser.add_argument("--type", help="Item type for weapons/armour (e.g. 'Crossbow', 'Armour')",
                        dest="base_type")
    parser.add_argument("--desired-mods", nargs="+",
                        help="Desired mod IDs (e.g. life_flat resistance attack_speed)")
    parser.add_argument("--ilvl", type=int, default=82,
                        help="Target item level (default: 82)")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="medium",
                        help="Crafting budget tier (default: medium)")
    parser.add_argument("--item", help="Analyze an existing item JSON file for crafting suggestions")
    parser.add_argument("--list-mods", action="store_true",
                        help="List all mod tier breakpoints")
    parser.add_argument("--mod", help="Show tier breakpoints for a specific mod")
    parser.add_argument("--list-bases", action="store_true",
                        help="List available item bases")
    parser.add_argument("--slot-bases", help="List bases for a specific slot")

    args = parser.parse_args()

    if args.list_mods or args.mod:
        print(list_mod_tiers(args.mod))
        return

    if args.list_bases or args.slot_bases:
        print(list_bases(args.slot_bases))
        return

    if args.item:
        try:
            with open(args.item) as f:
                item = json.load(f)
            print(analyze_item_for_crafting(item))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading item file: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.slot:
        parser.print_help()
        print("\nExamples:")
        print("  python crafting_advisor.py --slot 'Body Armour' --desired-mods life_flat resistance resistance armour_flat")
        print("  python crafting_advisor.py --slot Weapon --type Crossbow --desired-mods increased_phys flat_phys attack_speed")
        print("  python crafting_advisor.py --list-mods")
        print("  python crafting_advisor.py --mod life_flat")
        print("  python crafting_advisor.py --list-bases")
        return

    plan = plan_crafting(
        slot=args.slot,
        base_item=args.base,
        desired_mods=args.desired_mods,
        target_ilvl=args.ilvl,
        budget=args.budget,
        base_type=args.base_type,
    )
    print(plan.format())


if __name__ == "__main__":
    cli()
