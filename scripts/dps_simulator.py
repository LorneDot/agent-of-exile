#!/usr/bin/env python3
"""PoE2 Enhanced DPS Simulator.

Extends gem_analyzer.py with:
- Aura/buff calculations (Heralds, auras, buffs)
- Monster resistance estimation per map tier
- Charge damage bonuses (frenzy, power, endurance)
- Conditional damage modifiers (full life, low life, etc.)
- Penetration and exposure effects
- Effective DPS vs boss content

Usage:
    python dps_simulator.py --skill "Explosive Grenade" --links 5 --auras "Herald of Ash" "Herald of Thunder"
    python dps_simulator.py --skill "Spark" --monster-tier 16 --charges frenzy:3 power:3
    python dps_simulator.py --skill "Fireball" --vs-pinnacle --full-setup
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from gem_analyzer import (
    simulate_dps, SKILL_GEM_DATA, SUPPORT_MULTIPLIERS,
    GemDpsSimulation,
)

# ============================================================
# Aura/Buff data
# ============================================================

@dataclass
class AuraEffect:
    """An active aura or buff's damage impact."""
    name: str
    effect_type: str  # "more_damage", "increased_damage", "added_flat", "penetration"
    value: float
    condition: str = ""  # e.g. "while affected by Herald"


# Common PoE2 auras and buffs
AURA_DATABASE: dict[str, AuraEffect] = {
    "Herald of Ash": AuraEffect(
        name="Herald of Ash",
        effect_type="more_damage",
        value=1.15,  # ~15% more fire damage as secondary explosion
        condition="Added fire explosion on kill",
    ),
    "Herald of Thunder": AuraEffect(
        name="Herald of Thunder",
        effect_type="added_flat",
        value=1.12,  # ~12% added lightning
        condition="Added lightning bolts on kill",
    ),
    "Herald of Ice": AuraEffect(
        name="Herald of Ice",
        effect_type="more_damage",
        value=1.10,  # ~10% more cold from shatter explosions
        condition="Added cold explosion on shatter",
    ),
    "Anger": AuraEffect(
        name="Anger",
        effect_type="added_flat",
        value=1.15,  # ~15% added fire damage
        condition="Adds flat fire damage to attacks",
    ),
    "Wrath": AuraEffect(
        name="Wrath",
        effect_type="added_flat",
        value=1.18,  # ~18% added lightning damage
        condition="Adds flat lightning damage to attacks",
    ),
    "Hatred": AuraEffect(
        name="Hatred",
        effect_type="more_damage",
        value=1.25,  # 25% phys as extra cold
        condition="Gain % of physical as extra cold",
    ),
    "Precision": AuraEffect(
        name="Precision",
        effect_type="increased_damage",
        value=1.05,  # ~5% DPS from accuracy/crit
        condition="Increased accuracy and crit chance",
    ),
    "Vitality": AuraEffect(
        name="Vitality",
        effect_type="increased_damage",
        value=1.0,  # Defensive only
        condition="Life regeneration — no direct DPS",
    ),
    "Clarity": AuraEffect(
        name="Clarity",
        effect_type="increased_damage",
        value=1.0,  # QoL only
        condition="Mana regeneration — no direct DPS",
    ),
    "Tempest Bell": AuraEffect(
        name="Tempest Bell",
        effect_type="more_damage",
        value=1.30,  # ~30% more when bell is active
        condition="Bell deals bonus damage on hit",
    ),
    "Flame Wall": AuraEffect(
        name="Flame Wall",
        effect_type="added_flat",
        value=1.20,  # ~20% added fire when projectiles pass through
        condition="Added fire to projectiles passing through wall",
    ),
    "Sniper's Mark": AuraEffect(
        name="Sniper's Mark",
        effect_type="more_damage",
        value=1.20,  # ~20% more from mark effect
        condition="Increases damage taken by marked enemy",
    ),
}


# ============================================================
# Monster resistance data
# ============================================================

@dataclass
class MonsterStats:
    """Estimated monster stats per content tier."""
    tier: str
    level: int
    elemental_res: float  # base resistance %
    chaos_res: float
    armour: float
    evasion: float
    life_multiplier: float  # relative to white mob


