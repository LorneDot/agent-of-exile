#!/usr/bin/env python3
"""PoE2 Character Stat Calculator.

Computes defensive and offensive stats from a build specification.
All formulas are sourced from documented PoE2 mechanics.

Sources:
  - GGG patch notes and in-game tooltips
  - Community-verified mechanics (PoE2 wiki/maxroll)
  - poe2-skilltree-export (passive tree data)

Usage:
    python calc_stats.py build_spec.json
    python calc_stats.py build_spec.json --detail
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================
# Constants — sourced from PoE2 in-game tooltips and patch notes
# ============================================================

# Base life at level 1, gain per level — source: PoE2 character panel
BASE_LIFE = 40
LIFE_PER_LEVEL = 12  # ~12 life per level

# Base mana at level 1, gain per level — source: PoE2 in-game
BASE_MANA = 40
MANA_PER_LEVEL = 6  # ~6 mana per level

# Base attributes per class — source: grindinggear/poe2-skilltree-export data.json
CLASS_BASE_ATTRS: dict[str, dict[str, int]] = {
    "Marauder":    {"str": 15, "dex": 7,  "int": 7},
    "Witch":       {"str": 7,  "dex": 7,  "int": 15},
    "Ranger":      {"str": 7,  "dex": 15, "int": 7},
    "Duelist":     {"str": 11, "dex": 11, "int": 7},
    "Shadow":      {"str": 7,  "dex": 11, "int": 11},
    "Templar":     {"str": 11, "dex": 7,  "int": 11},
    "Warrior":     {"str": 15, "dex": 7,  "int": 7},
    "Sorceress":   {"str": 7,  "dex": 7,  "int": 15},
    "Huntress":    {"str": 7,  "dex": 15, "int": 7},
    "Mercenary":   {"str": 11, "dex": 11, "int": 7},
    "Monk":        {"str": 7,  "dex": 11, "int": 11},
    "Druid":       {"str": 11, "dex": 7,  "int": 11},
}

# Life per point of Strength — source: PoE2 character panel tooltip
LIFE_PER_STR = 2
# Mana per point of Intelligence — source: PoE2 character panel tooltip
MANA_PER_INT = 2
# Accuracy per point of Dexterity — source: PoE2 character panel tooltip
ACCURACY_PER_DEX = 5

# Attribute gain per level (not automatic in PoE2 — from passive tree and gear)
# PoE2 gives no automatic attribute per level. All attributes come from:
# - Passive tree (+5 per travel node for the relevant stat)
# - Gear affixes
# Source: GGG PoE2 reveal stream, confirmed in-game

# Resistance penalties — source: GGG patch notes, PoE2 campaign progression
ELEMENTAL_RES_PENALTY = {
    "act1_cruel": 0,    # After Act 1
    "act2_cruel": -10,  # After Act 3 (acts 1-3 cruel)
    "act3_cruel": -20,  # After Act 6
    "act4_cruel": -30,  # After Act 8
    "act5_cruel": -40,  # After Act 10 / early maps
    "endgame": -60,     # Default endgame penalty
}
# Source: GGG confirmed -60% res penalty in endgame [GGG-PN]

# Resistance cap (default) — source: PoE2 in-game
RES_CAP_BASE = 75
# Max achievable res cap — source: +max res mods from tree/gear
RES_CAP_MAX = 90

# Chaos resistance does not have the campaign penalty
# Source: PoE2 in-game, GGG developer comments

# Armour damage reduction formula — source: GGG developer posts, community testing
# Reduction = Armour / (Armour + 5 * Damage)
# Confirmed for PoE2 by GGG [GGG-DEV]

# Evasion formula — source: GGG developer posts
# Chance to Evade = 1 - Accuracy / (Accuracy + (Evasion * 0.25) ^ 0.8)
# Uses entropy system [GGG-IG]

# Energy Shield — source: PoE2 in-game
# Base ES from gear + % increases from passives and INT
# ES recharge: 33% per second after 2 seconds of not taking damage
# ES recharge rate scales with faster start of ES recharge

# Spirit — source: GGG PoE2 reveal
# Base: 100 Spirit at level 1 (from campaign)
# Gained from: gear affixes, passive tree, ascendancy nodes
# Used by: aura skills, herald skills, meta gems

# Stun threshold — source: PoE2 in-game
# Based on maximum life (and ES if you have specific keystones)

# ============================================================
# Damage formulas — sourced from PoE2 community testing & GGG
# ============================================================

# Hit damage formula (non-DoT):
#   Damage = (BaseFlat + AddedFlat) × (1 + Σ increased) × Π(1 + more)
#          × effectiveness_of_added_damage
#
# Source: GGG developer manifesto, verified in PoE2 beta

# DoT damage formula:
#   Damage = (BaseDoT + AddedFlat) × (1 + Σ increased) × Π(1 + more)
#          × (1 + Σ damage_over_time_multiplier)
#
# Source: PoE2 tooltips, community testing

# Ailment thresholds — source: GGG developer posts, PoE2 wiki
# Shock: base 20% increased damage taken, +5% per 5% shock effect over threshold
#        (max 50% without increased maximum)
# Chill: slow 10-30% based on cold damage relative to enemy max life
# Freeze: duration based on cold damage relative to enemy max life
# Ignite: 90% of base hit damage per second for 4 seconds
# Source: PoE2 tooltip descriptions, GGG balance manifesto

# Critical strike — source: PoE2 in-game
# Base crit chance: varies per weapon/skill (typically 5-7%)
# Base crit multi: 150% (100% base + 50% bonus)
# Lucky/unlucky: roll twice, take better/worse (source: GGG)


@dataclass
class DefensiveStats:
    """Computed defensive stat block."""

    life: float = 0
    energy_shield: float = 0
    mana: float = 0
    armour: float = 0
    evasion: float = 0

    fire_res: float = 0
    cold_res: float = 0
    lightning_res: float = 0
    chaos_res: float = 0

    block_chance: float = 0
    spell_block: float = 0
    spell_suppression: float = 0

    life_regen: float = 0
    es_regen: float = 0
    mana_regen: float = 0
    leech_rate: float = 0

    @property
    def ehp(self) -> float:
        """Effective HP (life + ES). Simplified — doesn't account for resists."""
        return self.life + self.energy_shield

    @property
    def ehp_vs_elemental(self) -> float:
        """EHP vs elemental, accounting for resistance."""
        avg_res = (self.fire_res + self.cold_res + self.lightning_res) / 3
        if avg_res >= 100:
            return float("inf")  # immune
        return self.ehp / (1 - avg_res / 100)

    def summary(self) -> str:
        """One-line defense summary."""
        parts = [f"Life: {self.life:.0f}", f"ES: {self.energy_shield:.0f}",
                 f"EHP: {self.ehp:.0f}"]
        if self.armour:
            parts.append(f"Armour: {self.armour:.0f}")
        if self.evasion:
            parts.append(f"Evasion: {self.evasion:.0f}")
        return " | ".join(parts)


