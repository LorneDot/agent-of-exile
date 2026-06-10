#!/usr/bin/env python3
"""PoE2 Build Optimizer.

Optimizes passive tree allocations:
- Cluster discovery: finds clusters of notable/keystone nodes
- Node swap simulation: "what if we drop X for Y?"
- Travel efficiency scoring: path quality metrics
- Budget reallocation: redistribute points for maximum value

Usage:
    python build_optimizer.py --class Mercenary --ascendancy "Gemling Legionnaire" --targets "58714 29514 17882"
    python build_optimizer.py --spec spec.json --find-clusters
    python build_optimizer.py --spec spec.json --what-if 58714 --replace-with 46123
    python build_optimizer.py --spec spec.json --optimize --budget 103
    python build_optimizer.py --spec spec.json --travel-report
"""

from __future__ import annotations

import json
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CACHE_FILE = Path.home() / ".cache" / "poe2-theory-crafter" / "tree-data.json"


# ============================================================
# Data structures
# ============================================================

@dataclass
class ClusterInfo:
    """A cluster of related passive nodes."""
    cluster_id: str
    notable_ids: list[str]
    travel_nodes: list[str]
    total_nodes: int
    centroid_id: str
    tags: list[str]
    value_score: float  # 0-100, how good this cluster is for the build

    def summary(self) -> str:
        return (f"Cluster '{self.cluster_id}': {len(self.notable_ids)} notables, "
                f"{len(self.travel_nodes)} travel, score={self.value_score:.0f}")


@dataclass
class NodeSwapResult:
    """Result of swapping one node allocation for another."""
    removed_id: str
    removed_name: str
    added_id: str
    added_name: str
    point_delta: int  # points saved (positive = saved points)
    travel_saved: int
    value_change: str  # description of what changed

    def format(self) -> str:
        sign = "+" if self.point_delta >= 0 else ""
        return (f"  {self.removed_name} ({self.removed_id}) → "
                f"{self.added_name} ({self.added_id}): "
                f"{sign}{self.point_delta} points, "
                f"travel saved: {self.travel_saved}, "
                f"{self.value_change}")


@dataclass
class TravelReport:
    """Travel efficiency analysis for a path."""
    total_nodes: int
    travel_nodes: int
    notable_nodes: int
    keystone_nodes: int
    travel_percentage: float
    notables_per_travel: float  # higher = more efficient routing
    dead_ends: int
    efficiency_grade: str

    def format(self) -> str:
        lines = [
            "=== Travel Efficiency Report ===",
            f"Total allocated: {self.total_nodes}",
            f"  Notables: {self.notable_nodes}",
            f"  Keystones: {self.keystone_nodes}",
            f"  Travel (stat nodes): {self.travel_nodes}",
            f"",
            f"Travel percentage: {self.travel_percentage:.1f}%",
            f"Notables per travel: {self.notables_per_travel:.2f}",
            f"Dead-end paths: {self.dead_ends}",
            f"Efficiency grade: {self.efficiency_grade}",
        ]

        if self.travel_percentage > 50:
            lines.append("\n[WARNING] High travel cost — consider more compact routing")
        if self.dead_ends > 2:
            lines.append(f"[WARNING] {self.dead_ends} dead-end paths — wasted travel points")
        if self.notables_per_travel < 0.5:
            lines.append("[WARNING] Low notable density — pathing through weak areas")

        return "\n".join(lines)


# ============================================================
# Tree loading
# ============================================================

def load_tree() -> dict | None:
    """Load passive tree data from cache."""
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE) as f:
        return json.load(f)


def build_graph(nodes: dict) -> dict[str, list[str]]:
    """Build undirected adjacency graph."""
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


def bfs_path(graph: dict[str, list[str]], start: str, end: str) -> list[str]:
    """BFS shortest path between two nodes."""
    if start == end:
        return [start]
    visited: set[str] = {start}
    parent: dict[str, str] = {}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                if neighbor == end:
                    # Reconstruct path
                    path = [end]
                    while path[-1] != start:
                        path.append(parent[path[-1]])
                    return list(reversed(path))
                queue.append(neighbor)
    return []


def get_node_name(nodes: dict, node_id: str) -> str:
    """Get a human-readable name for a node."""
    node = nodes.get(node_id, {})
    return node.get("name", node_id)


# ============================================================
# Cluster discovery
# ============================================================

