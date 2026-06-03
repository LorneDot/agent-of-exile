#!/usr/bin/env python3
"""PoE2 Skill Tree Router.

Given a class and a list of target notable/keystone node IDs, finds the
shortest connected path through the passive tree and suggests optimal
allocation order.

Algorithm: repeated BFS — start from the class root, find the nearest
target node, add all nodes on the path, repeat until all targets reached.

Usage:
    python route_tree.py --class Mercenary --targets 58714 29514 65468 17882
    python route_tree.py --class Witch --targets 50459 47175 --level 80 --budget
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
    """Build an undirected adjacency graph from node out/in fields.

    Graph keys are string node IDs. Values are lists of connected node IDs.
    """
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
    """Find the root node for a class.

    Strategy: look at the class's overridePairs to find the root,
    or find ascendancy start nodes for that class.
    """
    # First try: find ascendancy start nodes
    for nid, node in nodes.items():
        if node.get("isAscendancyStart"):
            ascendancy_id = node.get("ascendancyId", "")
            # ascendancyId like "Witch1" — match against class prefix
            # Map class names to ascendancy prefixes
            asc_map = {
                "Witch": "Witch", "Warrior": "Warrior", "Ranger": "Ranger",
                "Sorceress": "Sorceress", "Mercenary": "Mercenary",
                "Monk": "Monk", "Huntress": "Huntress", "Druid": "Druid",
                "Marauder": "Marauder", "Duelist": "Duelist",
                "Shadow": "Shadow", "Templar": "Templar",
            }
            prefix = asc_map.get(class_name, class_name)
            if ascendancy_id.startswith(prefix):
                return nid

    # Second try: any node connected to "root" that's in the class area
    root_connections = nodes.get("root", {}).get("out", [])
    for conn_id in root_connections:
        conn_id = str(conn_id)
        if conn_id in nodes:
            return conn_id

    return "root"


# ============================================================
# Pathfinding
# ============================================================

def bfs_path(graph: dict[str, list[str]], start: str, targets: set[str]) -> tuple[Optional[str], list[str]]:
    """Find the shortest path from start to the nearest target.

    Returns (target_id, path_list) where path includes start and target.
    Returns (None, []) if no target is reachable.
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


def route_tree(
    nodes: dict,
    class_name: str,
    target_ids: list[str],
) -> tuple[list[str], list[tuple[str, float, str]]]:
    """Route through the tree to reach all targets.

    Returns:
      - all_nodes: complete ordered list of all node IDs in the path
      - order: list of (node_id, impact_score, reason) for allocation priority
    """
    graph = build_graph(nodes)
    root = find_class_root(nodes, class_name)

    remaining = set(target_ids)
    # Remove any that don't exist
    remaining = {t for t in remaining if t in nodes}
    missing = [t for t in target_ids if t not in nodes]
    if missing:
        print(f"Warning: {len(missing)} target nodes not found in tree: {missing}",
              file=sys.stderr)

    all_path_nodes: list[str] = []
    order: list[tuple[str, float, str]] = []

    current_frontier = [root]

    while remaining and current_frontier:
        # Find nearest target from any frontier node
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

        # Add new nodes to the path (skip duplicates)
        for nid in best_path:
            if nid not in all_path_nodes:
                all_path_nodes.append(nid)

        remaining.remove(best_target)

        # Score the target for ordering priority
        score = score_node(nodes, best_target, best_dist)
        reason = reason_for_node(nodes, best_target)
        order.append((best_target, score, reason))

        # Update frontier to all allocated nodes
        current_frontier = list(all_path_nodes)

    if remaining:
        print(f"Warning: {len(remaining)} targets unreachable: {remaining}",
              file=sys.stderr)

    return all_path_nodes, order


# ============================================================
# Node scoring for allocation priority
# ============================================================