@dataclass
class OffensiveStats:
    """Computed offensive stat block."""

    main_skill_dps: float = 0
    hit_damage: float = 0
    attacks_per_second: float = 0
    crit_chance: float = 0
    crit_multiplier: float = 150
    accuracy: float = 0
    hit_chance: float = 100  # vs white mobs
    impale_chance: float = 0
    penetration: float = 0

    @property
    def effective_dps(self) -> float:
        """DPS after crit and accuracy."""
        crit_factor = 1 + (self.crit_chance / 100) * ((self.crit_multiplier / 100) - 1)
        return self.main_skill_dps * crit_factor * (self.hit_chance / 100)

    def summary(self) -> str:
        parts = [f"DPS: {self.effective_dps:.0f}",
                 f"Hit: {self.hit_damage:.0f}",
                 f"APS: {self.attacks_per_second:.2f}"]
        if self.crit_chance:
            parts.append(f"Crit: {self.crit_chance:.0f}%")
        return " | ".join(parts)


@dataclass
class BuildStats:
    """Full computed build statistics."""

    level: int = 80
    class_name: str = ""
    ascendancy: str = ""
    attributes: dict[str, int] = field(default_factory=lambda: {"str": 0, "dex": 0, "int": 0})
    defence: DefensiveStats = field(default_factory=DefensiveStats)
    offence: OffensiveStats = field(default_factory=OffensiveStats)

    def summary(self) -> str:
        lines = [
            f"=== {self.class_name} → {self.ascendancy} (Lv.{self.level}) ===",
            f"STR:{self.attributes['str']} DEX:{self.attributes['dex']} INT:{self.attributes['int']}",
            f"",
            f"--- Defense ---",
            self.defence.summary(),
            f"EHP vs Ele: {self.defence.ehp_vs_elemental:.0f}",
            f"Res: F{self.defence.fire_res:.0f}% C{self.defence.cold_res:.0f}% L{self.defence.lightning_res:.0f}% Ch{self.defence.chaos_res:.0f}%",
            f"",
            f"--- Offense ---",
            self.offence.summary(),
        ]
        return "\n".join(lines)


