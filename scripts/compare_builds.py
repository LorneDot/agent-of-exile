#!/usr/bin/env python3
"""Compare two PoE2 passive tree builds side-by-side.

Routes both builds through the passive tree, computes stats, and produces
a comparison table covering EHP, DPS, defensive layers, node differences,
travel efficiency, and ascendancy advantage.

Usage:
    python compare_builds.py --class-a Mercenary --asc-a "Gemling Legionnaire" \\
        --class-b Mercenary --asc-b Witchhunter \\
        --targets "58714 29514 17882 33887" --level 80

    python compare_builds.py --class-a Witch --class-b Sorceress \\
        --targets-a "22541 57959" --targets-b "5571 34313" --level 80
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

# Import from sibling scripts
from route_tree import (
    build_graph,
    find_class_root,
    find_ascendancy_nodes,
    route_targets,
    CACHE_FILE,
)
from calc_stats import (
    compute_stats,
    analyze_defense,
    CLASS_BASE_ATTRS,
    BASE_LIFE,
    LIFE_PER_LEVEL,
    BASE_MANA,
    MANA_PER_LEVEL,
    LIFE_PER_STR,
    MANA_PER_INT,
    ACCURACY_PER_DEX,
    ELEMENTAL_RES_PENALTY,
    RES_CAP_BASE,
    estimate_armour_reduction,
)


# ============================================================
# Stat parser — extracts numerical values from PoE2 stat strings
# ============================================================

def parse_tree_stats(nodes: dict, node_ids: list[str]) -> dict:
    """Parse stat strings from a set of tree nodes into aggregated values.

    Handles PoE2 markup like:
      "5% increased [Strength]"
      "+8% to [Resistances|Fire Resistance]"
      "12% increased [Armour]"
      "Regenerate 0.5% of maximum Life per second"
      "+5 to any [Attributes|Attribute]"
    """
    result = {
        "str": 0, "dex": 0, "int": 0,
        "increased_str": 0, "increased_dex": 0, "increased_int": 0,
        "increased_life": 0, "flat_life": 0,
        "increased_mana": 0, "flat_mana": 0,
        "increased_es": 0, "flat_es": 0,
        "increased_armour": 0, "increased_evasion": 0,
        "fire_res": 0, "cold_res": 0, "lightning_res": 0, "chaos_res": 0,
        "all_res": 0,
        "increased_damage": 0, "increased_attack_damage": 0,
        "increased_spell_damage": 0, "increased_projectile_damage": 0,
        "increased_attack_speed": 0, "increased_cast_speed": 0,
        "increased_crit_chance": 0, "increased_crit_multi": 0,
        "life_regen_pct": 0, "mana_regen_pct": 0,
        "block_chance": 0, "spell_block": 0,
        "spell_suppression": 0,
        "accuracy_flat": 0, "increased_accuracy": 0,
        "notable_count": 0, "keystone_count": 0,
        "jewel_socket_count": 0, "travel_count": 0,
        "ascendancy_notable_count": 0,
    }

    for nid in node_ids:
        node = nodes.get(nid, {})
        if not node:
            continue

        # Count node types
        if node.get("isKeystone"):
            result["keystone_count"] += 1
        elif node.get("isNotable"):
            if node.get("ascendancyId"):
                result["ascendancy_notable_count"] += 1
            else:
                result["notable_count"] += 1
        elif node.get("isJewelSocket"):
            result["jewel_socket_count"] += 1
        else:
            result["travel_count"] += 1

        for stat in node.get("stats", []):
            _parse_one_stat(stat, result)

    # Convert increased_* percentages for Strength/Dexterity/Intelligence
    # into attribute points: if we have 5% increased [Strength], we add it
    # to increased_str (which is a multiplier, not flat)
    # (The actual formula multiplies base + flat by (1 + increased%), handled
    #  by the caller.)

    return result


def _parse_one_stat(stat: str, result: dict) -> None:
    """Parse a single PoE2 stat string and accumulate into result dict."""
    s = stat.strip()

    # --- Attribute flat bonuses ---
    # "+10 to [Strength]"
    m = re.search(r'\+(\d+)\s+to\s+\[Strength\]', s)
    if m:
        result["str"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)\s+to\s+\[Dexterity\]', s)
    if m:
        result["dex"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)\s+to\s+\[Intelligence\]', s)
    if m:
        result["int"] += int(m.group(1))
        return
    # "+5 to any [Attributes|Attribute]"
    m = re.search(r'\+(\d+)\s+to\s+any\s+\[Attributes\|Attribute\]', s)
    if m:
        val = int(m.group(1))
        # Split evenly among three attributes
        result["str"] += val // 3 + (1 if val % 3 > 0 else 0)
        result["dex"] += val // 3 + (1 if val % 3 > 1 else 0)
        result["int"] += val // 3
        return

    # --- Attribute percent bonuses ---
    # "5% increased [Strength]"
    m = re.search(r'(\d+)%\s+increased\s+\[Strength\]', s)
    if m:
        result["increased_str"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[Dexterity\]', s)
    if m:
        result["increased_dex"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[Intelligence\]', s)
    if m:
        result["increased_int"] += int(m.group(1))
        return

    # --- Life / Mana / ES ---
    m = re.search(r'(\d+)%\s+increased\s+maximum\s+[Ll]ife', s)
    if m:
        result["increased_life"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)\s+to\s+maximum\s+[Ll]ife', s)
    if m:
        result["flat_life"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+maximum\s+[Mm]ana', s)
    if m:
        result["increased_mana"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)\s+to\s+maximum\s+[Mm]ana', s)
    if m:
        result["flat_mana"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+maximum\s+\[?Energy\s*[Ss]hield', s)
    if m:
        result["increased_es"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)\s+to\s+maximum\s+\[?Energy\s*[Ss]hield', s)
    if m:
        result["flat_es"] += int(m.group(1))
        return

    # --- Armour / Evasion ---
    m = re.search(r'(\d+)%\s+increased\s+\[Armour\]', s)
    if m:
        result["increased_armour"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[Evasion\]', s)
    if m:
        result["increased_evasion"] += int(m.group(1))
        return

    # --- Resistances ---
    m = re.search(r'\+(\d+)%\s+to\s+\[Resistances\|Fire\s+Resistance\]', s)
    if m:
        result["fire_res"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)%\s+to\s+\[Resistances\|Cold\s+Resistance\]', s)
    if m:
        result["cold_res"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)%\s+to\s+\[Resistances\|Lightning\s+Resistance\]', s)
    if m:
        result["lightning_res"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)%\s+to\s+\[Resistances\|Chaos\s+Resistance\]', s)
    if m:
        result["chaos_res"] += int(m.group(1))
        return
    # "+X% to all Elemental Resistances"
    m = re.search(r'\+(\d+)%\s+to\s+all\s+[Ee]lemental\s+[Rr]esistances', s)
    if m:
        val = int(m.group(1))
        result["all_res"] += val
        result["fire_res"] += val
        result["cold_res"] += val
        result["lightning_res"] += val
        return
    # "+X% to all Resistances"
    m = re.search(r'\+(\d+)%\s+to\s+all\s+[Rr]esistances', s)
    if m:
        val = int(m.group(1))
        result["all_res"] += val
        result["fire_res"] += val
        result["cold_res"] += val
        result["lightning_res"] += val
        result["chaos_res"] += val
        return

    # --- Generic/untyped increased damage ---
    m = re.search(r'(\d+)%\s+increased\s+\[?[Dd]amage\]?', s)
    if m:
        val = int(m.group(1))
        # Only count generic damage; avoid double-counting typed damage
        if "Attack" not in s and "Spell" not in s and "Projectile" not in s:
            result["increased_damage"] += val
            return

    m = re.search(r'(\d+)%\s+increased\s+\[AttackDamage\|Attack\s+Damage\]', s)
    if m:
        result["increased_attack_damage"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[?[Ss]pell\s*[Dd]amage\]?', s)
    if m:
        result["increased_spell_damage"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[?[Pp]rojectile\s*[Dd]amage\]?', s)
    if m:
        result["increased_projectile_damage"] += int(m.group(1))
        return

    # --- Attack / Cast speed ---
    m = re.search(r'(\d+)%\s+increased\s+\[AttackSpeed\|Attack\s+Speed\]', s)
    if m:
        result["increased_attack_speed"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[?[Cc]ast\s*[Ss]peed\]?', s)
    if m:
        result["increased_cast_speed"] += int(m.group(1))
        return

    # --- Crit ---
    m = re.search(r'(\d+)%\s+increased\s+\[?[Cc]ritical\s*[Ss]trike\s*[Cc]hance\]?', s)
    if m:
        result["increased_crit_chance"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)%\s+to\s+\[?[Cc]ritical\s*[Ss]trike\s*[Cc]hance\]?', s)
    if m:
        result["increased_crit_chance"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[?[Cc]ritical\s*[Dd]amage\s*[Bb]onus\]?', s)
    if m:
        result["increased_crit_multi"] += int(m.group(1))
        return

    # --- Regen ---
    m = re.search(r'[Rr]egenerate\s+(\d+\.?\d*)%\s+of\s+maximum\s+[Ll]ife', s)
    if m:
        result["life_regen_pct"] += float(m.group(1))
        return
    m = re.search(r'[Rr]egenerate\s+(\d+\.?\d*)%\s+of\s+maximum\s+[Mm]ana', s)
    if m:
        result["mana_regen_pct"] += float(m.group(1))
        return

    # --- Block / Suppression ---
    m = re.search(r'\+(\d+)%\s+to\s+[Cc]hance\s+to\s+[Bb]lock', s)
    if m:
        result["block_chance"] += int(m.group(1))
        return
    m = re.search(r'\+(\d+)%\s+to\s+[Cc]hance\s+to\s+[Bb]lock\s+[Ss]pell', s)
    if m:
        result["spell_block"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+[Cc]hance\s+to\s+[Ss]uppress\s+[Ss]pell', s)
    if m:
        result["spell_suppression"] += int(m.group(1))
        return

    # --- Accuracy ---
    m = re.search(r'\+(\d+)\s+to\s+\[?[Aa]ccuracy\]?', s)
    if m:
        result["accuracy_flat"] += int(m.group(1))
        return
    m = re.search(r'(\d+)%\s+increased\s+\[?[Aa]ccuracy\]?', s)
    if m:
        result["increased_accuracy"] += int(m.group(1))
        return


# ============================================================
# Build routing — wraps route_tree for a single build
# ============================================================

class BuildRoute:
    """Result of routing a single build through the passive tree."""

    def __init__(
        self,
        class_name: str,
        ascendancy: Optional[str],
        level: int,
        all_nodes: list[str],
        order: list,
        asc_nodes: list[str],
        asc_order: list,
        asc_max: int,
        trimmed: set[str],
        name: str = "",
    ):
        self.class_name = class_name
        self.ascendancy = ascendancy
        self.level = level
        self.all_nodes = all_nodes
        self.order = order  # [(nid, score, reason), ...]
        self.asc_nodes = asc_nodes
        self.asc_order = asc_order
        self.asc_max = asc_max
        self.trimmed = trimmed
        self.name = name

        self.available = (level - 1) + 24

    @property
    def total_nodes(self) -> int:
        return len(self.all_nodes)

    @property
    def over_budget(self) -> bool:
        return self.total_nodes > self.available

    @property
    def points_remaining(self) -> int:
        return max(0, self.available - self.total_nodes)

    @property
    def points_short(self) -> int:
        return max(0, self.total_nodes - self.available)


def route_build(
    nodes: dict,
    classes: list[dict],
    class_name: str,
    ascendancy: Optional[str],
    target_ids: set[str],
    level: int = 80,
    trim: bool = False,
    name: str = "",
) -> BuildRoute:
    """Route a single build through the passive tree.

    Returns a BuildRoute, or raises ValueError if routing fails.
    """
    graph = build_graph(nodes)
    root = find_class_root(nodes, class_name)

    available = (level - 1) + 24
    max_points = available if trim else None

    all_nodes, order, trimmed = route_targets(
        graph, nodes, root, target_ids, max_points
    )

    if not all_nodes:
        raise ValueError(
            f"Failed to route {class_name}: no path found to targets {target_ids}"
        )

    # Ascendancy routing
    asc_nodes: list[str] = []
    asc_order: list = []
    asc_max = 0

    if ascendancy:
        asc_start, asc_targets, asc_max = find_ascendancy_nodes(
            nodes, ascendancy, classes
        )
        if asc_start and asc_targets:
            asc_graph = build_graph(nodes)
            asc_nodes, asc_order, _ = route_targets(
                asc_graph, nodes, asc_start, set(asc_targets)
            )

    return BuildRoute(
        class_name=class_name,
        ascendancy=ascendancy,
        level=level,
        all_nodes=all_nodes,
        order=order,
        asc_nodes=asc_nodes,
        asc_order=asc_order,
        asc_max=asc_max,
        trimmed=trimmed,
        name=name,
    )


# ============================================================
# Build spec construction — builds a calc_stats-compatible spec
# ============================================================

def build_spec_from_route(
    route: BuildRoute, nodes: dict, parsed: dict
) -> dict:
    """Build a calc_stats-compatible spec dict from a route result."""
    base_attrs = CLASS_BASE_ATTRS.get(
        route.class_name, {"str": 0, "dex": 0, "int": 0}
    )

    # Total attributes from base + tree
    tree_str = base_attrs["str"] + parsed["str"]
    tree_dex = base_attrs["dex"] + parsed["dex"]
    tree_int = base_attrs["int"] + parsed["int"]

    spec = {
        "level": route.level,
        "className": route.class_name,
        "ascendClassName": route.ascendancy or "",
        "treeAttributes": {
            "str": parsed["str"],
            "dex": parsed["dex"],
            "int": parsed["int"],
        },
        "increasedLifeFromTree": parsed["increased_life"],
        "flatLifeFromGear": 0,  # tree-only comparison
        "increasedManaFromTree": parsed["increased_mana"],
        "flatManaFromGear": 0,
        "flatESFromGear": 0,
        "increasedESFromTree": parsed["increased_es"],
        "armourFromGear": 0,
        "increasedArmourFromTree": parsed["increased_armour"],
        "evasionFromGear": 0,
        "increasedEvasionFromTree": parsed["increased_evasion"],
        "gearResistances": {},
        "treeResistances": {
            "fire": parsed["fire_res"],
            "cold": parsed["cold_res"],
            "lightning": parsed["lightning_res"],
            "chaos": parsed["chaos_res"],
        },
        "blockChance": parsed["block_chance"],
        "spellBlock": parsed["spell_block"],
        "spellSuppression": parsed["spell_suppression"],
        "lifeRegenPercent": parsed["life_regen_pct"],
        "manaRegenPercent": 1.75 + parsed["mana_regen_pct"],
        "estimatedMainSkillDPS": 0,  # requires skill info
        "averageHitDamage": 0,
        "attacksPerSecond": 1.0,
        "critChance": 5 + parsed["increased_crit_chance"] * 0.05,  # rough estimate
        "critMultiplier": 150 + parsed["increased_crit_multi"],
        "flatAccuracy": parsed["accuracy_flat"],
        "penetration": 0,
        "campaignProgress": "endgame",
    }

    return spec


# ============================================================
# Comparison logic
# ============================================================

def compute_defensive_layers(parsed: dict, stats) -> list[str]:
    """Identify which defensive layers a build has."""
    layers = []
    # From parsed stats, estimate armour/evasion thresholds
    if parsed.get("increased_armour", 0) > 50:
        layers.append("Armour scaling")
    elif parsed.get("increased_armour", 0) > 20:
        layers.append("Light armour")

    if parsed.get("increased_evasion", 0) > 50:
        layers.append("Evasion scaling")
    elif parsed.get("increased_evasion", 0) > 20:
        layers.append("Light evasion")

    if parsed.get("increased_es", 0) > 30:
        layers.append("ES scaling")

    if parsed.get("block_chance", 0) > 10:
        layers.append(f"Block ({parsed['block_chance']}%)")
    if parsed.get("spell_block", 0) > 10:
        layers.append(f"Spell Block ({parsed['spell_block']}%)")
    if parsed.get("spell_suppression", 0) > 20:
        layers.append(f"Spell Supp ({parsed['spell_suppression']}%)")

    if parsed.get("life_regen_pct", 0) > 2:
        layers.append(f"Life Regen ({parsed['life_regen_pct']:.1f}%)")

    # Check resistances
    res_total = (
        parsed.get("fire_res", 0) +
        parsed.get("cold_res", 0) +
        parsed.get("lightning_res", 0)
    )
    if res_total > 40:
        layers.append(f"Elemental Res ({res_total}% total)")

    if parsed.get("chaos_res", 0) > 10:
        layers.append(f"Chaos Res ({parsed['chaos_res']}%)")

    return layers if layers else ["None identified"]


def compare_builds(route_a: BuildRoute, route_b: BuildRoute, nodes: dict) -> str:
    """Generate a side-by-side comparison of two builds."""
    parsed_a = parse_tree_stats(nodes, route_a.all_nodes + route_a.asc_nodes)
    parsed_b = parse_tree_stats(nodes, route_b.all_nodes + route_b.asc_nodes)

    spec_a = build_spec_from_route(route_a, nodes, parsed_a)
    spec_b = build_spec_from_route(route_b, nodes, parsed_b)

    stats_a = compute_stats(spec_a)
    stats_b = compute_stats(spec_b)

    layers_a = compute_defensive_layers(parsed_a, stats_a)
    layers_b = compute_defensive_layers(parsed_b, stats_b)

    # Node differences
    nodes_a = set(route_a.all_nodes)
    nodes_b = set(route_b.all_nodes)
    only_a = nodes_a - nodes_b
    only_b = nodes_b - nodes_a
    common = nodes_a & nodes_b

    # Notable/keystone names unique to each
    notable_only_a = []
    notable_only_b = []
    for nid in only_a:
        node = nodes.get(nid, {})
        if node.get("isNotable") or node.get("isKeystone"):
            notable_only_a.append(node.get("name", nid))
    for nid in only_b:
        node = nodes.get(nid, {})
        if node.get("isNotable") or node.get("isKeystone"):
            notable_only_b.append(node.get("name", nid))

    # Ascendancy notables each takes
    asc_a_names = []
    asc_b_names = []
    for nid in route_a.asc_nodes:
        node = nodes.get(nid, {})
        if node.get("isNotable"):
            asc_a_names.append(node.get("name", nid))
    for nid in route_b.asc_nodes:
        node = nodes.get(nid, {})
        if node.get("isNotable"):
            asc_b_names.append(node.get("name", nid))

    asc_only_a = [n for n in asc_a_names if n not in asc_b_names]
    asc_only_b = [n for n in asc_b_names if n not in asc_a_names]
    asc_common = [n for n in asc_a_names if n in asc_b_names]

    # Travel efficiency
    travel_a = parsed_a["travel_count"]
    travel_b = parsed_b["travel_count"]
    total_a = route_a.total_nodes + len(route_a.asc_nodes)
    total_b = route_b.total_nodes + len(route_b.asc_nodes)
    eff_a = (total_a - travel_a) / max(total_a, 1) * 100
    eff_b = (total_b - travel_b) / max(total_b, 1) * 100

    # Build the output
    lines = []
    sep = "=" * 78

    lines.append(sep)
    lines.append("  BUILD COMPARISON")
    lines.append(sep)

    # Header row
    label_w = 24
    col_w = 26

    asc_a_label = route_a.ascendancy or "(no ascendancy)"
    asc_b_label = route_b.ascendancy or "(no ascendancy)"

    lines.append(
        f"  {'':{label_w}s} {'BUILD A':^{col_w}s} │ {'BUILD B':^{col_w}s}"
    )
    lines.append(
        f"  {'':{label_w}s} {'─' * col_w}─┼─{'─' * col_w}"
    )
    lines.append(
        f"  {'Class':{label_w}s} {route_a.class_name:{col_w}s} │ {route_b.class_name:{col_w}s}"
    )
    lines.append(
        f"  {'Ascendancy':{label_w}s} {asc_a_label:{col_w}s} │ {asc_b_label:{col_w}s}"
    )
    lines.append(
        f"  {'Level':{label_w}s} {str(route_a.level):{col_w}s} │ {str(route_b.level):{col_w}s}"
    )
    lines.append("")

    # --- EHP Section ---
    lines.append(f"  {'─' * 16} EHP & DEFENSE {'─' * 16}")
    lines.append(
        f"  {'Life (tree only)':{label_w}s} {stats_a.defence.life:>{col_w - 2}.0f}   │ {stats_b.defence.life:>{col_w - 2}.0f}"
    )
    lines.append(
        f"  {'Energy Shield':{label_w}s} {stats_a.defence.energy_shield:>{col_w - 2}.0f}   │ {stats_b.defence.energy_shield:>{col_w - 2}.0f}"
    )
    lines.append(
        f"  {'EHP (Life+ES)':{label_w}s} {stats_a.defence.ehp:>{col_w - 2}.0f}   │ {stats_b.defence.ehp:>{col_w - 2}.0f}"
    )
    ehp_ratio = stats_a.defence.ehp / max(stats_b.defence.ehp, 1)
    if ehp_ratio > 1.05:
        lines.append(f"  {'EHP Winner':{label_w}s} {'>>> BUILD A <<<':^{col_w}s} │ {'':^{col_w}s}")
    elif ehp_ratio < 0.95:
        lines.append(f"  {'EHP Winner':{label_w}s} {'':^{col_w}s} │ {'>>> BUILD B <<<':^{col_w}s}")
    else:
        lines.append(f"  {'EHP Winner':{label_w}s} {'≈ roughly equal':^{col_w}s} │ {'≈ roughly equal':^{col_w}s}")

    ehp_ele_a = stats_a.defence.ehp_vs_elemental
    ehp_ele_b = stats_b.defence.ehp_vs_elemental
    if ehp_ele_a != float("inf") and ehp_ele_b != float("inf"):
        lines.append(
            f"  {'EHP vs Elemental':{label_w}s} {ehp_ele_a:>{col_w - 2}.0f}   │ {ehp_ele_b:>{col_w - 2}.0f}"
        )
    lines.append("")

    # --- Attributes ---
    lines.append(f"  {'─' * 16} ATTRIBUTES {'─' * 16}")
    lines.append(
        f"  {'Strength':{label_w}s} {stats_a.attributes['str']:{col_w}d} │ {stats_b.attributes['str']:{col_w}d}"
    )
    lines.append(
        f"  {'Dexterity':{label_w}s} {stats_a.attributes['dex']:{col_w}d} │ {stats_b.attributes['dex']:{col_w}d}"
    )
    lines.append(
        f"  {'Intelligence':{label_w}s} {stats_a.attributes['int']:{col_w}d} │ {stats_b.attributes['int']:{col_w}d}"
    )

    # Show where attributes come from
    attr_a = f"base+{parsed_a['str']} / base+{parsed_a['dex']} / base+{parsed_a['int']}"
    attr_b = f"base+{parsed_b['str']} / base+{parsed_b['dex']} / base+{parsed_b['int']}"
    lines.append(
        f"  {'(tree only)':{label_w}s} {attr_a:{col_w}s} │ {attr_b:{col_w}s}"
    )
    lines.append("")

    # --- Defensive Layers ---
    lines.append(f"  {'─' * 16} DEFENSIVE LAYERS {'─' * 16}")
    max_layers = max(len(layers_a), len(layers_b))
    for i in range(max_layers):
        la = layers_a[i] if i < len(layers_a) else ""
        lb = layers_b[i] if i < len(layers_b) else ""
        label = "Defenses:" if i == 0 else ""
        lines.append(
            f"  {label:{label_w}s} {la:{col_w}s} │ {lb:{col_w}s}"
        )

    # Resistances from tree
    res_line_a = f"F{parsed_a['fire_res']} C{parsed_a['cold_res']} L{parsed_a['lightning_res']} Ch{parsed_a['chaos_res']}"
    res_line_b = f"F{parsed_b['fire_res']} C{parsed_b['cold_res']} L{parsed_b['lightning_res']} Ch{parsed_b['chaos_res']}"
    lines.append(
        f"  {'Resists (tree):':{label_w}s} {res_line_a:{col_w}s} │ {res_line_b:{col_w}s}"
    )
    lines.append("")

    # --- Offensive Stats ---
    lines.append(f"  {'─' * 16} OFFENSE (tree only) {'─' * 16}")
    lines.append(
        f"  {'Inc. Damage':{label_w}s} {parsed_a['increased_damage'] + parsed_a['increased_attack_damage']:{col_w}d}% │ {parsed_b['increased_damage'] + parsed_b['increased_attack_damage']:{col_w}d}%"
    )
    lines.append(
        f"  {'Inc. Spell Dmg':{label_w}s} {parsed_a['increased_spell_damage']:{col_w}d}% │ {parsed_b['increased_spell_damage']:{col_w}d}%"
    )
    lines.append(
        f"  {'Inc. Attack Spd':{label_w}s} {parsed_a['increased_attack_speed']:{col_w}d}% │ {parsed_b['increased_attack_speed']:{col_w}d}%"
    )
    lines.append(
        f"  {'Inc. Cast Spd':{label_w}s} {parsed_a['increased_cast_speed']:{col_w}d}% │ {parsed_b['increased_cast_speed']:{col_w}d}%"
    )
    lines.append(
        f"  {'Crit Chance':{label_w}s} {parsed_a['increased_crit_chance']:{col_w}d}% inc │ {parsed_b['increased_crit_chance']:{col_w}d}% inc"
    )
    lines.append(
        f"  {'Crit Multi':{label_w}s} {parsed_a['increased_crit_multi']:{col_w}d}% inc │ {parsed_b['increased_crit_multi']:{col_w}d}% inc"
    )
    lines.append("")

    # --- Node Counts & Travel Efficiency ---
    lines.append(f"  {'─' * 16} TRAVEL EFFICIENCY {'─' * 16}")
    lines.append(
        f"  {'Total Nodes':{label_w}s} {total_a:{col_w}d} │ {total_b:{col_w}d}"
    )
    lines.append(
        f"  {'Notables':{label_w}s} {parsed_a['notable_count']:{col_w}d} │ {parsed_b['notable_count']:{col_w}d}"
    )
    lines.append(
        f"  {'Keystones':{label_w}s} {parsed_a['keystone_count']:{col_w}d} │ {parsed_b['keystone_count']:{col_w}d}"
    )
    lines.append(
        f"  {'Jewel Sockets':{label_w}s} {parsed_a['jewel_socket_count']:{col_w}d} │ {parsed_b['jewel_socket_count']:{col_w}d}"
    )
    lines.append(
        f"  {'Travel Nodes':{label_w}s} {travel_a:{col_w}d} │ {travel_b:{col_w}d}"
    )
    lines.append(
        f"  {'Node Efficiency':{label_w}s} {eff_a:{col_w - 1}.0f}% │ {eff_b:{col_w - 1}.0f}%"
    )
    lines.append(
        f"  {'Path Length':{label_w}s} {route_a.total_nodes:{col_w}d} │ {route_b.total_nodes:{col_w}d}"
    )
    lines.append(
        f"  {'Points Available':{label_w}s} {route_a.available:{col_w}d} │ {route_b.available:{col_w}d}"
    )

    if route_a.over_budget:
        lines.append(
            f"  {'Budget':{label_w}s} {'⚠ OVER by ' + str(route_a.points_short):{col_w}s} │ {'':{col_w}s}"
        )
    else:
        lines.append(
            f"  {'Budget':{label_w}s} {str(route_a.points_remaining) + ' remaining':{col_w}s} │ {'':{col_w}s}"
        )
    if route_b.over_budget:
        lines.append(
            f"  {'':{label_w}s} {'':{col_w}s} │ {'⚠ OVER by ' + str(route_b.points_short):{col_w}s}"
        )
    else:
        lines.append(
            f"  {'':{label_w}s} {'':{col_w}s} │ {str(route_b.points_remaining) + ' remaining':{col_w}s}"
        )

    efficiency_winner = ""
    if eff_a > eff_b + 2:
        efficiency_winner = "BUILD A is more efficient"
    elif eff_b > eff_a + 2:
        efficiency_winner = "BUILD B is more efficient"
    else:
        efficiency_winner = "Similar efficiency"
    lines.append(
        f"  {'Winner:':{label_w}s} {efficiency_winner:{col_w}s} │ {'':{col_w}s}"
    )
    lines.append("")

    # --- Key Node Differences ---
    lines.append(f"  {'─' * 16} NODE DIFFERENCES {'─' * 16}")
    lines.append(
        f"  {'Common nodes:':{label_w}s} {len(common)} shared | {'':{col_w}s}"
    )
    lines.append(
        f"  {'Unique to A:':{label_w}s} {len(only_a)} nodes | {'':{col_w}s}"
    )
    lines.append(
        f"  {'Unique to B:':{label_w}s} {'':{col_w}s} | {len(only_b)} nodes"
    )

    if notable_only_a:
        lines.append("")
        lines.append(f"  Notable/Keystone nodes unique to BUILD A:")
        for n in notable_only_a[:15]:
            lines.append(f"    • {n}")
        if len(notable_only_a) > 15:
            lines.append(f"    ... and {len(notable_only_a) - 15} more")

    if notable_only_b:
        lines.append("")
        lines.append(f"  Notable/Keystone nodes unique to BUILD B:")
        for n in notable_only_b[:15]:
            lines.append(f"    • {n}")
        if len(notable_only_b) > 15:
            lines.append(f"    ... and {len(notable_only_b) - 15} more")

    if not notable_only_a and not notable_only_b:
        lines.append("")
        lines.append(f"  (All notable/keystone nodes are shared between both builds)")

    lines.append("")

    # --- Ascendancy Advantage ---
    lines.append(f"  {'─' * 16} ASCENDANCY ADVANTAGE {'─' * 16}")

    if route_a.ascendancy or route_b.ascendancy:
        lines.append(
            f"  {'Build A takes:':{label_w}s} {', '.join(asc_a_names) if asc_a_names else '(none)':{col_w}s} │ {'':{col_w}s}"
        )
        lines.append(
            f"  {'Build B takes:':{label_w}s} {'':{col_w}s} │ {', '.join(asc_b_names) if asc_b_names else '(none)':{col_w}s}"
        )

        if asc_common:
            lines.append(f"")
            lines.append(f"  Shared ascendancy nodes: {', '.join(asc_common)}")

        asc_summary = []
        if route_a.ascendancy != route_b.ascendancy:
            asc_summary.append(
                f"Different ascendancies: {route_a.ascendancy} vs {route_b.ascendancy}"
            )

        if asc_only_a:
            asc_summary.append(
                f"A gets exclusive: {', '.join(asc_only_a)}"
            )
        if asc_only_b:
            asc_summary.append(
                f"B gets exclusive: {', '.join(asc_only_b)}"
            )

        # Estimate ascendancy point usage
        asc_pts_a = parsed_a["ascendancy_notable_count"] * 2
        asc_pts_b = parsed_b["ascendancy_notable_count"] * 2
        lines.append(f"")
        lines.append(
            f"  {'Asc. Points Used:':{label_w}s} {asc_pts_a:{col_w}d} │ {asc_pts_b:{col_w}d}"
        )

        if asc_summary:
            lines.append(f"")
            lines.append(f"  Summary:")
            for s in asc_summary:
                lines.append(f"    • {s}")
    else:
        lines.append(f"  {'':{label_w}s} (no ascendancies specified)")

    lines.append("")
    lines.append(sep)
    lines.append("  LEGEND")
    lines.append(f"  All stats are TREE-ONLY (no gear, no skills).")
    lines.append(f"  DPS estimates require skill gem data — use calc_stats.py for full analysis.")
    lines.append(f"  Build A = {route_a.class_name}" +
                 (f" ({route_a.ascendancy})" if route_a.ascendancy else ""))
    lines.append(f"  Build B = {route_b.class_name}" +
                 (f" ({route_b.ascendancy})" if route_b.ascendancy else ""))
    lines.append(sep)

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare two PoE2 passive tree builds side-by-side"
    )
    # Build A
    parser.add_argument(
        "--class-a", dest="class_a", required=True,
        help="Class for build A (e.g., Mercenary, Witch)"
    )
    parser.add_argument(
        "--asc-a", dest="asc_a", default=None,
        help="Ascendancy for build A (e.g., 'Gemling Legionnaire')"
    )
    # Build B
    parser.add_argument(
        "--class-b", dest="class_b", required=True,
        help="Class for build B"
    )
    parser.add_argument(
        "--asc-b", dest="asc_b", default=None,
        help="Ascendancy for build B"
    )
    # Targets — shared or separate
    parser.add_argument(
        "--targets", nargs="+", default=None,
        help="Shared target node IDs for both builds"
    )
    parser.add_argument(
        "--targets-a", nargs="+", default=None,
        help="Target node IDs for build A (overrides --targets for A)"
    )
    parser.add_argument(
        "--targets-b", nargs="+", default=None,
        help="Target node IDs for build B (overrides --targets for B)"
    )
    parser.add_argument(
        "--level", type=int, default=80,
        help="Target level (default: 80)"
    )
    parser.add_argument(
        "--trim", action="store_true",
        help="Auto-trim lowest-priority targets to fit point budget"
    )
    args = parser.parse_args()

    # Resolve targets
    if args.targets_a is None:
        if args.targets is None:
            print("Error: must provide --targets or --targets-a/--targets-b",
                  file=sys.stderr)
            sys.exit(1)
        targets_a = set(args.targets)
    else:
        targets_a = set(args.targets_a)

    if args.targets_b is None:
        if args.targets is None:
            print("Error: must provide --targets or --targets-a/--targets-b",
                  file=sys.stderr)
            sys.exit(1)
        targets_b = set(args.targets)
    else:
        targets_b = set(args.targets_b)

    # Load tree data
    try:
        data = json.loads(CACHE_FILE.read_text())
    except FileNotFoundError:
        print(
            f"Error: tree data not found at {CACHE_FILE}. "
            f"Run fetch_tree.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid tree data JSON: {e}", file=sys.stderr)
        sys.exit(1)

    nodes = data["nodes"]
    classes = data.get("classes", [])

    # Route build A
    error_a = None
    route_a = None
    try:
        route_a = route_build(
            nodes, classes,
            class_name=args.class_a,
            ascendancy=args.asc_a,
            target_ids=targets_a,
            level=args.level,
            trim=args.trim,
            name="A",
        )
    except ValueError as e:
        error_a = str(e)

    # Route build B
    error_b = None
    route_b = None
    try:
        route_b = route_build(
            nodes, classes,
            class_name=args.class_b,
            ascendancy=args.asc_b,
            target_ids=targets_b,
            level=args.level,
            trim=args.trim,
            name="B",
        )
    except ValueError as e:
        error_b = str(e)

    # Handle errors
    if error_a and error_b:
        print(f"ERROR: Both builds failed to route.", file=sys.stderr)
        print(f"  Build A: {error_a}", file=sys.stderr)
        print(f"  Build B: {error_b}", file=sys.stderr)
        sys.exit(1)

    if error_a:
        print(f"WARNING: Build A ({args.class_a}) failed: {error_a}", file=sys.stderr)
        if route_b:
            print(f"\nShowing results for Build B only:\n", file=sys.stderr)
            parsed = parse_tree_stats(nodes, route_b.all_nodes + route_b.asc_nodes)
            spec = build_spec_from_route(route_b, nodes, parsed)
            stats = compute_stats(spec)
            print(stats.summary())
        sys.exit(1)

    if error_b:
        print(f"WARNING: Build B ({args.class_b}) failed: {error_b}", file=sys.stderr)
        if route_a:
            print(f"\nShowing results for Build A only:\n", file=sys.stderr)
            parsed = parse_tree_stats(nodes, route_a.all_nodes + route_a.asc_nodes)
            spec = build_spec_from_route(route_a, nodes, parsed)
            stats = compute_stats(spec)
            print(stats.summary())
        sys.exit(1)

    # Both routed successfully — compare
    assert route_a is not None and route_b is not None
    print(compare_builds(route_a, route_b, nodes))


if __name__ == "__main__":
    cli()