def find_clusters(
    nodes: dict,
    graph: dict[str, list[str]],
    allocated_ids: list[str],
    max_cluster_distance: int = 3,
) -> list[ClusterInfo]:
    """Find clusters of notable/keystone nodes in allocated passives.

    A cluster is a group of notable nodes within max_cluster_distance
    travel nodes of each other.
    """
    allocated_set = set(allocated_ids)

    # Separate nodes by type
    notables: list[str] = []
    keystones: list[str] = []
    travel: list[str] = []

    for nid in allocated_ids:
        node = nodes.get(str(nid), {})
        if node.get("isKeystone"):
            keystones.append(str(nid))
        elif node.get("isNotable"):
            notables.append(str(nid))
        else:
            travel.append(str(nid))

    # Make a subgraph of allocated notables connected by short paths
    cluster_groups: list[set[str]] = []
    remaining = set(notables)

    while remaining:
        seed = remaining.pop()
        cluster = {seed}
        queue = deque([seed])
        in_cluster = {seed}

        while queue:
            current = queue.popleft()
            for n in notables:
                if n in in_cluster:
                    continue
                path = bfs_path(graph, current, n)
                # Count travel nodes in path (exclude endpoints)
                travel_in_path = [p for p in path[1:-1]
                                  if p in allocated_set or not nodes.get(p, {}).get("isNotable")]
                if len(travel_in_path) <= max_cluster_distance:
                    in_cluster.add(n)
                    cluster.add(n)
                    queue.append(n)
                    if n in remaining:
                        remaining.discard(n)

        cluster_groups.append(cluster)

    # Build ClusterInfo for each group
    clusters: list[ClusterInfo] = []
    for i, group in enumerate(cluster_groups):
        group_travel: list[str] = []
        for n1 in group:
            for n2 in group:
                if n1 >= n2:
                    continue
                path = bfs_path(graph, n1, n2)
                for p in range(len(path)):
                    pid = path[p]
                    if pid not in group and pid in allocated_set:
                        group_travel.append(pid)

        unique_travel = list(set(group_travel))
        notable_ids = sorted(group)

        # Collect tags from notable nodes
        tags: list[str] = []
        for nid in group:
            node = nodes.get(nid, {})
            node_tags = node.get("tags", [])
            tags.extend(node_tags)

        # Calculate centroid (node with minimum total distance to others)
        centroid = notable_ids[0]
        min_dist = float("inf")
        for nid in group:
            total_dist = sum(len(bfs_path(graph, nid, other))
                             for other in group if other != nid)
            if total_dist < min_dist:
                min_dist = total_dist
                centroid = nid

        # Score: notables per travel node (higher = more compact)
        score = len(notable_ids) / max(len(unique_travel), 1) * 25
        score = min(100, score)

        clusters.append(ClusterInfo(
            cluster_id=f"cluster_{i + 1}",
            notable_ids=notable_ids,
            travel_nodes=unique_travel,
            total_nodes=len(notable_ids) + len(unique_travel),
            centroid_id=centroid,
            tags=list(set(tags)),
            value_score=score,
        ))

    clusters.sort(key=lambda c: c.value_score, reverse=True)
    return clusters


# ============================================================
# Node swap simulation
# ============================================================