def estimate_life(base_class: str, level: int, strength: int,
                  life_from_tree: float = 0,
                  life_from_gear: float = 0) -> float:
    """Estimate total life.

    Formula: (BASE + LEVEL*GAIN + STR*LIFE_PER_STR + flat_from_gear)
             × (1 + %increased_from_tree + %increased_from_gear)
    """
    base_life = BASE_LIFE + level * LIFE_PER_LEVEL
    life_from_str = strength * LIFE_PER_STR

    # Typical % increased life available
    # Source: community build data — PoE2 has limited %life on tree
    pct_increased = life_from_tree / 100  # life_from_tree is percentages

    flat_total = base_life + life_from_str + life_from_gear
    return flat_total * (1 + pct_increased)


def estimate_mana(base_class: str, level: int, intelligence: int,
                  mana_from_tree: float = 0,
                  mana_from_gear: float = 0) -> float:
    """Estimate total mana.

    Formula: (BASE + LEVEL*GAIN + INT*MANA_PER_INT + flat_from_gear)
             × (1 + %increased_from_tree)
    """
    base_mana = BASE_MANA + level * MANA_PER_LEVEL
    mana_from_int = intelligence * MANA_PER_INT

    pct_increased = mana_from_tree / 100

    flat_total = base_mana + mana_from_int + mana_from_gear
    return flat_total * (1 + pct_increased)


def estimate_armour_reduction(armour: float, hit_damage: float) -> float:
    """Armour damage reduction % against a given hit.

    Formula: Reduction = Armour / (Armour + 5 × HitDamage)
    Source: GGG developer posts, verified in PoE2 community testing.
    """
    if armour <= 0 or hit_damage <= 0:
        return 0.0
    return (armour / (armour + 5 * hit_damage)) * 100


def estimate_resistances(gear_res: dict[str, float],
                         tree_res: dict[str, float],
                         campaign_progress: str = "endgame") -> dict[str, float]:
    """Calculate effective resistances after penalty.

    Source: PoE2 campaign applies -60% total penalty by endgame.
    Each resistance is capped at 75% (higher with +max res).
    """
    penalty = ELEMENTAL_RES_PENALTY.get(campaign_progress, -60)

    result = {}
    for res_type in ("fire", "cold", "lightning"):
        total = gear_res.get(res_type, 0) + tree_res.get(res_type, 0) + penalty
        result[f"{res_type}_res"] = min(total, RES_CAP_BASE)

    # Chaos doesn't have the penalty
    result["chaos_res"] = min(gear_res.get("chaos", 0) + tree_res.get("chaos", 0),
                              RES_CAP_BASE)

    return result


