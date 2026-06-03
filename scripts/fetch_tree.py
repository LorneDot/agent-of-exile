#!/usr/bin/env python3
"""Fetch and cache the PoE2 skill tree data from GGG's GitHub export.

Downloads data.json from grindinggear/poe2-skilltree-export and caches
it locally. Subsequent calls use the cache unless --force is passed.

Usage:
    python fetch_tree.py                  # fetch + cache
    python fetch_tree.py --force          # force re-fetch
    python fetch_tree.py --path           # print cache path
    python fetch_tree.py --stats          # print tree stats
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "grindinggear/poe2-skilltree-export/main/data.json"
)
CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
CACHE_FILE = CACHE_DIR / "tree-data.json"
META_FILE = CACHE_DIR / "meta.json"


def fetch_tree(force: bool = False) -> dict:
    """Fetch tree data, using cache unless force=True."""
    if not force and CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)

    import urllib.request

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {DATA_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(DATA_URL) as resp:
        data = json.load(resp)

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


def get_tree_stats(data: dict) -> dict:
    """Return summary statistics about the tree."""
    return {
        "version": data.get("tree", "unknown"),
        "classes": len(data.get("classes", [])),
        "class_names": [c["name"] for c in data.get("classes", [])],
        "nodes": len(data.get("nodes", {})),
        "groups": len(data.get("groups", {})),
        "edges": len(data.get("edges", {})),
        "jewel_slots": len(data.get("jewelSlots", [])),
    }


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch PoE2 skill tree data from GGG GitHub"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch even if cached"
    )
    parser.add_argument(
        "--path", action="store_true", help="Print cache file path and exit"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print tree statistics"
    )
    args = parser.parse_args()

    if args.path:
        fetch_tree()  # ensure cache exists
        print(CACHE_FILE)
        return

    data = fetch_tree(force=args.force)

    if args.stats:
        stats = get_tree_stats(data)
        for k, v in stats.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    cli()
