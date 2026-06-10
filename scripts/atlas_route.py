#!/usr/bin/env python3
"""PoE Atlas Passive Tree Planner.

Given a strategy name or a list of target atlas notable/keystone node IDs,
finds the shortest connected path through the atlas passive tree, suggests
optimal allocation order, and enforces point budgets (from Waystone completion).

Fetches atlas tree data from grindinggear/atlastree-export on GitHub and
caches it locally.

Usage:
    python atlas_route.py --strategy expedition
    python atlas_route.py --strategy breach --level 30
    python atlas_route.py --targets "12345 67890" --level 40
    python atlas_route.py --strategy harvest --level 50 --json
"""

from __future__ import annotations

import json
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ============================================================
# Constants
# ============================================================

CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
CACHE_FILE = CACHE_DIR / "atlas-tree-data.json"
META_FILE = CACHE_DIR / "atlas-meta.json"

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "grindinggear/atlastree-export/master/data.json"
)

# Strategy → (display_name, [notable_ids], optional [keystone_ids])
# Each entry: list of atlas notable/keystone node IDs relevant to that strategy.
STRATEGIES: dict[str, tuple[str, list[str], list[str]]] = {
    "expedition": (
        "Expedition / Kalguur",
        [
            "29688",  # Hunt for Answers (+chance for Expedition)
            "30021",  # Ancient Decay (monsters spawn with missing life)
            "42276",  # Ancient Writings (extra Remnants, suffix mods)
            "55783",  # Buried Knowledge (logbook quant, runic markers)
            "42414",  # Distinguished Demolitionist (explosive radius/charges)
            "32761",  # Lucky Guess (Gwennen)
            "5718",   # Rather Not (Rog)
            "15639",  # Scratchin' up the Ground (Tujen)
            "4619",   # A Noble Quest (Dannig)
        ],
        [
            "13802",  # Extreme Archaeology (1 explosive, huge radius)
        ],
    ),
    "breach": (
        "Breach",
        [
            "49997",  # Broken Border (+chance for Breaches)
            "21345",  # Evolving Hives (more magic/rare monsters)
            "53006",  # Swelling Ranks (pack size, wombgifts)
            "60106",  # Violent Skirmish (faster breaches)
            "45606",  # Clawed Open (unstable breach duration)
            "18139",  # Fortified Dominance (hives → fortresses, boss dup)
            "22697",  # Fecund Colony (wombgifts from bosses)
            "20107",  # Massing Forces (extra unstable breaches)
            "51650",  # Adaptive Reaction (hive scaling)
            "9409",   # Protracted Siege (more hive waves)
        ],
        [
            "21908",  # Enemy at the Gates (always unstable breaches)
            "12551",  # Dimensional Foothold (always hives)
        ],
    ),
    "delirium": (
        "Delirium",
        [
            "42605",  # That Which You Seek (+chance for Mirrors)
            "2276",   # The Singular Eternity (fog dissipates slower)
            "15324",  # Descent Into Madness (fog scales faster)
            "11112",  # Compulsive Hoarder (extra reward types)
            "56199",  # Delusions of Persecution (bosses, splinters)
            "40355",  # Imagined Pursuits (reward type +count)
            "9972",   # Screaming Whispers (splinter stack size)
            "55126",  # Pathological (maps with delirium layers)
            "26152",  # Paranoid Fixation (Simulacrum splinters, Delirium rewards)
        ],
        [
            "44043",  # Unending Nightmare (fog never dissipates)
        ],
    ),
    "ritual": (
        "Ritual",
        [
            "16908",  # Sacred Lands (+chance for Rituals)
            "29457",  # Answered Appeals (cheaper defer, faster reappear)
            "48067",  # Flexible Dogma (cheaper rerolls)
            "54829",  # Profitable Prayers (extra rerolls)
            "41753",  # Sacrificial Due (blood-filled vessel drop)
            "37380",  # Occult Devotion (always 4 altars)
        ],
        [
            "1733",   # Arbitrary Tenets (randomized favour costs)
            "36064",  # Immutable Dogma (no rerolls, double tribute)
        ],
    ),
    "essence": (
        "Essence",
        [
            "9419",   # Prolific Essence (extra imprisoned monster)
            "26310",  # Crystal Lattice (extra essences)
            "55696",  # Amplified Energies (highest tier essences)
            "57336",  # Crystal Resonance (map boss inherits essences)
            "62161",  # Crystalline Carapaces (essence tablets)
        ],
        [],
    ),
    "harvest": (
        "Harvest",
        [
            "54874",  # Call of the Grove (+chance for Sacred Grove)
            "57163",  # Heart of the Grove (T4 plants, no wilt)
            "53175",  # Bountiful Harvest (exp, extra monsters)
            "39276",  # Bumper Crop (extra harvest)
            "45664",  # Doubling Season (duplicated lifeforce)
            "44049",  # Primal Drought (less blue, more yellow/purple)
            "27485",  # Wild Drought (less purple)
            "65089",  # Vivid Drought (less yellow)
        ],
        [
            "51310",  # Crop Rotation (tier upgrade on harvest)
        ],
    ),
    "bossing": (
        "Pinnacle Bosses",
        [
            "61358",  # Shaping the World (Waystone drops, tier upgrade)
            "18476",  # Higher Stakes (pinnacle boss fragment drops)
            "12651",  # Remnants of the Past (boss map sustain)
            "18900",  # Test of Will (pinnacle witness progress)
            "54499",  # Purifying Fire (Arbiter of Ash progress)
            "8182",   # Corrosive Touch (Breach boss progress)
            "55003",  # Dawn's Light (pinnacle boss rewards)
            "41053",  # Deep Hunger (Delirium boss progress)
            "37197",  # Flaming Word (Arbiter of Ash fragments)
            "28157",  # Rampant Growth (Expedition boss progress)
        ],
        [
            "34384",  # Destructive Play (additional pinnacle bosses)
            "48336",  # Cosmic Wrath (pinnacle boss difficulty)
            "33008",  # Eldritch Sight (pinnacle boss rewards)
        ],
    ),
    "general": (
        "General / All-Purpose",
        [
            "24609",  # Shaping the Mountains (rare monsters, Waystone tiers)
            "35608",  # Shaping the Skies (magic monsters, Waystone tiers)
            "34352",  # Significant Troves (precursor tablets from uniques)
            "14578",  # Skittering Swarms (more precursor tablets)
            "25273",  # Invasive Adversaries (difficult/rewarding packs)
            "53876",  # Chittering Champions (Waystone boss tablet drop)
            "64462",  # Amplified Artefacts (tablets from rares)
            "30954",  # Remarkable Relics (rarer precursor tablets)
            "34393",  # Mounting Modifiers (Waystone explicit mod effect)
            "30266",  # Multiplying Modifiers (Waystone mod effect)
            "64464",  # Awakened Depths (Abyss depths chance)
            "26020",  # Abyssal Army (Abyss XP/monsters)
        ],
        [
            "2493",   # Wellspring of Creation (less dmg, more life - safer)
            "36386",  # Dance of Destruction (more dmg, less life - faster)
        ],
    ),
}


