#!/usr/bin/env python3
"""PoE2 Skill Tree Router.

Given a class, ascendancy, and a list of target notable/keystone node IDs,
finds the shortest connected path through the passive tree, suggests optimal
allocation order, and enforces point budgets (regular + ascendancy).

Usage:
    python route_tree.py --class Mercenary --targets 58714 29514 --level 80
    python route_tree.py --class Mercenary --ascendancy "Gemling Legionnaire" --targets 58714 29514
    python route_tree.py --class Mercenary --targets ... --level 80 --trim
"""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path
from typing import Optional

CACHE_FILE = Path.home() / ".cache" / "poe2-theory-crafter" / "tree-data.json"

# ============================================================
# Graph building
# ============================================================

def build_graph(nodes: dict) -> dict[str, list[str]]:
    """Build an undirected adjacency graph from node out/in fields."""
    graph: dict[str, set[str]] = {}
    for nid, node in nodes.items():
        if nid not in graph:
            graph[nid] = set()
        for out_id in node.get("out", []):
            out_id = str(out_id)
            graph[nid].add(out_id)
            if out_id not in graph:
                graph[out_id] = set()
            graph[out_id].add(nid)
    return {k: list(v) for k, v in graph.items()}


def find_class_root(nodes: dict, class_name: str) -> str:
    """Find the root node for a class via its ascendancy start nodes."""
    asc_map = {
        "Witch": "Witch", "Warrior": "Warrior", "Ranger": "Ranger",
        "Sorceress": "Sorceress", "Mercenary": "Mercenary",
        "Monk": "Monk", "Huntress": "Huntress", "Druid": "Druid",
        "Marauder": "Marauder", "Duelist": "Duelist",
        "Shadow": "Shadow", "Templar": "Templar",
    }
    prefix = asc_map.get(class_name, class_name)
    for nid, node in nodes.items():
        if node.get("isAscendancyStart"):
            if (node.get("ascendancyId") or "").startswith(prefix):
                return nid

    # Fallback: first connection from "root"
    for conn_id in nodes.get("root", {}).get("out", []):
        conn_id = str(conn_id)
        if conn_id in nodes:
            return conn_id
    return "root"


def find_ascendancy_nodes(
    nodes: dict, ascendancy_name: str, classes: list[dict]
) -> tuple[Optional[str], list[str], int]:
    """Find ascendancy start and all notables for a given ascendancy.

    Returns (start_node_id, [notable_ids], max_ascendancy_points).
    """
    # Find the ascendancy's internal ID from classes data
    ascendancy_id = None
    for cls in classes:
        for asc in cls.get("ascendancies", []):
            if asc.get("name") == ascendancy_name:
                ascendancy_id = asc.get("id")
                break
        if ascendancy_id:
            break

    if not ascendancy_id:
        return None, [], 0

    # Find the ascendancy start node
    start_node = None
    for nid, node in nodes.items():
        if node.get("ascendancyId") == ascendancy_id and node.get(
            "isAscendancyStart"
        ):
            start_node = nid
            break

    # Collect all ascendancy notables
    asc_notables = []
    for nid, node in nodes.items():
        if node.get("ascendancyId") == ascendancy_id and node.get("isNotable"):
            asc_notables.append(nid)

    # Count how many ascendancy notables exist (typically 4 notables = 8 points)
    # PoE2: 4 ascendancy notables, each costs 2 points = 8 total
    max_points = len(asc_notables) * 2

    return start_node, asc_notables, max_points


# ============================================================
# Pathfinding
# ============================================================

def bfs_path(
    graph: dict[str, list[str]], start: str, targets: set[str]
) -> tuple[Optional[str], list[str]]:
    """Find the shortest path from start to the nearest target."""
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
    """Route through the tree to reach targets.

    Returns (all_path_nodes, scored_order, trimmed_targets).
    If max_points is set, trims lowest-scoring targets to fit budget.
    trimmed_targets are the targets that were cut.
    """
    remaining = set(target_ids)
    remaining = {t for t in remaining if t in nodes}

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
    if max_points is not None and len(all_path_nodes) > max_points:
        # Sort order by score ascending and trim from bottom
        order.sort(key=lambda x: x[1])  # lowest score first
        while len(all_path_nodes) > max_points and order:
            cut_nid, cut_score, _ = order.pop(0)
            trimmed.add(cut_nid)
            # Recompute path without this target
            all_path_nodes, order, _ = route_targets(
                graph, nodes, root,
                target_ids - trimmed,
                max_points=None,  # don't recurse trim
            )

        # Re-sort by score descending for display
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
    elif node.get("isJewelSocket"):
        base = 4.0

    if travel_cost > 0:
        base *= (10.0 / travel_cost)

    return round(base, 2)


