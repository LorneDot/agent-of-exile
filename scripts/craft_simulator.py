#!/usr/bin/env python3
"""PoE2 Crafting Probability Simulator.

Simulates crafting outcomes using mod weights to estimate:
- Probability of hitting desired mods
- Expected currency cost
- Optimal crafting method for budget/goal
- Craft vs buy comparison

Usage:
    python craft_simulator.py --slot "Body Armour" --desired-mods life_flat fire_res cold_res --method essence
    python craft_simulator.py --slot "Ring" --desired-mods life_flat fire_res cold_res lightning_res --budget 100
    python craft_simulator.py --slot "Weapon" --type Crossbow --desired-mods increased_phys flat_phys attack_speed
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
WEIGHTS_CACHE = CACHE_DIR / "poe2-mod-weights.json"

from fetch_poe2_data import build_mod_weights, get_weights_for_slot


# ============================================================
# Crafting method definitions
# ============================================================

@dataclass
class CraftMethod:
    """A specific crafting approach with costs and outcomes."""
    name: str
    description: str
    base_cost: float  # in chaos orbs
    steps: list[str]
    num_prefixes_guaranteed: int = 0
    num_suffixes_guaranteed: int = 0
    total_mods: int = 4  # expected total mods on finished item


CRAFT_METHODS: dict[str, CraftMethod] = {
    "transmute_aug_regal": CraftMethod(
        name="Transmute → Aug → Regal",
        description="Basic crafting: magic → rare with 3-4 mods",
        base_cost=1.5,
        steps=[
            "Orb of Transmutation (normal → magic, 1 mod)",
            "Orb of Augmentation (add 2nd mod to magic)",
            "Regal Orb (magic → rare, adds 1 mod, total 3)",
        ],
        total_mods=3,
    ),
    "essence_regal": CraftMethod(
        name="Essence → Aug → Regal",
        description="Guaranteed mod type via essence, then aug + regal",
        base_cost=3,
        steps=[
            "Essence (guarantees 1 desired mod)",
            "Orb of Augmentation (adds 2nd mod)",
            "Regal Orb → rare (3 mods total)",
        ],
        num_prefixes_guaranteed=1,
        total_mods=3,
    ),
    "essence_regal_exalt": CraftMethod(
        name="Essence → Aug → Regal → Exalt",
        description="Essence guarantee + exalt slam for 4th mod",
        base_cost=5,
        steps=[
            "Essence (guarantees 1 desired mod)",
            "Orb of Augmentation",
            "Regal Orb → rare",
            "Exalted Orb (slam for 4th mod)",
        ],
        num_prefixes_guaranteed=1,
        total_mods=4,
    ),
    "essence_spam": CraftMethod(
        name="Essence spam",
        description="Repeated essence + scour until 3+ desired mods",
        base_cost=15,
        steps=[
            "Essence (guarantees 1 desired mod type)",
            "If 2nd mod is bad: Orb of Scouring + retry",
            "Repeat until 2+ desired mods as magic",
            "Regal Orb → Exalted Orb(s) to 4-6 mods",
        ],
        num_prefixes_guaranteed=1,
        total_mods=5,
    ),
    "greater_essence_spam": CraftMethod(
        name="Greater Essence spam",
        description="Greater Essence for T3+ guaranteed mod, scour bad results",
        base_cost=40,
        steps=[
            "Greater Essence (guarantees T3+ desired mod)",
            "Scour + retry if other mods are bad",
            "Regal → Exalt to 5 mods",
            "Craft last mod if bench available, or slam",
        ],
        num_prefixes_guaranteed=1,
        total_mods=5,
    ),
    "chaos_spam": CraftMethod(
        name="Chaos Orb spam",
        description="Repeated chaos rerolls on rare base",
        base_cost=50,
        steps=[
            "Alchemy Orb (normal → rare, 4 mods)",
            "Chaos Orb reroll until 3+ desired mods",
            "Exalted Orb(s) for 5th/6th mods",
        ],
        total_mods=5,
    ),
    "buy": CraftMethod(
        name="Trade (buy finished item)",
        description="Search trade for item with desired mods",
        base_cost=0,  # variable
        steps=["Search poe2 trade site with mod filters", "Buy best match in budget"],
        total_mods=6,
    ),
}


# ============================================================
# Probability calculations
# ============================================================

@dataclass
class CraftSimulation:
    """Simulation result for crafting a specific item."""
    slot: str
    desired_mods: list[str]
    method: CraftMethod
    total_weight: int
    target_weight: int
    hit_probability_per_roll: float  # per individual mod roll
    overall_success_probability: float  # all desired mods on one item
    expected_attempts: float
    estimated_total_cost: str
    alternatives: list[tuple[str, float, str]]  # (method_name, cost, verdict)

    def format(self) -> str:
        lines = [
            f"╔══════════════════════════════════════════════╗",
            f"║  CRAFTING SIMULATION: {self.slot}",
            f"╚══════════════════════════════════════════════╝",
            f"",
            f"  Desired mods: {', '.join(self.desired_mods)}",
            f"  Method: {self.method.name}",
            f"",
            f"  Mod pool: {self.target_weight}/{self.total_weight} weight "
            f"({self.hit_probability_per_roll*100:.1f}% per roll)",
            f"  Success chance: {self.overall_success_probability*100:.1f}%",
            f"  Expected attempts: {self.expected_attempts:.0f}",
            f"  Estimated cost: {self.estimated_total_cost}",
            f"",
            f"--- Steps ---",
        ]
        for step in self.method.steps:
            lines.append(f"  • {step}")

        if self.alternatives:
            lines.append(f"\n--- Alternative Methods ---")
            for method_name, cost, verdict in self.alternatives:
                lines.append(f"  • {method_name}: ~{cost:.0f}c — {verdict}")

        return "\n".join(lines)


def simulate_craft(
    slot: str,
    desired_mods: list[str],
    method_name: str = "essence_regal_exalt",
    target_ilvl: int = 82,
    weights_data: Optional[dict] = None,
) -> CraftSimulation:
    """Simulate crafting probability for given slot + mods + method."""
    if weights_data is None:
        weights_data = build_mod_weights()

    # Get all mods available for this slot with their weights
    all_mods = get_weights_for_slot(slot, weights_data)

    if not all_mods:
        # Try generic weapon
        all_mods = get_weights_for_slot("Weapon", weights_data)

    if not all_mods:
        return CraftSimulation(
            slot=slot, desired_mods=desired_mods,
            method=CRAFT_METHODS.get(method_name, CRAFT_METHODS["buy"]),
            total_weight=0, target_weight=0,
            hit_probability_per_roll=0, overall_success_probability=0,
            expected_attempts=0, estimated_total_cost="N/A",
            alternatives=[],
        )

    total_weight = sum(w for _, w in all_mods)
    target_weight = sum(w for m, w in all_mods if m in desired_mods)

    if total_weight == 0:
        hit_prob = 0
    else:
        hit_prob = target_weight / total_weight

    method = CRAFT_METHODS.get(method_name, CRAFT_METHODS["essence_regal_exalt"])

    # Calculate overall probability
    num_unguaranteed = len(desired_mods) - method.num_prefixes_guaranteed - method.num_suffixes_guaranteed
    num_unguaranteed = max(num_unguaranteed, 0)

    # Each unguaranteed mod has to hit from the pool
    # For essence methods: first mod is guaranteed, remaining roll randomly
    remaining_rolls = method.total_mods - method.num_prefixes_guaranteed - method.num_suffixes_guaranteed
    remaining_rolls = max(remaining_rolls, 1)

    # Simplified: need to hit num_unguaranteed desired mods in remaining_rolls rolls
    # Using binomial-style probability
    overall_prob = 1.0
    if num_unguaranteed > 0 and hit_prob > 0:
        # Probability that we get all num_unguaranteed hits in remaining_rolls rolls
        if num_unguaranteed <= remaining_rolls:
            # Each roll has hit_prob chance, need all num_unguaranteed
            # This is a simplification — assumes replacement (close enough for large pools)
            for i in range(num_unguaranteed):
                # Slightly worse odds each time since pool shrinks
                remaining_pool = total_weight - i * (total_weight / remaining_rolls)
                mod_prob = target_weight / max(remaining_pool, 1)
                overall_prob *= mod_prob
            overall_prob = min(overall_prob, 1.0)
        else:
            overall_prob = 0  # Can't fit all desired mods
    elif num_unguaranteed == 0:
        overall_prob = 1.0  # All guaranteed by essence

    expected_attempts = 1 / max(overall_prob, 0.001)
    total_cost = method.base_cost * expected_attempts

    # Generate alternatives
    alternatives: list[tuple[str, float, str]] = []
    for alt_name, alt_method in CRAFT_METHODS.items():
        if alt_name == method_name or alt_name == "buy":
            continue
        # Quick estimate for alternative
        alt_unguaranteed = len(desired_mods) - alt_method.num_prefixes_guaranteed
        alt_unguaranteed = max(alt_unguaranteed, 1)
        alt_prob = hit_prob ** alt_unguaranteed if hit_prob > 0 else 0
        alt_prob = min(alt_prob, 1.0)
        alt_attempts = 1 / max(alt_prob, 0.001)
        alt_cost = alt_method.base_cost * alt_attempts

        verdict = "cheaper" if alt_cost < total_cost else "more expensive"
        if alt_cost < total_cost * 0.5:
            verdict = "much cheaper"
        elif alt_cost > total_cost * 2:
            verdict = "much more expensive"

        alternatives.append((alt_method.name, alt_cost, verdict))

    alternatives.sort(key=lambda x: x[1])

    cost_str = f"~{total_cost:.0f}c" if total_cost < 100 else f"~{total_cost/100:.1f}div"
    if total_cost > 1000:
        cost_str += " (trade recommended)"

    return CraftSimulation(
        slot=slot,
        desired_mods=desired_mods,
        method=method,
        total_weight=total_weight,
        target_weight=target_weight,
        hit_probability_per_roll=hit_prob,
        overall_success_probability=overall_prob,
        expected_attempts=expected_attempts,
        estimated_total_cost=cost_str,
        alternatives=alternatives[:5],
    )


def craft_vs_buy(
    slot: str,
    desired_mods: list[str],
    budget: float = 100,
    weights_data: Optional[dict] = None,
) -> str:
    """Compare crafting cost vs buying from trade."""
    # Simulate best crafting method
    sim = simulate_craft(slot, desired_mods, "essence_regal_exalt", weights_data=weights_data)

    # Quick trade estimate based on mod count
    num_mods = len(desired_mods)
    trade_estimates = {
        1: "1-3c",
        2: "3-10c",
        3: "10-30c",
        4: "30-80c",
        5: "80-200c (1-2 div)",
        6: "2-10 div+",
    }
    trade_est = trade_estimates.get(num_mods, "varies")

    lines = [
        f"=== Craft vs Buy: {slot} ===",
        f"Desired mods: {', '.join(desired_mods)}",
        f"Budget: {budget}c",
        "",
        f"Crafting estimated cost: {sim.estimated_total_cost} "
        f"({sim.expected_attempts:.0f} attempts at {sim.method.base_cost:.0f}c each)",
        f"Trade estimated cost: {trade_est}",
        "",
    ]

    # Rough comparison
    if sim.expected_attempts * sim.method.base_cost > budget:
        lines.append("▶ VERDICT: TRADE — crafting likely exceeds budget")
        lines.append(f"  Use poe2 trade site to search for {slot} with these mods")
    elif sim.overall_success_probability < 0.05:
        lines.append("▶ VERDICT: TRADE — crafting success rate too low (<5%)")
    elif num_mods <= 3:
        lines.append("▶ VERDICT: CRAFT — 2-3 mod items are easy to craft")
    else:
        lines.append("▶ VERDICT: YOUR CHOICE — both viable")
        lines.append(f"  Crafting: guaranteed essence mod, gamble for rest")
        lines.append(f"  Trading: instant, but may not find exact rolls")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Crafting Probability Simulator"
    )
    parser.add_argument("--slot", required=True,
                        help="Equipment slot (e.g. 'Body Armour', 'Ring', 'Weapon')")
    parser.add_argument("--type", dest="weapon_type",
                        help="Weapon/armour type (e.g. 'Crossbow', 'Armour')")
    parser.add_argument("--desired-mods", nargs="+", required=True,
                        help="Desired mod IDs (e.g. life_flat fire_res cold_res)")
    parser.add_argument("--method", default="essence_regal_exalt",
                        choices=list(CRAFT_METHODS.keys()),
                        help="Crafting method to simulate")
    parser.add_argument("--budget", type=float, default=100,
                        help="Budget in chaos orbs (for craft vs buy)")
    parser.add_argument("--vs-buy", action="store_true",
                        help="Compare crafting vs buying from trade")
    parser.add_argument("--ilvl", type=int, default=82,
                        help="Target item level")

    args = parser.parse_args()

    # Load weights
    weights_data = build_mod_weights()

    # Map weapon type to slot
    slot = args.slot
    if args.weapon_type:
        slot = args.weapon_type

    if args.vs_buy:
        print(craft_vs_buy(slot, args.desired_mods, args.budget, weights_data))
    else:
        sim = simulate_craft(
            slot, args.desired_mods, args.method,
            args.ilvl, weights_data,
        )
        print(sim.format())


if __name__ == "__main__":
    cli()