# ============================================================
# Data fetching and caching
# ============================================================

def fetch_atlas_data(force: bool = False) -> dict:
    """Fetch atlas tree data from GGG GitHub, using cache unless force=True.

    Returns the parsed JSON as a dict. Raises RuntimeError on failure.
    """
    if not force and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # Cache corrupted, re-fetch

    import urllib.request
    import urllib.error

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching atlas tree data from GitHub...", file=sys.stderr)
    print(f"  {DATA_URL}", file=sys.stderr)

    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "atlas-route/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Failed to fetch atlas tree data from GitHub.\n"
            f"  URL: {DATA_URL}\n"
            f"  Error: {e}\n"
            f"\nCheck that grindinggear/atlastree-export exists and you have network access.\n"
            f"Try: curl -sI '{DATA_URL}'\n"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse atlas tree data (invalid JSON).\n"
            f"  URL: {DATA_URL}\n"
            f"  Error: {e}\n"
        ) from e

    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

    meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "url": DATA_URL,
        "version": data.get("tree", "unknown"),
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    return data


# ============================================================
# Graph building
# ============================================================

def build_graph(nodes: dict) -> dict[str, list[str]]:
    """Build an undirected adjacency graph from node out/in fields.

    Atlas tree nodes have 'out' (list of connected node IDs) and optionally
    'in' (reverse connections). We union both to build a complete undirected
    graph.
    """
    graph: dict[str, set[str]] = {}

    for nid, node in nodes.items():
        if nid not in graph:
            graph[nid] = set()

        for out_id in node.get("out", []):
            out_str = str(out_id)
            graph[nid].add(out_str)
            if out_str not in graph:
                graph[out_str] = set()
            graph[out_str].add(nid)

        for in_id in node.get("in", []):
            in_str = str(in_id)
            graph[nid].add(in_str)
            if in_str not in graph:
                graph[in_str] = set()
            graph[in_str].add(nid)

    return {k: list(v) for k, v in graph.items()}