def reason_for_node(nodes: dict, node_id: str) -> str:
    """Human-readable reason for a node's priority."""
    node = nodes.get(node_id, {})
    name = node.get("name", node_id)

    if node.get("isKeystone"):
        return f"KEYSTONE: {name} — build-defining"
    elif node.get("isNotable"):
        stats = node.get("stats", [])
        if stats:
            return f"Notable: {name} — {stats[0][:80]}"
        return f"Notable: {name}"
    elif node.get("isJewelSocket"):
        return f"Jewel Socket — flexible stats"
    return f"Travel node: {name}"


# ============================================================
# Output formatting
# ============================================================

def format_route(
    all_nodes: list[str],
    order: list[tuple[str, float, str]],
    nodes: dict,
    class_name: str,
    level: int,
    ascendancy_nodes: list[str] | None = None,
    ascendancy_order: list[tuple[str, float, str]] | None = None,
    ascendancy_name: str | None = None,
    ascendancy_max: int = 0,
    trimmed: set[str] | None = None,
    show_budget: bool = True,
) -> str:
    """Format the routing result as a readable build plan."""
    available = (level - 1) + 24
    ascendancy_available = 8  # max ascendancy points

    lines = [
        f"=== {class_name} Skill Tree Route ===",
    ]
    if ascendancy_name:
        lines.append(f"Ascendancy: {ascendancy_name} ({ascendancy_max} points available)")
    lines.append(f"Level {level}: {available} regular points + up to {ascendancy_available} ascendancy points")
    lines.append(f"Total regular nodes in path: {len(all_nodes)}")

    if trimmed:
        lines.append(f"✂️  Trimmed {len(trimmed)} targets to fit budget: {', '.join(sorted(trimmed))}")

    if show_budget and len(all_nodes) > available:
        lines.append(f"⚠️  OVER BUDGET by {len(all_nodes) - available} points!")
    elif show_budget:
        lines.append(f"✓ {available - len(all_nodes)} points remaining")

    # Ascendancy section
    if ascendancy_nodes and ascendancy_order:
        lines.extend([
            "",
            "--- Ascendancy Nodes (separate point pool, up to 8) ---",
            "",
        ])
        for i, (nid, score, reason) in enumerate(ascendancy_order, 1):
            node = nodes.get(nid, {})
            name = node.get("name", nid)
            lines.append(f"  A{i}. [{nid}] {name} (score: {score})")
            lines.append(f"      {reason}")
        asc_notables = [n for n in ascendancy_nodes if nodes.get(n, {}).get("isNotable")]
        asc_travel = [n for n in ascendancy_nodes if n not in set(asc_notables)]
        lines.append(f"\n  Ascendancy notables: {len(asc_notables)} ({len(asc_notables) * 2} points)")
        if asc_travel:
            lines.append(f"  Ascendancy travel: {len(asc_travel)} nodes")

    # Allocation order
    lines.extend(["", "--- Allocation Order (highest priority first) ---", ""])

    # Interleave ascendancy nodes into the order based on when you'd take them
    # Ascendancy trials unlock at specific points — typically you get 2 points
    # per trial, so take ascendancy notables as soon as available
    all_order = list(order)
    if ascendancy_order:
        # Insert ascendancy nodes at positions suggesting first trial
        insert_pos = min(15, len(all_order))
        for ao in reversed(ascendancy_order):
            all_order.insert(insert_pos, ao)

    for i, (nid, score, reason) in enumerate(all_order, 1):
        node = nodes.get(nid, {})
        name = node.get("name", nid)
        is_asc = " [ASCENDANCY]" if node.get("ascendancyId") else ""
        lines.append(f"  {i:2d}. [{nid}] {name}{is_asc} (score: {score})")
        lines.append(f"      {reason}")

    # Summary counts
    lines.extend(["", "--- Summary ---", ""])
    notables = [n for n in all_nodes if nodes.get(n, {}).get("isNotable")]
    keystones = [n for n in all_nodes if nodes.get(n, {}).get("isKeystone")]
    jewels = [n for n in all_nodes if nodes.get(n, {}).get("isJewelSocket")]
    travel = [n for n in all_nodes
              if n not in set(notables + keystones + jewels)]

    lines.append(f"Keystones ({len(keystones)}): {', '.join(keystones) if keystones else 'none'}")
    lines.append(f"Notables ({len(notables)}): {len(notables)} nodes")
    lines.append(f"Jewel Sockets ({len(jewels)}): {len(jewels)} nodes")
    lines.append(f"Travel nodes: {len(travel)}")
    lines.append(f"Total cost: {len(all_nodes)} regular + {ascendancy_max} ascendancy points")

    return "\n".join(lines)