def simulate_swap(
    nodes: dict,
    graph: dict[str, list[str]],
    allocated_ids: list[str],
    remove_id: str,
    add_id: str,
    class_start: str,
) -> Optional[NodeSwapResult]:
    """Simulate removing one node and adding another.

    Calculates the point savings/loss, travel savings, and value change.
    """
    remove_id = str(remove_id)
    add_id = str(add_id)
    allocated_set = set(str(x) for x in allocated_ids)

    if remove_id not in allocated_set:
        return None
    if add_id in allocated_set:
        return None  # Already allocated
    if add_id not in nodes:
        return None

    remove_name = get_node_name(nodes, remove_id)
    add_name = get_node_name(nodes, add_id)

    # Calculate travel from class start to removed node
    path_to_removed = bfs_path(graph, class_start, remove_id)
    # Calculate travel to added node
    path_to_added = bfs_path(graph, class_start, add_id)

    travel_to_removed = len(path_to_removed) - 1
    travel_to_added = len(path_to_added) - 1

    travel_saved = travel_to_removed - travel_to_added

    # Check if removed node leaves other nodes disconnected
    remaining = allocated_set - {remove_id}
    # Quick check: does the removed node disconnect any other allocated nodes?
    # If removed node is on only path to other nodes, warn about it
    orphaned: list[str] = []
    if remaining:
        # Simple check: if any node's only path to class_start goes through remove_id
        for nid in remaining:
            alt_path = bfs_path(graph, class_start, nid)
            if remove_id in alt_path:
                # Check if there's another path
                skip_path: list[str] = []
                visited_skip: set[str] = {remove_id}
                alt_queue = deque([class_start])
                found = False
                parent_alt: dict[str, str] = {}
                while alt_queue and not found:
                    cur = alt_queue.popleft()
                    for nb in graph.get(cur, []):
                        if nb not in visited_skip:
                            visited_skip.add(nb)
                            parent_alt[nb] = cur
                            if nb == nid:
                                found = True
                                break
                            alt_queue.append(nb)
                if not found:
                    orphaned.append(get_node_name(nodes, nid))

    # Build result
    point_delta = 0  # 1 removed, 1 added = neutral for single node swap
    # But travel may change

    value_change_parts: list[str] = []
    remove_node = nodes.get(remove_id, {})
    add_node = nodes.get(add_id, {})

    remove_type = ("keystone" if remove_node.get("isKeystone") else
                   "notable" if remove_node.get("isNotable") else "travel")
    add_type = ("keystone" if add_node.get("isKeystone") else
                "notable" if add_node.get("isNotable") else "travel")

    if add_type == "notable" and remove_type == "travel":
        value_change_parts.append("upgraded travel→notable")
    elif add_type == "keystone" and remove_type == "notable":
        value_change_parts.append("sidegraded notable→keystone")
    elif remove_type == "notable" and add_type == "travel":
        value_change_parts.append("downgraded notable→travel")
    else:
        value_change_parts.append(f"swap {remove_type}→{add_type}")

    if orphaned:
        value_change_parts.append(
            f"WARNING: orphaning {', '.join(orphaned)} (nodes lose connection!)"
        )

    if travel_saved > 0:
        value_change_parts.append(f"saves {travel_saved} travel points")

    result = NodeSwapResult(
        removed_id=remove_id,
        removed_name=remove_name,
        added_id=add_id,
        added_name=add_name,
        point_delta=point_delta + travel_saved,
        travel_saved=travel_saved,
        value_change="; ".join(value_change_parts) if value_change_parts else "no change",
    )

    return result


# ============================================================
# Travel efficiency
# ============================================================

def travel_report(
    nodes: dict,
    graph: dict[str, list[str]],
    allocated_ids: list[str],
    class_start: str,
) -> TravelReport:
    """Analyze travel efficiency of allocated passive nodes."""
    allocated_set = set(str(x) for x in allocated_ids)

    # Categorize nodes
    notables_count = 0
    keystones_count = 0
    travel_count = 0

    for nid in allocated_set:
        node = nodes.get(nid, {})
        if node.get("isKeystone"):
            keystones_count += 1
        elif node.get("isNotable"):
            notables_count += 1
        else:
            travel_count += 1

    total = notables_count + keystones_count + travel_count
    travel_pct = (travel_count / total * 100) if total > 0 else 0
    notable_total = notables_count + keystones_count
    notables_per_travel = notable_total / max(travel_count, 1)

    # Count dead-ends: nodes with degree 1 that aren't keystones
    dead_ends = 0
    for nid in allocated_set:
        neighbors = graph.get(nid, [])
        allocated_neighbors = [n for n in neighbors if n in allocated_set]
        if len(allocated_neighbors) <= 1:
            node = nodes.get(nid, {})
            if not node.get("isKeystone"):
                dead_ends += 1

    # Grade
    if travel_pct < 25 and notables_per_travel > 1.0:
        grade = "A — Excellent"
    elif travel_pct < 35 and notables_per_travel > 0.7:
        grade = "B — Good"
    elif travel_pct < 50 and notables_per_travel > 0.4:
        grade = "C — Average"
    elif travel_pct < 60:
        grade = "D — Below average"
    else:
        grade = "F — Inefficient"

    return TravelReport(
        total_nodes=total,
        travel_nodes=travel_count,
        notable_nodes=notables_count,
        keystone_nodes=keystones_count,
        travel_percentage=travel_pct,
        notables_per_travel=notables_per_travel,
        dead_ends=dead_ends,
        efficiency_grade=grade,
    )


# ============================================================
# Budget optimization
# ============================================================