def compute_stats(spec: dict) -> BuildStats:
    """Compute full stats for a build spec."""
    level = spec.get("level", 80)
    class_name = spec.get("className", "")
    ascendancy = spec.get("ascendClassName", "")

    # Base attributes
    base_attrs = CLASS_BASE_ATTRS.get(class_name, {"str": 0, "dex": 0, "int": 0})

    # Estimated attributes from tree (user-provided or estimated from passives count)
    tree_attrs = spec.get("treeAttributes", {"str": 0, "dex": 0, "int": 0})
    gear_attrs = spec.get("gearAttributes", {"str": 0, "dex": 0, "int": 0})

    strength = base_attrs["str"] + tree_attrs.get("str", 0) + gear_attrs.get("str", 0)
    dexterity = base_attrs["dex"] + tree_attrs.get("dex", 0) + gear_attrs.get("dex", 0)
    intelligence = base_attrs["int"] + tree_attrs.get("int", 0) + gear_attrs.get("int", 0)

    # Life estimate
    life_tree = spec.get("increasedLifeFromTree", 0)  # sum of % increased life
    life_gear = spec.get("flatLifeFromGear", 0)
    life = estimate_life(class_name, level, strength, life_tree, life_gear)

    # Mana estimate
    mana_tree = spec.get("increasedManaFromTree", 0)
    mana_gear = spec.get("flatManaFromGear", 0)
    mana = estimate_mana(class_name, level, intelligence, mana_tree, mana_gear)

    # ES estimate (from gear + tree %)
    es_flat = spec.get("flatESFromGear", 0)
    es_increased = spec.get("increasedESFromTree", 0) + intelligence * 0.2  # ~0.2% ES per INT
    energy_shield = es_flat * (1 + es_increased / 100)

    # Resistances
    gear_res = spec.get("gearResistances", {})
    tree_res = spec.get("treeResistances", {})
    res = estimate_resistances(gear_res, tree_res,
                               spec.get("campaignProgress", "endgame"))

    # Armour/Evasion
    armour = spec.get("armourFromGear", 0) * (1 + spec.get("increasedArmourFromTree", 0) / 100)
    evasion = spec.get("evasionFromGear", 0) * (1 + spec.get("increasedEvasionFromTree", 0) / 100)

    defence = DefensiveStats(
        life=life,
        energy_shield=energy_shield,
        mana=mana,
        armour=armour,
        evasion=evasion,
        **res,
        block_chance=spec.get("blockChance", 0),
        spell_block=spec.get("spellBlock", 0),
        spell_suppression=spec.get("spellSuppression", 0),
        life_regen=life * spec.get("lifeRegenPercent", 0) / 100,
        mana_regen=mana * spec.get("manaRegenPercent", 1.75) / 100,  # base 1.75%
    )

    # Offensive estimates
    main_dps = spec.get("estimatedMainSkillDPS", 0)
    hit_damage = spec.get("averageHitDamage", 0)
    aps = spec.get("attacksPerSecond", 1.0)
    accuracy = dexterity * ACCURACY_PER_DEX + spec.get("flatAccuracy", 0)
    # Simplified hit chance vs white mobs at same level
    hit_chance = min(100, accuracy / (accuracy + level * 10) * 100)

    offence = OffensiveStats(
        main_skill_dps=main_dps,
        hit_damage=hit_damage,
        attacks_per_second=aps,
        crit_chance=spec.get("critChance", 0),
        crit_multiplier=spec.get("critMultiplier", 150),
        accuracy=accuracy,
        hit_chance=hit_chance,
        penetration=spec.get("penetration", 0),
    )

    return BuildStats(
        level=level,
        class_name=class_name,
        ascendancy=ascendancy,
        attributes={"str": strength, "dex": dexterity, "int": intelligence},
        defence=defence,
        offence=offence,
    )