def find_atlas_root(nodes: dict) -> str:
    """Find the root/starting node of the atlas tree."""
    # The atlas tree has a "root" node with only out connections
    if "root" in nodes:
        return "root"
    # Fallback: find a node with no 'in' but has 'out'
    for nid, node in nodes.items():
        if node.get("out") and not node.get("in"):
            return nid
    # Last resort: first node
    return next(iter(nodes))


# ============================================================
# Pathfinding
# ============================================================

def bfs_path(
    graph: dict[str, list[str]], start: str, targets: set[str]
) -> tuple[Optional[str], list[str]]:
    """Find the shortest path from start to the nearest target node.

    Returns (nearest_target_id, path_list_including_start_and_target).
    """
    if not targets:
        return None, []

    queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
    visited = {start}

    while queue:
        current, path = queue.popleft()
        if current in targets:
            return current, path
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None, []


def route_targets(
    graph: dict[str, list[str]],
    nodes: dict,
    root: str,
    target_ids: set[str],
    max_points: int | None = None,
) -> tuple[list[str], list[tuple[str, float, str]], set[str]]:
    """Greedy best-first routing through the atlas tree.

    Starting from root, repeatedly finds the nearest unvisited target,
    adds its path to the accumulated set, and repeats until all reachable
    targets are covered or the point budget is exhausted.

    Returns (all_path_nodes, scored_order, trimmed_targets).
    """
    remaining = {t for t in target_ids if t in nodes}
    all_path_nodes: list[str] = []
    order: list[tuple[str, float, str]] = []
    current_frontier = [root]

    while remaining and current_frontier:
        best_target: Optional[str] = None
        best_path: list[str] = []
        best_dist = float("inf")

        for fnode in current_frontier:
            target, path = bfs_path(graph, fnode, remaining)
            if target and len(path) < best_dist:
                best_dist = len(path)
                best_target = target
                best_path = path

        if best_target is None:
            break

        # Add newly discovered nodes to the total path
        for nid in best_path:
            if nid not in all_path_nodes:
                all_path_nodes.append(nid)

        remaining.remove(best_target)
        score = score_node(nodes, best_target, best_dist)
        reason = reason_for_node(nodes, best_target)
        order.append((best_target, score, reason))
        current_frontier = list(all_path_nodes)

    trimmed: set[str] = set()

    # Auto-trim: if budget constrained, cut lowest-scoring targets
    if max_points is not None:
        point_cost = len(all_path_nodes) - 1 if all_path_nodes and all_path_nodes[0] == "root" else len(all_path_nodes)
        if point_cost > max_points:
            order.sort(key=lambda x: x[1])  # lowest score first
            while True:
                current_cost = len(all_path_nodes) - 1 if all_path_nodes and all_path_nodes[0] == "root" else len(all_path_nodes)
                if current_cost <= max_points or not order:
                    break
                cut_nid, cut_score, _ = order.pop(0)
                trimmed.add(cut_nid)
                all_path_nodes, order, _ = route_targets(
                    graph, nodes, root,
                    target_ids - trimmed,
                    max_points=None,  # don't recurse trim
                )

            order.sort(key=lambda x: x[1], reverse=True)

    return all_path_nodes, order, trimmed


# ============================================================
# Node scoring
# ============================================================

def score_node(nodes: dict, node_id: str, travel_cost: int) -> float:
    """Score a node for allocation priority. Higher = take earlier."""
    node = nodes.get(node_id, {})
    base = 1.0

    if node.get("isKeystone"):
        base = 10.0
    elif node.get("isNotable"):
        base = 5.0

    if travel_cost > 0:
        base *= (8.0 / travel_cost)

    return round(base, 2)