def optimize_budget(
    nodes: dict,
    graph: dict[str, list[str]],
    allocated_ids: list[str],
    class_start: str,
    max_points: int,
) -> tuple[list[str], str]:
    """Optimize node allocations to fit within a point budget.

    Strategy:
    1. Score every allocated node by "value per point"
    2. Remove lowest-value nodes until budget is met
    3. Prefer keeping keystones > notables > travel

    Returns (optimized_ids, report).
    """
    allocated_set = set(str(x) for x in allocated_ids)
    current_points = len(allocated_set)

    if current_points <= max_points:
        return list(allocated_set), "(Within budget — no optimization needed)"

    # Score each node
    scored: list[tuple[str, float, str]] = []  # (id, score, type)
    for nid in allocated_set:
        node = nodes.get(nid, {})
        ntype = ("keystone" if node.get("isKeystone") else
                 "notable" if node.get("isNotable") else "travel")

        if ntype == "keystone":
            score = 100
        elif ntype == "notable":
            # Prioritize notables with more connections
            neighbors = graph.get(nid, [])
            allocated_neighbors = sum(1 for n in neighbors if n in allocated_set)
            score = 50 + allocated_neighbors * 10
        else:
            # Travel nodes: score by how many allocated nodes depend on them
            score = 10

        scored.append((nid, score, ntype))

    scored.sort(key=lambda x: x[1])

    # Remove from lowest score up until budget met
    to_remove = current_points - max_points
    removed: set[str] = set()

    for nid, score, ntype in scored:
        if len(removed) >= to_remove:
            break
        # Don't remove nodes that would disconnect others
        if ntype == "travel":
            # Check if removing would orphan any node
            test_set = allocated_set - removed - {nid}
            if test_set:
                # BFS from class_start through test_set
                reachable = _reachable_nodes(graph, class_start, test_set)
                if reachable != test_set:
                    continue  # Can't remove — would disconnect
        removed.add(nid)

    final = list(allocated_set - removed)
    report = (
        f"Removed {len(removed)} nodes to fit {max_points}-point budget:\n"
        + "\n".join(f"  • {get_node_name(nodes, rid)} ({rid}) — score={next((s for i,s,t in scored if i==rid), 0):.0f}"
                     for rid in list(removed)[:10])
        + (f"\n  ... and {len(removed) - 10} more" if len(removed) > 10 else "")
    )

    return final, report


def _reachable_nodes(graph: dict[str, list[str]], start: str,
                     allowed: set[str]) -> set[str]:
    """Find all nodes reachable from start within allowed set."""
    reachable: set[str] = set()
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for nb in graph.get(current, []):
            if nb in allowed and nb not in reachable:
                queue.append(nb)
    return reachable & allowed


# ============================================================
# Consolidation analyzer
# ============================================================