MONSTER_TIERS: dict[str, MonsterStats] = {
    "T1": MonsterStats("T1 Waystone", 68, 15, 10, 500, 500, 1.0),
    "T6": MonsterStats("T6 Waystone", 73, 20, 15, 1500, 1500, 2.0),
    "T11": MonsterStats("T11 Waystone", 78, 25, 20, 4000, 4000, 4.0),
    "T16": MonsterStats("T16 Waystone", 82, 30, 25, 8000, 8000, 8.0),
    "pinnacle": MonsterStats("Pinnacle Boss", 85, 40, 30, 20000, 15000, 50.0),
    "uber": MonsterStats("Uber Pinnacle", 85, 50, 40, 30000, 20000, 100.0),
}


# ============================================================
# Charge bonuses
# ============================================================

CHARGE_BONUSES = {
    "frenzy": {"more_damage": 0.04, "attack_speed": 0.04},  # per charge
    "power": {"crit_chance": 0.40, "crit_multiplier": 0.0},  # per charge (% increased)
    "endurance": {"more_damage": 0.0},  # defensive only per charge
}


# ============================================================
# Full DPS simulation
# ============================================================

@dataclass
class FullDpsResult:
    """Complete DPS simulation with all modifiers."""
    skill_name: str
    gem_level: int
    links: int

    # Base DPS
    base_dps: float

    # Modifiers
    support_multiplier: float
    aura_multiplier: float
    charge_multiplier: float
    conditional_multiplier: float
    penetration_factor: float

    # Target
    monster_tier: str
    monster_res: float

    # Results
    raw_dps: float
    effective_dps: float  # after monster resistance
    pinnacle_dps: float   # vs pinnacle boss

    # Breakdown
    active_auras: list[str]
    active_charges: dict[str, int]
    conditions: list[str]

    def format(self) -> str:
        lines = [
            f"╔══════════════════════════════════════════════╗",
            f"║  ENHANCED DPS SIMULATION: {self.skill_name}",
            f"╚══════════════════════════════════════════════╝",
            f"",
            f"  Gem Level: {self.gem_level} | Links: {self.links}",
            f"  Base DPS: {self.base_dps:.0f}",
            f"",
            f"--- Multipliers ---",
            f"  Support gems: {self.support_multiplier:.2f}x",
        ]
        if self.active_auras:
            lines.append(f"  Auras: {self.aura_multiplier:.2f}x")
            lines.append(f"    ({', '.join(self.active_auras)})")
        if sum(self.active_charges.values()) > 0:
            lines.append(f"  Charges: {self.charge_multiplier:.2f}x")
            for ct, count in self.active_charges.items():
                if count > 0:
                    lines.append(f"    {ct}: {count}")
        if self.conditional_multiplier != 1.0:
            lines.append(f"  Conditional: {self.conditional_multiplier:.2f}x")
            for cond in self.conditions:
                lines.append(f"    • {cond}")
        if self.penetration_factor != 1.0:
            lines.append(f"  Penetration: {self.penetration_factor:.2f}x")

        lines.append(f"\n  Raw DPS: {self.raw_dps:.0f}")
        lines.append(f"")
        lines.append(f"--- Effective DPS ---")
        lines.append(f"  vs {self.monster_tier}: {self.effective_dps:.0f}")
        lines.append(f"  vs Pinnacle: {self.pinnacle_dps:.0f}")

        return "\n".join(lines)