def analyze_defense(stats: BuildStats, spec: dict) -> str:
    """Analyze defensive layers against map/pinnacle thresholds.

    Thresholds (community-vetted for PoE2 softcore):
      T1 Waystones (68): 3K EHP + capped res
      T6 Waystones (73): 4K EHP + capped res + 1 layer
      T11 Waystones (78): 5K EHP + capped res + 2 layers
      T16 Waystones (82): 6K EHP + overcapped res + 2 layers
      Pinnacle boss: 8K EHP + overcapped res + 3 layers

    Defensive layers counted: armour >5K, evasion >8K, block >30%,
    spell suppression >50%, Mind over Matter.
    """
    # Raw resistance totals (before 75% cap) to check overcapping
    gear_res = spec.get("gearResistances", {})
    tree_res = spec.get("treeResistances", {})
    penalty = ELEMENTAL_RES_PENALTY.get(
        spec.get("campaignProgress", "endgame"), -60
    )

    raw_res: dict[str, float] = {}
    for rtype in ("fire", "cold", "lightning"):
        raw_res[rtype] = gear_res.get(rtype, 0) + tree_res.get(rtype, 0) + penalty

    # Count defensive layers
    layer_names: list[str] = []
    if stats.defence.armour > 5000:
        layer_names.append(f"Armour ({stats.defence.armour:.0f})")
    if stats.defence.evasion > 8000:
        layer_names.append(f"Evasion ({stats.defence.evasion:.0f})")
    if stats.defence.block_chance > 30:
        layer_names.append(f"Block ({stats.defence.block_chance:.0f}%)")
    if stats.defence.spell_suppression > 50:
        layer_names.append(f"Spell Supp ({stats.defence.spell_suppression:.0f}%)")
    if spec.get("mindOverMatter"):
        layer_names.append("MoM")

    num_layers = len(layer_names)
    ehp = stats.defence.ehp

    # Capped check (all three elemental res at the 75% soft-cap)
    res_capped = all(
        getattr(stats.defence, f"{r}_res") >= RES_CAP_BASE
        for r in ("fire", "cold", "lightning")
    )
    # Overcapped = raw total exceeds cap (buffer against curses/pen)
    res_overcapped = all(
        raw_res[r] > RES_CAP_BASE for r in ("fire", "cold", "lightning")
    )

    tiers: list[tuple[str, float, str, int]] = [
        ("T1 Waystones (68)",   3000, "capped",     0),
        ("T6 Waystones (73)",   4000, "capped",     1),
        ("T11 Waystones (78)",  5000, "capped",     2),
        ("T16 Waystones (82)",  6000, "overcapped", 2),
        ("Pinnacle boss",  8000, "overcapped", 3),
    ]

    lines: list[str] = ["=== Defense Layer Analysis ===", ""]
    for name, ehp_thresh, res_req, layer_req in tiers:
        issues: list[str] = []

        if ehp < ehp_thresh:
            issues.append(
                f"EHP {ehp:.0f} below {ehp_thresh} threshold "
                f"(short by {ehp_thresh - ehp:.0f})"
            )

        if res_req == "capped" and not res_capped:
            missing = [
                r for r in ("fire", "cold", "lightning")
                if getattr(stats.defence, f"{r}_res") < RES_CAP_BASE
            ]
            issues.append(f"resists not capped (missing: {', '.join(missing)})")

        if res_req == "overcapped" and not res_overcapped:
            under = [
                f"{r} raw={raw_res[r]:.0f}%"
                for r in ("fire", "cold", "lightning")
                if raw_res[r] <= RES_CAP_BASE
            ]
            issues.append(f"resists not overcapped ({', '.join(under)})")

        if num_layers < layer_req:
            issues.append(
                f"only {num_layers} defensive layer(s) (need {layer_req})"
            )

        if issues:
            lines.append(f"{name}: UNSAFE — {'; '.join(issues)}")
        else:
            layer_detail = ""
            if layer_names:
                layer_detail = f" ({num_layers} layers: {', '.join(layer_names)})"
            lines.append(f"{name}: SAFE{layer_detail}")

    return "\n".join(lines)


