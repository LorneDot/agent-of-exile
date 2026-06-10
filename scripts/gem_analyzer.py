#!/usr/bin/env python3
"""PoE2 Enhanced Gem Analyzer.

Extends gem_linker.py with:
- DPS simulation with support gem multipliers
- Breakpoint analysis (level thresholds)
- Attribute requirement checking
- Full support synergy scoring matrix
- 5-link and 6-link optimization

Usage:
    python gem_analyzer.py --skill "Explosive Grenade" --level 80
    python gem_analyzer.py --skill "Spark" --simulate-dps --links 5
    python gem_analyzer.py --skill "Fireball" --check-requirements --level 90
    python gem_analyzer.py --skill "Explosive Grenade" --optimize-links 5
    python gem_analyzer.py --compare "Spark" "Arc"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

GEMS_CACHE = Path.home() / ".cache" / "poe2-theory-crafter" / "gems.json"

from gem_linker import (
    SKILL_TAGS, EFFECT_PRIORITY,
    load_gem_data, find_supports,
)


# ============================================================
# Skill gem base data — DPS, scaling, attribute requirements
# ============================================================

@dataclass
class SkillGemData:
    """Detailed skill gem information."""
    name: str
    tags: list[str]
    base_damage_min: float = 0
    base_damage_max: float = 0
    damage_effectiveness: float = 100  # percent
    base_aps: float = 1.0
    damage_type: str = "physical"  # physical, fire, cold, lightning, chaos
    str_req: int = 0
    dex_req: int = 0
    int_req: int = 0
    level_multiplier: float = 1.05  # ~5% more damage per level
    quality_bonus: str = ""


# Extended skill gem database
SKILL_GEM_DATA: dict[str, SkillGemData] = {
    "Explosive Grenade": SkillGemData(
        name="Explosive Grenade",
        tags=["Attack", "AoE", "Projectile", "Grenade", "Fire", "Detonator"],
        base_damage_min=45, base_damage_max=135,
        damage_effectiveness=120,
        base_aps=1.0,
        damage_type="fire",
        dex_req=72, int_req=48,
        quality_bonus="+1% increased Area of Effect",
    ),
    "Spark": SkillGemData(
        name="Spark",
        tags=["Spell", "Projectile", "Lightning", "Duration"],
        base_damage_min=8, base_damage_max=48,
        damage_effectiveness=70,
        base_aps=1.0,
        damage_type="lightning",
        int_req=98,
        quality_bonus="+1% increased Projectile Speed",
    ),
    "Fireball": SkillGemData(
        name="Fireball",
        tags=["Spell", "AoE", "Projectile", "Fire"],
        base_damage_min=30, base_damage_max=45,
        damage_effectiveness=240,
        base_aps=1.0,
        damage_type="fire",
        int_req=109,
        quality_bonus="+1% chance to Ignite",
    ),
    "Arc": SkillGemData(
        name="Arc",
        tags=["Spell", "Lightning", "Chain"],
        base_damage_min=6, base_damage_max=62,
        damage_effectiveness=100,
        base_aps=1.0,
        damage_type="lightning",
        int_req=109,
        quality_bonus="+1% chance to Shock",
    ),
    "Lightning Arrow": SkillGemData(
        name="Lightning Arrow",
        tags=["Attack", "AoE", "Projectile", "Lightning", "Bow"],
        base_damage_min=28, base_damage_max=55,
        damage_effectiveness=105,
        base_aps=1.0,
        damage_type="lightning",
        dex_req=98,
        quality_bonus="+1% increased Attack Speed",
    ),
    "Ice Shot": SkillGemData(
        name="Ice Shot",
        tags=["Attack", "AoE", "Projectile", "Cold", "Bow"],
        base_damage_min=28, base_damage_max=55,
        damage_effectiveness=105,
        base_aps=1.0,
        damage_type="cold",
        dex_req=98,
        quality_bonus="+1% chance to Freeze",
    ),
    "Earthquake": SkillGemData(
        name="Earthquake",
        tags=["Attack", "AoE", "Melee", "Slam", "Duration"],
        base_damage_min=65, base_damage_max=100,
        damage_effectiveness=160,
        base_aps=0.75,
        damage_type="physical",
        str_req=98,
        quality_bonus="+1% increased Area of Effect",
    ),
    "Essence Drain": SkillGemData(
        name="Essence Drain",
        tags=["Spell", "Projectile", "Chaos", "DamageOverTime"],
        base_damage_min=25, base_damage_max=38,
        damage_effectiveness=100,
        base_aps=1.0,
        damage_type="chaos",
        int_req=82, dex_req=48,
        quality_bonus="+1% Chaos Damage over Time Multiplier",
    ),
    "Cyclone": SkillGemData(
        name="Cyclone",
        tags=["Attack", "AoE", "Melee", "Movement"],
        base_damage_min=35, base_damage_max=55,
        damage_effectiveness=70,
        base_aps=3.0,
        damage_type="physical",
        str_req=72, dex_req=48,
        quality_bonus="+1% increased Area of Effect",
    ),
    "Skeletal Warrior": SkillGemData(
        name="Skeletal Warrior",
        tags=["Spell", "Minion", "Duration"],
        base_damage_min=0, base_damage_max=0,
        damage_effectiveness=100,
        base_aps=1.0,
        damage_type="minion",
        int_req=64,
        quality_bonus="Summoned Skeletons have +1% increased maximum Life",
    ),
    "Contagion": SkillGemData(
        name="Contagion",
        tags=["Spell", "AoE", "Chaos", "DamageOverTime"],
        base_damage_min=15, base_damage_max=22,
        damage_effectiveness=100,
        base_aps=1.0,
        damage_type="chaos",
        int_req=82,
        quality_bonus="+1% increased Area of Effect",
    ),
}


# ============================================================
# Effect multiplier estimates for support gem types
# ============================================================

SUPPORT_MULTIPLIERS: dict[str, float] = {
    "more_damage": 1.30,       # ~30% more damage
    "more_projectiles": 1.25,  # ~25% more projectiles = ~25% more damage for proj
    "penetration": 1.15,       # ~15% effective damage through resist pen
    "extra_use": 1.20,         # Extra use = ~20% more uptime
    "added_damage": 1.20,      # Added flat damage
    "faster_detonation": 1.15, # Faster detonation = QoL, ~15% effective DPS
    "pierce": 1.10,            # ~10% more clear speed
    "chain": 1.15,             # ~15% more clear speed
    "fork": 1.10,              # ~10% more clear speed
    "ailment_spread": 1.10,    # ~10% more ailment coverage
    "ailment_effect": 1.15,    # ~15% more ailment effectiveness
    "impale": 1.25,            # ~25% more physical damage from impale
    "increased_speed": 1.10,   # ~10% more effective DPS
    "increased_aoe": 1.05,     # AoE QoL, ~5% effective DPS
    "increased_cast_speed": 1.15,  # ~15% more cast speed
    "increased_duration": 1.05,    # ~5% more effective DPS for duration skills
    "cost_reduction": 1.0,     # QoL only
    "buff": 1.15,              # Generic buff ~15%
    "debuff": 1.10,            # Generic debuff ~10%
    "utility": 1.05,           # Minor utility
    "cost_conversion": 1.0,    # QoL only
    "magic_find": 1.0,         # No DPS impact
}


@dataclass
class GemDpsSimulation:
    """DPS simulation result for a gem setup."""
    skill: str
    gem_level: int
    links: int
    base_damage: float
    damage_effectiveness: float
    aps: float
    total_multiplier: float
    estimated_dps: float
    supports: list[str]
    multiplier_breakdown: list[tuple[str, float]] = field(default_factory=list)

    def format(self) -> str:
        lines = [
            f"=== DPS Simulation: {self.skill} (Lv.{self.gem_level}, {self.links}-link) ===",
            f"Base damage: {self.base_damage:.0f}",
            f"Effectiveness: {self.damage_effectiveness:.0f}%",
            f"APS: {self.aps:.2f}",
            f"Total multiplier: {self.total_multiplier:.2f}x",
            f"Estimated DPS: {self.estimated_dps:.0f}",
            "",
            "--- Support Gem Breakdown ---",
        ]
        for support, mult in self.multiplier_breakdown:
            lines.append(f"  {support}: {mult:.2f}x")

        return "\n".join(lines)


@dataclass
class GemComparison:
    """Comparison between two skills."""
    skill_a: str
    skill_b: str
    dps_a: float
    dps_b: float
    tags_a: list[str]
    tags_b: list[str]
    shared_tags: list[str]
    winner: str
    dps_ratio: float

    def format(self) -> str:
        lines = [
            f"=== {self.skill_a} vs {self.skill_b} ===",
            f"",
            f"  {self.skill_a}: {self.dps_a:.0f} DPS",
            f"  {self.skill_b}: {self.dps_b:.0f} DPS",
            f"  Winner: {self.winner} ({self.dps_ratio:.1f}x)",
            f"",
            f"  Shared tags: {', '.join(self.shared_tags)}",
            f"  {self.skill_a} unique: {', '.join(set(self.tags_a) - set(self.tags_b))}",
            f"  {self.skill_b} unique: {', '.join(set(self.tags_b) - set(self.tags_a))}",
        ]
        return "\n".join(lines)


def simulate_dps(
    skill_name: str,
    gem_level: int = 20,
    links: int = 4,
    quality: int = 20,
    gem_data: Optional[dict] = None,
    weapon_damage: float = 0,
    added_flat: float = 0,
    increased_mod: float = 0,
) -> GemDpsSimulation:
    """Simulate DPS for a gem setup with support gems.

    Formula:
      DPS = (BaseDmg + WeaponDmg + AddedFlat) × (1 + increased/100)
           × Effectiveness × APS × level_scaling × Π(support_multipliers)
    """
    # Get skill data
    skill_lower = skill_name.lower().strip()
    skill_data = SKILL_GEM_DATA.get(skill_name)
    if not skill_data:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_lower:
                skill_data = val
                skill_name = key
                break

    if not skill_data:
        return GemDpsSimulation(
            skill=skill_name, gem_level=gem_level, links=links,
            base_damage=0, damage_effectiveness=100, aps=1.0,
            total_multiplier=1.0, estimated_dps=0, supports=[],
            multiplier_breakdown=[("Skill not in database", 0)],
        )

    # Level scaling: ~5% more per level above 1
    level_scaling = skill_data.level_multiplier ** (gem_level - 1)

    # Average base damage
    avg_base = (skill_data.base_damage_min + skill_data.base_damage_max) / 2

    # Quality bonus
    quality_mult = 1.0 + quality * 0.005  # ~0.5% per quality point

    # Get support gems
    if gem_data is None:
        gem_data = load_gem_data()
    supports = find_supports(skill_data.tags, gem_data, max_results=links - 1)

    # Calculate multipliers
    total_mult = 1.0
    multiplier_breakdown: list[tuple[str, float]] = []

    # Skill gem itself counts as 1 link
    for i, (name, score, effect, reason) in enumerate(supports):
        if i >= links - 1:
            break
        mult = SUPPORT_MULTIPLIERS.get(effect, 1.05)
        total_mult *= mult
        multiplier_breakdown.append((name, mult))

    # Base damage calculation
    total_base = avg_base + weapon_damage + added_flat
    increased_factor = 1 + increased_mod / 100
    effectiveness_factor = skill_data.damage_effectiveness / 100

    dps = (total_base * increased_factor * effectiveness_factor *
           skill_data.base_aps * level_scaling * quality_mult * total_mult)

    return GemDpsSimulation(
        skill=skill_name,
        gem_level=gem_level,
        links=links,
        base_damage=avg_base,
        damage_effectiveness=skill_data.damage_effectiveness,
        aps=skill_data.base_aps,
        total_multiplier=total_mult,
        estimated_dps=round(dps, 1),
        supports=[s[0] for s in supports[:links - 1]],
        multiplier_breakdown=multiplier_breakdown,
    )


def check_requirements(
    skill_name: str,
    gem_level: int = 20,
    str_attr: int = 0,
    dex_attr: int = 0,
    int_attr: int = 0,
) -> str:
    """Check if attribute requirements are met and report attribute gaps."""
    skill_data = SKILL_GEM_DATA.get(skill_name)
    if not skill_data:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_name.lower():
                skill_data = val
                skill_name = key
                break

    if not skill_data:
        return f"Skill '{skill_name}' not in database."

    # Attribute requirements scale with gem level
    level_factor = 1.0 + (gem_level - 1) * 0.05  # ~5% more req per level

    req_str = int(skill_data.str_req * level_factor)
    req_dex = int(skill_data.dex_req * level_factor)
    req_int = int(skill_data.int_req * level_factor)

    lines = [
        f"=== Attribute Requirements: {skill_name} (Level {gem_level}) ===",
        "",
        "Requirement   | You Have | Needed | Status",
        "--------------|----------|--------|-------",
    ]

    all_met = True
    for attr_name, req, have in [
        ("STR", req_str, str_attr),
        ("DEX", req_dex, dex_attr),
        ("INT", req_int, int_attr),
    ]:
        if req > 0:
            status = "✓" if have >= req else "✗ MISSING"
            if have < req:
                all_met = False
            lines.append(f"  {attr_name:12s} | {have:8d} | {req:6d} | {status}")

    if all_met:
        lines.append("\n✓ All requirements met.")
    else:
        lines.append(f"\n✗ Requirements not met. Need more attributes.")
        if req_str > str_attr:
            lines.append(f"  Short by {req_str - str_attr} STR — gear or passive tree")
        if req_dex > dex_attr:
            lines.append(f"  Short by {req_dex - dex_attr} DEX — gear or passive tree")
        if req_int > int_attr:
            lines.append(f"  Short by {req_int - int_attr} INT — gear or passive tree")

    return "\n".join(lines)


def optimize_links(
    skill_name: str,
    links: int = 5,
    gem_data: Optional[dict] = None,
    prefer_defense: bool = False,
) -> str:
    """Optimize support gem selection for a given number of links.

    Uses greedy algorithm: pick highest-scoring supports, then check
    for diminishing returns (too many "more damage" supports).
    """
    skill_lower = skill_name.lower().strip()
    skill_data = SKILL_GEM_DATA.get(skill_name)
    if not skill_data:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_lower:
                skill_data = val
                skill_name = key
                break

    if not skill_data:
        return f"Skill '{skill_name}' not in database. Use --tags to specify manually."

    if gem_data is None:
        gem_data = load_gem_data()

    tags = skill_data.tags
    all_supports = find_supports(tags, gem_data, max_results=20)

    # Categorize supports
    damage_supports: list[tuple[str, int, str, str]] = []
    utility_supports: list[tuple[str, int, str, str]] = []
    defense_supports: list[tuple[str, int, str, str]] = []

    high_damage_effects = {"more_damage", "more_projectiles", "penetration", "extra_use",
                           "added_damage", "impale"}

    for sup in all_supports:
        effect = sup[2]
        if effect in high_damage_effects:
            damage_supports.append(sup)
        elif effect in {"cost_conversion", "cost_reduction", "buff", "debuff"}:
            defense_supports.append(sup)
        else:
            utility_supports.append(sup)

    # Greedy selection: best damage first, then utility/defense
    selected: list[tuple[str, int, str, str]] = []
    # At most 4-5 damage supports to avoid diminishing returns
    max_damage = min(links - 1, 4)
    selected.extend(damage_supports[:max_damage])
    remaining = (links - 1) - len(selected)

    if prefer_defense and remaining > 0:
        selected.extend(defense_supports[:remaining])
        remaining = (links - 1) - len(selected)

    if remaining > 0:
        selected.extend(utility_supports[:remaining])

    # Simulate DPS
    sim = simulate_dps(skill_name, gem_level=20, links=links,
                       added_flat=0, increased_mod=0)

    lines = [
        f"=== Optimized {links}-Link Setup: {skill_name} ===",
        f"Gem tags: {', '.join(tags)}",
        "",
        f"{'#':3s} {'Gem':30s} {'Score':>6s} {'Effect Type':>20s}",
        f"{'-'*3} {'-'*30} {'-'*6} {'-'*20}",
    ]

    lines.append(f"  {'1':>2s} {skill_name + ' (Skill Gem)':30s} {'—':>6s} {'—':>20s}")

    for i, (name, score, effect, reason) in enumerate(selected[:links - 1], 2):
        lines.append(f"  {i:>2d} {name:30s} {score:>6d} {effect:>20s}")

    total_mult = 1.0
    for name, score, effect, reason in selected[:links - 1]:
        total_mult *= SUPPORT_MULTIPLIERS.get(effect, 1.05)

    lines.append(f"\nTotal multiplier: {total_mult:.2f}x")
    lines.append(f"Estimated DPS: {sim.estimated_dps:.0f}")

    # Diminishing returns warning
    damage_count = sum(1 for s in selected
                       if s[2] in {"more_damage", "increased_speed"})
    if damage_count > 4:
        lines.append(f"\n[NOTE] {damage_count} damage supports — diminishing returns likely."
                     f"\n       Consider replacing one with utility/defense.")

    return "\n".join(lines)


def compare_skills(
    skill_a: str,
    skill_b: str,
    gem_level: int = 20,
    links: int = 4,
) -> GemComparison:
    """Compare two skills for DPS and support compatibility."""
    sim_a = simulate_dps(skill_a, gem_level, links)
    sim_b = simulate_dps(skill_b, gem_level, links)

    data_a = SKILL_GEM_DATA.get(skill_a)
    data_b = SKILL_GEM_DATA.get(skill_b)
    if not data_a:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_a.lower():
                data_a = val
                skill_a = key
                break
    if not data_b:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_b.lower():
                data_b = val
                skill_b = key
                break

    tags_a = data_a.tags if data_a else []
    tags_b = data_b.tags if data_b else []
    tags_a_lower = [t.lower() for t in tags_a]
    tags_b_lower = [t.lower() for t in tags_b]
    shared = [t for t in tags_a if t.lower() in tags_b_lower]

    winner = skill_a if sim_a.estimated_dps >= sim_b.estimated_dps else skill_b
    ratio = max(sim_a.estimated_dps, sim_b.estimated_dps) / max(min(sim_a.estimated_dps, sim_b.estimated_dps), 1)

    return GemComparison(
        skill_a=skill_a, skill_b=skill_b,
        dps_a=sim_a.estimated_dps, dps_b=sim_b.estimated_dps,
        tags_a=tags_a, tags_b=tags_b,
        shared_tags=shared,
        winner=winner,
        dps_ratio=ratio,
    )


def synergy_matrix(skill_name: str, gem_data: Optional[dict] = None) -> str:
    """Display a support gem synergy matrix for a skill.

    Shows all compatible supports with scores, effects, and multipliers.
    """
    skill_lower = skill_name.lower().strip()
    skill_data = SKILL_GEM_DATA.get(skill_name)
    if not skill_data:
        for key, val in SKILL_GEM_DATA.items():
            if key.lower() == skill_lower:
                skill_data = val
                skill_name = key
                break

    if not skill_data:
        return f"Skill '{skill_name}' not in database."

    if gem_data is None:
        gem_data = load_gem_data()

    supports = find_supports(skill_data.tags, gem_data, max_results=50)

    lines = [
        f"=== Support Synergy Matrix: {skill_name} ===",
        f"Tags: {', '.join(skill_data.tags)}",
        "",
        f"{'Rank':>4s} {'Support Gem':30s} {'Score':>6s} {'DPS Mult':>8s} {'Effect':>20s}",
        f"{'─'*4} {'─'*30} {'─'*6} {'─'*8} {'─'*20}",
    ]

    for i, (name, score, effect, reason) in enumerate(supports[:20], 1):
        mult = SUPPORT_MULTIPLIERS.get(effect, 1.0)
        mult_str = f"{mult:.2f}x"
        lines.append(f"  {i:>3d} {name:30s} {score:>6d} {mult_str:>8s} {effect:>20s}")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Enhanced Gem Analyzer — DPS simulation, breakpoints, synergy",
    )
    parser.add_argument("--skill", help="Skill gem name (e.g. 'Explosive Grenade')")
    parser.add_argument("--level", type=int, default=20, help="Gem level (default: 20)")
    parser.add_argument("--links", type=int, default=4, help="Number of links (default: 4)")
    parser.add_argument("--quality", type=int, default=20, help="Gem quality (default: 20)")
    parser.add_argument("--weapon-damage", type=float, default=0,
                        help="Added weapon damage for simulation")
    parser.add_argument("--added-flat", type=float, default=0,
                        help="Added flat damage from gear")
    parser.add_argument("--increased", type=float, default=0,
                        help="Total % increased damage from tree+gear")
    parser.add_argument("--simulate-dps", action="store_true",
                        help="Run DPS simulation")
    parser.add_argument("--optimize-links", type=int, metavar="N",
                        help="Optimize support gems for N-link setup")
    parser.add_argument("--check-requirements", action="store_true",
                        help="Check attribute requirements")
    parser.add_argument("--str", type=int, default=0, dest="str_attr",
                        help="Strength attribute for requirement check")
    parser.add_argument("--dex", type=int, default=0, dest="dex_attr",
                        help="Dexterity attribute for requirement check")
    parser.add_argument("--int", type=int, default=0, dest="int_attr",
                        help="Intelligence attribute for requirement check")
    parser.add_argument("--compare", nargs=2, metavar=("SKILL_A", "SKILL_B"),
                        help="Compare two skills")
    parser.add_argument("--matrix", action="store_true",
                        help="Show full support synergy matrix")

    args = parser.parse_args()

    if not args.skill and not args.compare:
        parser.print_help()
        print("\nExamples:")
        print("  python gem_analyzer.py --skill 'Explosive Grenade' --simulate-dps --links 5")
        print("  python gem_analyzer.py --skill 'Spark' --optimize-links 5")
        print("  python gem_analyzer.py --skill 'Fireball' --matrix")
        print("  python gem_analyzer.py --compare 'Spark' 'Arc'")
        print("  python gem_analyzer.py --skill 'Earthquake' --check-requirements --str 150 --dex 70 --int 60")
        return

    if args.compare:
        comp = compare_skills(args.compare[0], args.compare[1],
                              args.level, args.links)
        print(comp.format())
        return

    if args.optimize_links:
        print(optimize_links(args.skill, args.optimize_links))
        return

    if args.matrix:
        print(synergy_matrix(args.skill))
        return

    if args.check_requirements:
        print(check_requirements(args.skill, args.level,
                                 args.str_attr, args.dex_attr, args.int_attr))
        return

    if args.simulate_dps or True:  # default action
        sim = simulate_dps(
            args.skill, args.level, args.links, args.quality,
            weapon_damage=args.weapon_damage,
            added_flat=args.added_flat,
            increased_mod=args.increased,
        )
        print(sim.format())


if __name__ == "__main__":
    cli()