def find_consolidation_targets(
    nodes: dict,
    graph: dict[str, list[str]],
    allocated_ids: list[str],
    class_start: str,
) -> str:
    """Find nearby clusters that could be consolidated for efficiency.

    Suggests routing improvements by identifying:
    - Clusters that could share travel nodes
    - Redundant pathing (two routes to same area)
    - Bridge nodes that unlock efficient shortcuts
    """
    allocated_set = set(str(x) for x in allocated_ids)
    clusters = find_clusters(nodes, graph, list(allocated_set),
                             max_cluster_distance=5)

    lines = ["=== Consolidation Analysis ===", f"",
             f"Found {len(clusters)} cluster(s):"]

    for c in clusters:
        notables_names = [get_node_name(nodes, n) for n in c.notable_ids[:5]]
        summary = ", ".join(notables_names)
        if len(c.notable_ids) > 5:
            summary += f", +{len(c.notable_ids) - 5} more"
        lines.append(f"  {c.summary()}")
        lines.append(f"    Notables: {summary}")
        if c.tags:
            lines.append(f"    Tags: {', '.join(c.tags[:5])}")

    # Find pairs of clusters that are close but not connected optimally
    if len(clusters) >= 2:
        lines.append(f"\n--- Inter-Cluster Optimization ---")
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                ci = clusters[i]
                cj = clusters[j]
                path = bfs_path(graph, ci.centroid_id, cj.centroid_id)
                travel_between = len(path) - 2  # exclude endpoints
                lines.append(
                    f"  {ci.cluster_id} ↔ {cj.cluster_id}: "
                    f"{travel_between} travel nodes between centroids"
                )
                if travel_between <= 4:
                    lines.append(f"    → Close! Consider bridging for efficiency.")

    # Check for redundant paths
    lines.append(f"\n--- Redundancy Check ---")
    # Look for nodes that are reached via two different paths (waste)
    for nid in list(allocated_set)[:5]:
        node = nodes.get(nid, {})
        if node.get("isNotable"):
            path = bfs_path(graph, class_start, nid)
            path_travel = sum(1 for p in path if p not in allocated_set)
            lines.append(
                f"  {get_node_name(nodes, nid)} ({nid}): "
                f"{len(path)} hops from start, {path_travel} new travel nodes needed"
            )

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Build Optimizer — cluster discovery, swaps, travel efficiency",
    )
    parser.add_argument("--spec", help="JSON build spec file with 'passives' array")
    parser.add_argument("--class", dest="class_name",
                        help="Class name (e.g. 'Mercenary')")
    parser.add_argument("--targets", nargs="+",
                        help="Target node IDs for routing")
    parser.add_argument("--find-clusters", action="store_true",
                        help="Discover notable clusters in allocated passives")
    parser.add_argument("--what-if", metavar="REMOVE_ID",
                        help="Simulate removing this node")
    parser.add_argument("--replace-with", metavar="ADD_ID",
                        help="Node to add instead (for --what-if)")
    parser.add_argument("--optimize-budget", type=int, metavar="MAX_POINTS",
                        help="Optimize allocations to fit within budget")
    parser.add_argument("--travel-report", action="store_true",
                        help="Show travel efficiency report")
    parser.add_argument("--consolidate", action="store_true",
                        help="Find consolidation opportunities")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    nodes_data = load_tree()
    if not nodes_data:
        print("Error: No tree data cached. Run: python fetch_tree.py --force",
              file=sys.stderr)
        sys.exit(1)

    nodes = nodes_data.get("nodes", {})
    classes_data = nodes_data.get("classes", [])
    graph = build_graph(nodes)

    # Get allocated IDs from spec or targets
    allocated_ids: list[str] = []
    if args.spec:
        try:
            with open(args.spec) as f:
                spec = json.load(f)
            allocated_ids = [str(p) for p in spec.get("passives", [])]
            class_name = spec.get("className", args.class_name or "")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading spec: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.targets:
        allocated_ids = [str(t) for t in args.targets]
        class_name = args.class_name or ""
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python build_optimizer.py --spec spec.json --travel-report")
        print("  python build_optimizer.py --spec spec.json --find-clusters")
        print("  python build_optimizer.py --spec spec.json --what-if 58714 --replace-with 46123")
        print("  python build_optimizer.py --spec spec.json --optimize-budget 103")
        return

    class_name = class_name or args.class_name or ""

    # Find class start
    from route_tree import find_class_root
    class_start = find_class_root(nodes, class_name) if class_name else "root"

    if args.travel_report:
        report = travel_report(nodes, graph, allocated_ids, class_start)
        print(report.format())

    elif args.find_clusters:
        clusters = find_clusters(nodes, graph, allocated_ids)
        if args.json:
            cluster_data = [
                {"id": c.cluster_id, "notables": c.notable_ids,
                 "travel": c.travel_nodes, "score": c.value_score}
                for c in clusters
            ]
            print(json.dumps(cluster_data, indent=2))
        else:
            print(f"Found {len(clusters)} cluster(s):\n")
            for c in clusters:
                print(c.summary())
                names = [get_node_name(nodes, n) for n in c.notable_ids]
                print(f"  Notables: {', '.join(names)}")
                if c.tags:
                    print(f"  Tags: {', '.join(c.tags[:5])}")
                print()

    elif args.what_if and args.replace_with:
        swap = simulate_swap(
            nodes, graph, allocated_ids,
            args.what_if, args.replace_with, class_start,
        )
        if swap:
            print(swap.format())
        else:
            print(f"Cannot simulate swap: {args.what_if} → {args.replace_with}")

    elif args.optimize_budget:
        optimized, report = optimize_budget(
            nodes, graph, allocated_ids, class_start, args.optimize_budget,
        )
        print(report)
        if args.json:
            print(json.dumps(optimized, indent=2))

    elif args.consolidate:
        print(find_consolidation_targets(nodes, graph, allocated_ids, class_start))

    else:
        # Default: show travel report + clusters
        report = travel_report(nodes, graph, allocated_ids, class_start)
        print(report.format())
        print()
        clusters = find_clusters(nodes, graph, allocated_ids)
        for c in clusters:
            print(c.summary())


if __name__ == "__main__":
    cli()