def format_leveling_guide(
    order: list[tuple[str, float, str]],
    all_nodes: list[str],
    nodes: dict,
    level: int,
    ascendancy_order: list[tuple[str, float, str]] | None = None,
    ascendancy_name: str | None = None,
    ascendancy_max: int = 0,
    trimmed: set[str] | None = None,
) -> str:
    """Format a leveling guide splitting the allocation into point bands.

    Bands:
      Levels 1-20  (~27 pts): path to first build-enabling notable
      Levels 20-40 (~28 pts): path to 2nd-3rd key notables
      Levels 40-60 (~26 pts): damage scaling notables
      Levels 60-80 (~22 pts): defense, jewel sockets, cleanup
      Levels 80+  (remaining): remaining points + ascendancy cleanup
    """
    available = (level - 1) + 24

    # Build the full sequential allocation order (regular + ascendancy interleaved)
    all_order: list[tuple[str, float, str, bool]] = []
    # (node_id, score, reason, is_ascendancy)

    # Interleave ascendancy: take ascendancy notables around level 20-30
    # (first trial ~level 20-25, second ~40-50, third ~60-65, fourth ~75-80)
    reg_idx = 0
    asc_idx = 0
    asc_insert_points = [
        max(0, min(int(len(order) * 0.20), len(order))),   # ~20% through = first trial
        max(0, min(int(len(order) * 0.45), len(order))),   # ~45% through = second trial
        max(0, min(int(len(order) * 0.65), len(order))),   # ~65% through = third trial
        max(0, min(int(len(order) * 0.85), len(order))),   # ~85% through = fourth trial
    ]
    asc_targets = []
    if ascendancy_order:
        asc_targets = list(ascendancy_order)

    while reg_idx < len(order) or asc_idx < len(asc_targets):
        # Insert ascendancy nodes at the appropriate positions
        while asc_idx < len(asc_targets) and asc_idx < len(asc_insert_points) and reg_idx >= asc_insert_points[asc_idx]:
            nid, score, reason = asc_targets[asc_idx]
            all_order.append((nid, score, reason, True))
            asc_idx += 1
        if reg_idx < len(order):
            nid, score, reason = order[reg_idx]
            all_order.append((nid, score, reason, False))
            reg_idx += 1
    # Any remaining ascendancy
    while asc_idx < len(asc_targets):
        nid, score, reason = asc_targets[asc_idx]
        all_order.append((nid, score, reason, True))
        asc_idx += 1

    # Define level bands with approximate point budgets
    bands = [
        (1, 20, 27, "Path to first build-enabling notable"),
        (20, 40, 28, "Path to 2nd-3rd key notables"),
        (40, 60, 26, "Damage scaling notables"),
        (60, 80, 22, "Defense, jewel sockets, cleanup"),
    ]
    # Last band: 80+
    remaining_pts = available
    for _, _, pts, _ in bands:
        remaining_pts -= pts
    if remaining_pts < 0:
        remaining_pts = 0
    bands.append((80, level, remaining_pts, "Remaining points + ascendancy cleanup"))

    lines: list[str] = []
    lines.append("")
    lines.append("=== Leveling Guide ===")
    lines.append("")
    lines.append(f"Total regular point budget: {available}")
    lines.append(f"Total nodes to allocate: {len(all_nodes)}")
    if trimmed:
        trimmed_names = []
        for tid in sorted(trimmed):
            tn = nodes.get(tid, {})
            trimmed_names.append(tn.get("name", tid))
        lines.append(f"Trimmed (budget constrained): {', '.join(trimmed_names)}")
    lines.append("")

    # Split the ordered list into bands proportionally
    total_items = len(all_order)
    if total_items == 0:
        lines.append("(no nodes to allocate)")
        return "\n".join(lines)

    # Estimate average points per target (including travel nodes between them)
    # all_nodes includes travel + targets; order only has targets
    avg_pts_per_target = len(all_nodes) / len(order) if order else 1.0

    # Compute cumulative point proportions and split
    band_budgets = [b[2] for b in bands]
    total_budget = sum(band_budgets)
    item_idx = 0
    total_points_spent = 0
    ascendancy_points_spent = 0

    for band_idx, (band_start, band_end, band_pts, focus) in enumerate(bands):
        if band_start > level:
            break
        if item_idx >= total_items:
            break

        # Proportion of items in this band
        if band_idx < len(bands) - 1:
            proportion = band_pts / total_budget if total_budget > 0 else 0
            items_in_band = max(1, round(total_items * proportion))
            items_in_band = min(items_in_band, total_items - item_idx)
        else:
            items_in_band = total_items - item_idx

        if items_in_band <= 0:
            break

        band_items = all_order[item_idx:item_idx + items_in_band]
        item_idx += items_in_band

        # Count regular vs ascendancy
        band_reg = sum(1 for _, _, _, is_asc in band_items if not is_asc)
        band_asc = sum(1 for _, _, _, is_asc in band_items if is_asc)

        # Estimate actual points: each regular target implies ~avg_pts_per_target points
        est_band_pts = int(band_reg * avg_pts_per_target)
        total_points_spent += est_band_pts
        ascendancy_points_spent += band_asc * 2

        lines.append(f"--- Levels {band_start}-{band_end} (~{band_pts} regular points) ---")
        lines.append(f"Focus: {focus}")
        if ascendancy_name and band_asc > 0:
            lines.append(f"Ascendancy nodes in band: {band_asc} ({band_asc * 2} ascendancy points)")
        lines.append(f"Est. points spent: {total_points_spent} / {available} regular")
        if ascendancy_points_spent > 0:
            lines.append(f"Ascendancy points so far: {ascendancy_points_spent} / {ascendancy_max}")
        lines.append("")

        for i, (nid, score, reason, is_asc) in enumerate(band_items, 1):
            node = nodes.get(nid, {})
            name = node.get("name", nid)
            asc_tag = " [ASCENDANCY]" if is_asc else ""
            lines.append(f"  {i:2d}. [{nid}] {name}{asc_tag} (score: {score})")
            lines.append(f"      {reason}")

        lines.append("")

    # Add a summary line
    lines.append(f"---")
    lines.append(f"Total est. points: {total_points_spent} regular + {ascendancy_points_spent} ascendancy")
    lines.append(f"(Target nodes only; travel nodes shown in main route above)")

    return "\n".join(lines)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Route through the PoE2 passive tree to reach target nodes"
    )
    parser.add_argument("--class", dest="class_name", required=True,
                        help="Class name (e.g., Mercenary, Witch)")
    parser.add_argument("--ascendancy", default=None,
                        help="Ascendancy name (e.g., 'Gemling Legionnaire')")
    parser.add_argument("--targets", nargs="+", required=True,
                        help="Target node IDs to reach")
    parser.add_argument("--level", type=int, default=80,
                        help="Target level (default: 80)")
    parser.add_argument("--trim", action="store_true",
                        help="Auto-trim lowest-priority targets to fit budget")
    parser.add_argument("--budget", action="store_true",
                        help="Show point budget details")
    parser.add_argument("--leveling", action="store_true",
                        help="Append a leveling guide with point bands")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    data = json.loads(CACHE_FILE.read_text())
    nodes = data["nodes"]
    classes = data.get("classes", [])

    graph = build_graph(nodes)
    root = find_class_root(nodes, args.class_name)
    available = (args.level - 1) + 24
    max_points = available if args.trim else None

    # Regular tree routing
    all_nodes, order, trimmed = route_targets(
        graph, nodes, root, set(args.targets), max_points
    )

    # Ascendancy routing
    asc_nodes: list[str] = []
    asc_order: list[tuple[str, float, str]] = []
    asc_max = 0

    if args.ascendancy:
        asc_start, asc_targets, asc_max = find_ascendancy_nodes(
            nodes, args.ascendancy, classes
        )
        if asc_start and asc_targets:
            asc_graph = build_graph(nodes)
            asc_nodes, asc_order, _ = route_targets(
                asc_graph, nodes, asc_start, set(asc_targets)
            )

    if args.json:
        result = {
            "class": args.class_name,
            "ascendancy": args.ascendancy,
            "level": args.level,
            "available_points": available,
            "ascendancy_points": asc_max,
            "total_allocated": len(all_nodes),
            "nodes": all_nodes,
            "ascendancy_nodes": asc_nodes,
            "order": [{"id": nid, "score": score, "reason": reason}
                      for nid, score, reason in order],
            "ascendancy_order": [{"id": nid, "score": score, "reason": reason}
                                 for nid, score, reason in asc_order],
            "trimmed": sorted(trimmed) if trimmed else [],
        }
        if args.leveling:
            result["leveling_guide"] = format_leveling_guide(
                order, all_nodes, nodes, args.level,
                ascendancy_order=asc_order if asc_order else None,
                ascendancy_name=args.ascendancy,
                ascendancy_max=asc_max,
                trimmed=trimmed if trimmed else None,
            )
        print(json.dumps(result, indent=2))
    else:
        print(format_route(
            all_nodes, order, nodes, args.class_name, args.level,
            ascendancy_nodes=asc_nodes if asc_nodes else None,
            ascendancy_order=asc_order if asc_order else None,
            ascendancy_name=args.ascendancy,
            ascendancy_max=asc_max,
            trimmed=trimmed if trimmed else None,
            show_budget=args.budget or args.trim,
        ))
        if args.leveling:
            print(format_leveling_guide(
                order, all_nodes, nodes, args.level,
                ascendancy_order=asc_order if asc_order else None,
                ascendancy_name=args.ascendancy,
                ascendancy_max=asc_max,
                trimmed=trimmed if trimmed else None,
            ))


if __name__ == "__main__":
    cli()