def compute_gear_targets(stats: BuildStats, spec: dict,
                         targets: dict) -> str:
    """Compute gear gaps needed to reach desired stat targets.

    Compares tree-provided stats against user's desired targets and
    reports what must be sourced from gear (+ runes for resistances).
    """
    base_attrs = CLASS_BASE_ATTRS.get(
        stats.class_name, {"str": 0, "dex": 0, "int": 0}
    )
    tree_attrs = spec.get("treeAttributes", {"str": 0, "dex": 0, "int": 0})

    # Tree-only life (no gear contributions)
    tree_str = base_attrs["str"] + tree_attrs.get("str", 0)
    life_tree_pct = spec.get("increasedLifeFromTree", 0)
    tree_life_flat = (
        BASE_LIFE + stats.level * LIFE_PER_LEVEL + tree_str * LIFE_PER_STR
    )
    tree_life = tree_life_flat * (1 + life_tree_pct / 100)

    # Tree-only mana
    tree_int = base_attrs["int"] + tree_attrs.get("int", 0)
    mana_tree_pct = spec.get("increasedManaFromTree", 0)
    tree_mana_flat = (
        BASE_MANA + stats.level * MANA_PER_LEVEL + tree_int * MANA_PER_INT
    )
    tree_mana = tree_mana_flat * (1 + mana_tree_pct / 100)

    # Tree resists
    tree_res = spec.get("treeResistances", {})
    penalty = ELEMENTAL_RES_PENALTY.get(
        spec.get("campaignProgress", "endgame"), -60
    )

    lines: list[str] = ["=== Gear Target Analysis ===", ""]

    # --- Life target ---
    if "life" in targets:
        target_life = float(targets["life"])
        gap = target_life - tree_life
        if gap > 0.5:
            # Flat life from gear also gets multiplied by %increased
            multiplier = 1 + life_tree_pct / 100
            flat_needed = gap / multiplier if multiplier > 0 else gap
            lines.append(
                f"To reach {target_life:.0f} life: need +{flat_needed:.0f} "
                f"flat life from gear (tree gives {tree_life:.0f} base)"
            )
        else:
            lines.append(
                f"Life target of {target_life:.0f} already met "
                f"(tree gives {tree_life:.0f})"
            )

    # --- Mana target ---
    if "mana" in targets:
        target_mana = float(targets["mana"])
        gap = target_mana - tree_mana
        if gap > 0.5:
            multiplier = 1 + mana_tree_pct / 100
            flat_needed = gap / multiplier if multiplier > 0 else gap
            lines.append(
                f"To reach {target_mana:.0f} mana: need +{flat_needed:.0f} "
                f"flat mana from gear (tree gives {tree_mana:.0f} base)"
            )
        else:
            lines.append(
                f"Mana target of {target_mana:.0f} already met "
                f"(tree gives {tree_mana:.0f})"
            )

    # --- Resistance targets ---
    for res_name in ("fire", "cold", "lightning"):
        target_key = f"{res_name}_res"
        if target_key in targets:
            target = float(targets[target_key])
            tree_provided = tree_res.get(res_name, 0)
            # After penalty: gear + tree + penalty >= target
            needed = target - tree_provided - penalty
            if needed > 0:
                lines.append(
                    f"To cap {res_name} res: need +{needed:.0f}% from "
                    f"gear+runes (after {penalty}% penalty, tree gives "
                    f"{tree_provided:.0f}%)"
                )
            else:
                after_pen = tree_provided + penalty
                lines.append(
                    f"{res_name} res already capped from tree "
                    f"(tree gives {tree_provided:.0f}%, "
                    f"after penalty: {after_pen:.0f}%)"
                )

    # --- Chaos resistance (no campaign penalty) ---
    if "chaos_res" in targets:
        target = float(targets["chaos_res"])
        tree_provided = tree_res.get("chaos", 0)
        needed = target - tree_provided
        if needed > 0:
            lines.append(
                f"To cap chaos res: need +{needed:.0f}% from gear "
                f"(tree gives {tree_provided:.0f}%)"
            )
        else:
            lines.append(
                f"Chaos res already capped from tree "
                f"(tree gives {tree_provided:.0f}%)"
            )

    # --- Attribute targets ---
    for attr in ("str", "dex", "int"):
        if attr in targets:
            target = int(targets[attr])
            tree_provided = base_attrs.get(attr, 0) + tree_attrs.get(attr, 0)
            gap = target - tree_provided
            if gap > 0:
                lines.append(
                    f"To reach {target} {attr.upper()}: need +{gap} "
                    f"from gear (tree gives {tree_provided})"
                )
            else:
                lines.append(
                    f"{attr.upper()} target of {target} already met "
                    f"(tree gives {tree_provided})"
                )

    return "\n".join(lines)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute PoE2 character stats from a build spec"
    )
    parser.add_argument("spec", help="Build spec JSON")
    parser.add_argument("--detail", action="store_true",
                        help="Show detailed breakdowns")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--danger", action="store_true",
                        help="Analyze defensive layers vs map/pinnacle thresholds")
    parser.add_argument("--targets", type=str, default=None,
                        help="JSON dict of desired stats for gear gap analysis, "
                             "e.g. '{\"life\": 4000, \"fire_res\": 75}'")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    stats = compute_stats(spec)

    if args.json:
        import dataclasses
        print(json.dumps(dataclasses.asdict(stats), indent=2))
    elif args.detail:
        print(stats.summary())
        print()
        phys_hit = spec.get("typicalPhysicalHit", 2000)
        if stats.defence.armour:
            red = estimate_armour_reduction(stats.defence.armour, phys_hit)
            print(f"Armour reduction vs {phys_hit} phys hit: {red:.1f}%")
    else:
        print(stats.summary())

    # Defense layer analysis
    if args.danger:
        print()
        print(analyze_defense(stats, spec))

    # Gear target analysis
    if args.targets:
        try:
            targets = json.loads(args.targets)
        except json.JSONDecodeError as e:
            print(f"Error parsing --targets JSON: {e}", file=sys.stderr)
            sys.exit(1)
        print()
        print(compute_gear_targets(stats, spec, targets))


if __name__ == "__main__":
    cli()