def reason_for_node(nodes: dict, node_id: str) -> str:
    """Human-readable reason explaining a node's priority."""
    node = nodes.get(node_id, {})
    name = node.get("name", node_id)

    if node.get("isKeystone"):
        return f"KEYSTONE: {name} — build-defining atlas passive"
    elif node.get("isNotable"):
        stats = node.get("stats", [])
        if stats:
            return f"Notable: {name} — {stats[0][:100]}"
        return f"Notable: {name}"
    return f"Travel node: {name}"


# ============================================================
# Output formatting
# ============================================================

def format_route(
    all_nodes: list[str],
    order: list[tuple[str, float, str]],
    nodes: dict,
    strategy_name: str,
    point_budget: int,
    trimmed: set[str] | None = None,
) -> str:
    """Format the routing result as a readable atlas passive plan."""
    # The root node is the starting point and costs 0 points
    point_cost = len(all_nodes) - 1 if all_nodes and all_nodes[0] == "root" else len(all_nodes)

    lines = [
        f"=== Atlas Passive Tree Route ===",
        f"Strategy: {strategy_name}",
        f"Point budget: {point_budget} atlas passive points",
        f"Total point cost: {point_cost} (path includes {len(all_nodes)} nodes including root)",
    ]

    if trimmed:
        trimmed_names = []
        for tid in sorted(trimmed):
            tn = nodes.get(tid, {})
            trimmed_names.append(f"[{tid}] {tn.get('name', tid)}")
        lines.append(f"\u2702  Trimmed {len(trimmed)} targets to fit budget:")
        for tn in trimmed_names:
            lines.append(f"    - {tn}")

    if point_cost > point_budget:
        lines.append(f"\u26a0  OVER BUDGET by {point_cost - point_budget} points!")
        lines.append("    Consider reducing targets or using --level to increase budget.")
    else:
        lines.append(f"\u2713 {point_budget - point_cost} points remaining")

    # Allocation order
    lines.extend(["", "--- Allocation Order (highest priority first) ---", ""])

    for i, (nid, score, reason) in enumerate(order, 1):
        node = nodes.get(nid, {})
        name = node.get("name", nid)
        is_keystone = " [KEYSTONE]" if node.get("isKeystone") else ""
        is_notable = " [NOTABLE]" if node.get("isNotable") else ""
        tag = is_keystone if is_keystone else is_notable
        lines.append(f"  {i:2d}. [{nid}] {name}{tag} (score: {score})")
        lines.append(f"      {reason}")

    # Summary counts
    lines.extend(["", "--- Summary ---", ""])
    notables = [n for n in all_nodes if nodes.get(n, {}).get("isNotable")]
    keystones = [n for n in all_nodes if nodes.get(n, {}).get("isKeystone")]
    travel = [n for n in all_nodes if n not in set(notables + keystones) and n != "root"]

    lines.append(f"Keystones: {len(keystones)}")
    lines.append(f"Notables:  {len(notables)}")
    lines.append(f"Travel nodes: {len(travel)}")
    lines.append(f"Total point cost: {point_cost} (root not counted in allocation)")

    return "\n".join(lines)


def format_json_output(
    all_nodes: list[str],
    order: list[tuple[str, float, str]],
    nodes: dict,
    strategy_name: str,
    point_budget: int,
    trimmed: set[str] | None = None,
) -> str:
    """Format the routing result as JSON."""
    point_cost = len(all_nodes) - 1 if all_nodes and all_nodes[0] == "root" else len(all_nodes)
    result = {
        "strategy": strategy_name,
        "point_budget": point_budget,
        "total_point_cost": point_cost,
        "total_nodes_in_path": len(all_nodes),
        "over_budget": point_cost > point_budget,
        "remaining_points": max(0, point_budget - point_cost),
        "nodes": all_nodes,
        "order": [
            {"id": nid, "score": score, "reason": reason, "name": nodes.get(nid, {}).get("name", nid)}
            for nid, score, reason in order
        ],
        "summary": {
            "keystones": len([n for n in all_nodes if nodes.get(n, {}).get("isKeystone")]),
            "notables": len([n for n in all_nodes if nodes.get(n, {}).get("isNotable")]),
            "travel": len([n for n in all_nodes if not nodes.get(n, {}).get("isKeystone")
                           and not nodes.get(n, {}).get("isNotable") and n != "root"]),
        },
        "trimmed": sorted(trimmed) if trimmed else [],
    }
    return json.dumps(result, indent=2)