def simulate_full_dps(
    skill_name: str,
    gem_level: int = 20,
    links: int = 5,
    quality: int = 20,
    auras: Optional[list[str]] = None,
    charges: Optional[dict[str, int]] = None,
    penetration: float = 0,
    exposure: float = 0,
    monster_tier: str = "T16",
    conditional_damage: Optional[list[str]] = None,
) -> FullDpsResult:
    """Complete DPS simulation with all modifiers."""

    # Base simulation from gem_analyzer
    base_sim = simulate_dps(skill_name, gem_level, links, quality)
    base_dps = base_sim.estimated_dps

    # Support multiplier (from gem_analyzer)
    support_mult = base_sim.total_multiplier

    # Aura effects
    aura_mult = 1.0
    active_auras = auras or []
    for aura_name in active_auras:
        aura = AURA_DATABASE.get(aura_name)
        if aura and aura.effect_type == "more_damage":
            aura_mult *= aura.value
        elif aura and aura.effect_type == "added_flat":
            aura_mult *= aura.value  # Simplification

    # Charge effects
    charge_mult = 1.0
    active_charges = charges or {}
    for charge_type, count in active_charges.items():
        bonuses = CHARGE_BONUSES.get(charge_type, {})
        dmg_bonus = bonuses.get("more_damage", 0) * count
        charge_mult *= (1 + dmg_bonus)

    # Conditional damage
    cond_mult = 1.0
    conditions = conditional_damage or []
    for cond in conditions:
        if "low_life" in cond:
            cond_mult *= 1.30  # Pain Attunement style
        elif "full_life" in cond:
            cond_mult *= 1.15
        elif "shocked" in cond:
            cond_mult *= 1.20  # base shock
        elif "chilled" in cond:
            cond_mult *= 1.05
        elif "ignited" in cond:
            cond_mult *= 1.10

    # Total raw DPS
    total_mult = support_mult * aura_mult * charge_mult * cond_mult
    raw_dps = base_dps * total_mult

    # Penetration factor
    pen_total = penetration + exposure
    pen_factor = 1.0
    if pen_total > 0:
        # Penetration reduces effective resistance
        # Effective res = max(res - pen, -200) roughly
        pen_factor = 1.0 + min(pen_total / 100, 0.5)  # cap at +50%

    # Monster resistance
    monster = MONSTER_TIERS.get(monster_tier, MONSTER_TIERS["T16"])
    effective_res = max(monster.elemental_res - pen_total, -50)  # can go negative
    res_factor = 1 - (effective_res / 100)

    effective_dps = raw_dps * res_factor

    # Pinnacle DPS
    pinnacle = MONSTER_TIERS["pinnacle"]
    pinnacle_res = max(pinnacle.elemental_res - pen_total, -50)
    pinnacle_factor = 1 - (pinnacle_res / 100)
    pinnacle_dps = raw_dps * pinnacle_factor

    return FullDpsResult(
        skill_name=skill_name,
        gem_level=gem_level,
        links=links,
        base_dps=base_dps,
        support_multiplier=support_mult,
        aura_multiplier=aura_mult,
        charge_multiplier=charge_mult,
        conditional_multiplier=cond_mult,
        penetration_factor=pen_factor,
        monster_tier=monster.tier,
        monster_res=monster.elemental_res,
        raw_dps=raw_dps,
        effective_dps=effective_dps,
        pinnacle_dps=pinnacle_dps,
        active_auras=active_auras,
        active_charges=active_charges,
        conditions=conditions,
    )


def list_auras() -> str:
    """List all known auras and their effects."""
    lines = ["=== Auras & Buffs ===\n"]
    for name, aura in sorted(AURA_DATABASE.items()):
        lines.append(f"  {name}: {aura.effect_type} ({aura.value:.2f}x)")
        lines.append(f"    {aura.condition}")
    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Enhanced DPS Simulator — auras, charges, monster resists"
    )
    parser.add_argument("--skill", required=True,
                        help="Skill gem name")
    parser.add_argument("--level", type=int, default=20,
                        help="Gem level (default: 20)")
    parser.add_argument("--links", type=int, default=5,
                        help="Number of links (default: 5)")
    parser.add_argument("--quality", type=int, default=20,
                        help="Gem quality (default: 20)")
    parser.add_argument("--auras", nargs="+",
                        help="Active auras/buffs (e.g. 'Herald of Ash' 'Anger')")
    parser.add_argument("--charges",
                        help="Charges in format 'type:count' (e.g. 'frenzy:3,power:3')")
    parser.add_argument("--penetration", type=float, default=0,
                        help="Total elemental penetration %")
    parser.add_argument("--exposure", type=float, default=0,
                        help="Elemental exposure % (e.g. -15 from exposure)")
    parser.add_argument("--monster-tier", default="T16",
                        choices=["T1", "T6", "T11", "T16", "pinnacle", "uber"])
    parser.add_argument("--conditional", nargs="+",
                        help="Conditional modifiers ('low_life', 'shocked', etc.)")
    parser.add_argument("--list-auras", action="store_true",
                        help="List available auras and exit")

    args = parser.parse_args()

    if args.list_auras:
        print(list_auras())
        return

    # Parse charges
    charges: dict[str, int] = {}
    if args.charges:
        for pair in args.charges.split(","):
            ct, count = pair.strip().split(":")
            charges[ct.strip()] = int(count.strip())

    result = simulate_full_dps(
        skill_name=args.skill,
        gem_level=args.level,
        links=args.links,
        quality=args.quality,
        auras=args.auras,
        charges=charges,
        penetration=args.penetration,
        exposure=args.exposure,
        monster_tier=args.monster_tier,
        conditional_damage=args.conditional,
    )

    print(result.format())


if __name__ == "__main__":
    cli()