def score_node(nodes: dict, node_id: str, travel_cost: int) -> float:
    """Score a node for allocation priority. Higher = take earlier.

    Factors:
    - Keystones are highest priority (build-defining)
    - Notables are medium priority
    - Lower travel cost = higher priority (more efficient)
    - Jewel sockets get a boost
    """
    node = nodes.get(node_id, {})
    base = 1.0

    if node.get("isKeystone"):
        base = 10.0
    elif node.get("isNotable"):
        base = 5.0
    elif node.get("isJewelSocket"):
        base = 4.0

    # Efficiency bonus: closer nodes score higher
    if travel_cost > 0:
        base *= (10.0 / travel_cost)

    return round(base, 2)


def reason_for_node(nodes: dict, node_id: str) -> str:
    """Human-readable reason for a node's priority."""
    node = nodes.get(node_id, {})
    name = node.get("name", node_id)

    if node.get("isKeystone"):
        return f"KEYSTONE: {name} — build-defining, take immediately when reachable"
    elif node.get("isNotable"):
        stats = node.get("stats", [])
        if stats:
            return f"Notable: {name} — {stats[0][:80]}"
        return f"Notable: {name}"
    elif node.get("isJewelSocket"):
        return f"Jewel Socket — slot a jewel for flexible stats"
    return f"Travel node: {name}"


# ============================================================
# Output formatting
# ============================================================

def format_route(
    all_nodes: list[str],
    order: list[tuple[str, float, str]],
    nodes: dict,
    class_name: str,
    level: int = 80,
    show_budget: bool = True,
) -> str:
    """Format the routing result as a readable build plan."""
    available = (level - 1) + 24  # levels + quests

    lines = [
        f"=== {class_name} Skill Tree Route ===",
        f"Level {level}: {available} points available",
        f"Total nodes in path: {len(all_nodes)}",
    ]

    if show_budget and len(all_nodes) > available:
        lines.append(f"⚠️  OVER BUDGET by {len(all_nodes) - available} points!")
    elif show_budget:
        lines.append(f"✓ {available - len(all_nodes)} points remaining")

    lines.extend(["", "--- Allocation Order (highest priority first) ---", ""])

    for i, (nid, score, reason) in enumerate(order, 1):
        node = nodes.get(nid, {})
        name = node.get("name", nid)
        lines.append(f"  {i:2d}. [{nid}] {name} (score: {score})")
        lines.append(f"      {reason}")

    lines.extend(["", "--- Complete Node List ---", ""])
    # Group by category
    notables = [n for n in all_nodes if nodes.get(n, {}).get("isNotable")]
    keystones = [n for n in all_nodes if nodes.get(n, {}).get("isKeystone")]
    jewels = [n for n in all_nodes if nodes.get(n, {}).get("isJewelSocket")]
    travel = [n for n in all_nodes
              if n not in set(notables + keystones + jewels)]

    lines.append(f"Keystones ({len(keystones)}): {', '.join(keystones)}")
    lines.append(f"Notables ({len(notables)}): {', '.join(notables)}")
    lines.append(f"Jewel Sockets ({len(jewels)}): {', '.join(jewels)}")
    lines.append(f"Travel nodes ({len(travel)}): {len(travel)} nodes")

    return "\n".join(lines)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Route through the PoE2 passive tree to reach target nodes"
    )
    parser.add_argument("--class", dest="class_name", required=True,
                        help="Class name (e.g., Mercenary, Witch)")
    parser.add_argument("--targets", nargs="+", required=True,
                        help="Target node IDs to reach")
    parser.add_argument("--level", type=int, default=80,
                        help="Target level (default: 80)")
    parser.add_argument("--budget", action="store_true",
                        help="Show point budget")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    data = json.loads(CACHE_FILE.read_text())
    nodes = data["nodes"]

    all_nodes, order = route_tree(nodes, args.class_name, args.targets)

    if args.json:
        result = {
            "class": args.class_name,
            "level": args.level,
            "available_points": (args.level - 1) + 24,
            "total_allocated": len(all_nodes),
            "nodes": all_nodes,
            "order": [{"id": nid, "score": score, "reason": reason}
                      for nid, score, reason in order],
        }
        print(json.dumps(result, indent=2))
    else:
        print(format_route(all_nodes, order, nodes, args.class_name,
                          args.level, args.budget))


if __name__ == "__main__":
    cli()