# ============================================================
# CLI
# ============================================================

def resolve_targets(
    strategy: str | None,
    targets_arg: list[str] | None,
    nodes: dict,
) -> tuple[str, set[str]]:
    """Resolve strategy name + optional targets into a final target set.

    Returns (display_name, set_of_node_ids).
    """
    if strategy:
        strategy_lower = strategy.lower()
        if strategy_lower not in STRATEGIES:
            available = ", ".join(sorted(STRATEGIES.keys()))
            print(
                f"Error: unknown strategy '{strategy}'.\n"
                f"Available strategies: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

        display_name, notable_ids, keystone_ids = STRATEGIES[strategy_lower]
        target_set = set(notable_ids)

        # Add keystones if they exist in the tree
        for kid in keystone_ids:
            if kid in nodes:
                target_set.add(kid)
            else:
                print(f"Warning: keystone {kid} not found in atlas tree", file=sys.stderr)

        # Filter out nodes not in the tree
        valid = {t for t in target_set if t in nodes}
        invalid = target_set - valid
        if invalid:
            print(f"Warning: {len(invalid)} strategy node(s) not found in atlas tree: {sorted(invalid)}",
                  file=sys.stderr)

        return display_name, valid

    elif targets_arg:
        target_set = set(targets_arg)
        valid = {t for t in target_set if t in nodes}
        invalid = target_set - valid
        if invalid:
            print(f"Warning: {len(invalid)} target(s) not found in atlas tree: {sorted(invalid)}",
                  file=sys.stderr)
        return "custom", valid

    else:
        print("Error: must specify --strategy or --targets", file=sys.stderr)
        sys.exit(1)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Plan your PoE Atlas Passive Tree route to reach target nodes"
    )
    parser.add_argument(
        "--strategy", default=None,
        help=(
            "Preset strategy: expedition, breach, delirium, ritual, "
            "essence, harvest, bossing, general"
        ),
    )
    parser.add_argument(
        "--targets", nargs="+", default=None,
        help="Specific atlas node IDs to target (space-separated)",
    )
    parser.add_argument(
        "--level", type=int, default=40,
        help="Number of atlas passive points available (default: 40)",
    )
    parser.add_argument(
        "--trim", action="store_true",
        help="Auto-trim lowest-priority targets to fit point budget",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--force-fetch", action="store_true",
        help="Force re-fetch of atlas tree data from GitHub",
    )
    parser.add_argument(
        "--list-strategies", action="store_true",
        help="List available strategies with their target nodes",
    )
    args = parser.parse_args()

    # List strategies mode
    if args.list_strategies:
        print("Available Atlas Strategies:\n")
        for key, (name, notables, keystones) in sorted(STRATEGIES.items()):
            print(f"  {key}: {name}")
            print(f"    Notable nodes: {len(notables)}")
            print(f"    Keystone nodes: {len(keystones)}")
            if notables:
                print(f"    IDs: {' '.join(notables)}")
            print()
        return

    # Validate
    if not args.strategy and not args.targets:
        parser.error("must specify --strategy or --targets")

    # Fetch data
    try:
        data = fetch_atlas_data(force=args.force_fetch)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    nodes = data.get("nodes", {})
    if not nodes:
        print("Error: atlas tree data contains no nodes", file=sys.stderr)
        sys.exit(1)

    # Resolve targets
    display_name, target_ids = resolve_targets(args.strategy, args.targets, nodes)

    if not target_ids:
        print("Error: no valid target nodes found", file=sys.stderr)
        sys.exit(1)

    # Build graph and route
    graph = build_graph(nodes)
    root = find_atlas_root(nodes)

    max_points = args.level if args.trim else None
    all_nodes, order, trimmed = route_targets(
        graph, nodes, root, target_ids, max_points
    )

    if not all_nodes:
        print("Error: could not find a path to any target nodes", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(format_json_output(
            all_nodes, order, nodes, display_name, args.level, trimmed
        ))
    else:
        print(format_route(
            all_nodes, order, nodes, display_name, args.level, trimmed
        ))


if __name__ == "__main__":
    cli()
