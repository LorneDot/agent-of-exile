#!/usr/bin/env python3
"""Fetch PoE2 character data from the official API.

Requires a POESESSID cookie from pathofexile.com login.
Get it from browser DevTools → Application → Cookies → POESESSID.

Usage:
    # List characters on an account
    python fetch_character.py --account Lorne --session YOUR_SESSION_ID

    # Fetch a specific character's full data
    python fetch_character.py --account Lorne --char MyWitch --session YOUR_SESSION_ID

    # Output as JSON for pipeline use
    python fetch_character.py --account Lorne --char MyWitch --session YOUR_SESSION_ID --json

    # Read session from environment variable (recommended for security)
    export POESESSID=your_session_id
    python fetch_character.py --account Lorne --char MyWitch
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


API_BASE = "https://www.pathofexile.com"
CHARACTERS_URL = f"{API_BASE}/character-window/get-characters"
ITEMS_URL = f"{API_BASE}/character-window/get-items"
PASSIVES_URL = f"{API_BASE}/character-window/get-passive-skills"


def _fetch(url: str, session_id: str) -> dict:
    """Make an authenticated request to the PoE API."""
    req = urllib.request.Request(url)
    req.add_header("Cookie", f"POESESSID={session_id}")
    req.add_header("User-Agent", "poe2-theory-crafter/1.0")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"API returned {e.code}: {body[:500]}"
        ) from e


def list_characters(account: str, session_id: str) -> list[dict]:
    """List all characters on an account.

    Returns list of {name, league, class, level, ...} dicts.
    """
    url = f"{CHARACTERS_URL}?accountName={account}"
    data = _fetch(url, session_id)
    # Filter to PoE2 characters (PoE2 leagues have specific naming)
    # Return all — let caller filter
    return data if isinstance(data, list) else []


def fetch_character(account: str, character: str, session_id: str) -> dict:
    """Fetch full character data: items, passives, stats.

    Returns a dict with:
      - character: {name, league, class, level, ascendancy, ...}
      - items: [{slot, item data, sockets, ...}]
      - passives: {hashes, jewel_data, ...}
    """
    items_data = _fetch(
        f"{ITEMS_URL}?accountName={account}&character={character}",
        session_id,
    )
    passives_data = _fetch(
        f"{PASSIVES_URL}?accountName={account}&character={character}&reqData=1",
        session_id,
    )

    return {
        "character": items_data.get("character", {}),
        "items": items_data.get("items", []),
        "jewels": items_data.get("jewels", []),
        "passives": passives_data,
    }


def summarize_character(data: dict) -> str:
    """Produce a human-readable character summary."""
    char = data.get("character", {})
    items = data.get("items", [])
    passives = data.get("passives", {})

    lines = [
        f"=== {char.get('name', 'Unknown')} ===",
        f"Class: {char.get('class', '?')}",
        f"Level: {char.get('level', '?')}",
        f"League: {char.get('league', '?')}",
        f"Ascendancy: {char.get('ascendancyClass', 'None')}",
        "",
        "--- Equipment ---",
    ]

    slot_order = [
        "Weapon", "Weapon2", "Offhand", "Offhand2",
        "Helm", "Body Armour", "Gloves", "Boots",
        "Amulet", "Ring", "Ring2", "Belt",
        "Flask", "Flask2",
    ]

    items_by_slot: dict[str, dict] = {}
    for item in items:
        slot = item.get("inventoryId", "Unknown")
        items_by_slot[slot] = item

    for slot in slot_order:
        item = items_by_slot.get(slot)
        if item:
            name = item.get("name", "") or item.get("typeLine", "?")
            rarity = item.get("frameType", 0)
            rarity_str = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique"}.get(
                rarity, "?"
            )
            ilvl = item.get("ilvl", "?")
            sockets = len(item.get("sockets", []))
            links = item.get("socketedItems", [])
            links_str = ""
            if links:
                gem_names = [g.get("typeLine", "?") for g in links]
                links_str = f" [{', '.join(gem_names)}]"
            lines.append(
                f"  {slot:12s} [{rarity_str}] {name} (iLv.{ilvl}){links_str}"
            )
        else:
            lines.append(f"  {slot:12s} [Empty]")

    # Passive summary
    hashes = passives.get("hashes", [])
    lines.append(f"\n--- Passives ---")
    lines.append(f"  Allocated nodes: {len(hashes)}")

    # Ascendancy nodes
    ascendancy_nodes = [
        h for h in hashes
        if isinstance(h, int) and h > 60000  # ascendancy nodes are high IDs
    ]
    if ascendancy_nodes:
        lines.append(f"  Ascendancy nodes: {len(ascendancy_nodes)}")

    # Jewel data
    jewel_data = passives.get("jewel_data", {})
    if jewel_data:
        cluster_count = len(jewel_data)
        lines.append(f"  Jewel sockets: {cluster_count}")

    return "\n".join(lines)


def analyze_build(data: dict) -> str:
    """Quick analysis pass on a character — what looks off?

    Source: basic sanity checks. For deep analysis, feed to the agent via
    the character audit workflow in SKILL.md.
    """
    char = data.get("character", {})
    items = data.get("items", [])
    passives = data.get("passives", {})
    issues = []
    level = char.get("level", 0)

    # Check for empty gear slots
    equipped = {i.get("inventoryId"): i for i in items}
    core_slots = [
        "Weapon", "Helm", "Body Armour", "Gloves", "Boots",
        "Amulet", "Ring", "Ring2", "Belt",
    ]
    empty = [s for s in core_slots if s not in equipped]
    if empty:
        issues.append(f"Empty slots: {', '.join(empty)}")

    # Check resistances (from character panel if available)
    if level >= 68:
        # At maps, you want capped resists
        issues.append(
            "[INFO] At maps (68+) — verify 75%+ elemental resists after -60% penalty"
        )

    # Check life/ES
    life = char.get("life", 0)
    es = char.get("energyShield", 0)
    if level >= 70 and life < 2000 and es < 2000:
        issues.append(
            f"Low EHP: {life} life + {es} ES — aim for 4K+ combined at this level"
        )

    # Check for unspent passive points
    # (API doesn't directly expose this, but low hash count vs level is a clue)
    hashes = passives.get("hashes", [])
    expected_passives = (level - 1) + 24  # levels + quest rewards
    if hashes and len(hashes) < expected_passives * 0.7:
        issues.append(
            f"Few allocated passives: {len(hashes)} — expected ~{expected_passives}"
        )

    if not issues:
        return "No obvious issues detected from quick scan."

    return "\n".join(f"• {i}" for i in issues)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch PoE2 character data from official API"
    )
    parser.add_argument(
        "--account", required=True, help="Account name (from pathofexile.com)"
    )
    parser.add_argument("--char", help="Character name (omit to list all)")
    parser.add_argument(
        "--session",
        help="POESESSID cookie value (or set POESESSID env var)",
        default=None,
    )
    parser.add_argument(
        "--json", action="store_true", help="Output raw JSON"
    )
    parser.add_argument(
        "--analyze", action="store_true", help="Run quick analysis pass"
    )
    args = parser.parse_args()

    session_id = args.session or os.environ.get("POESESSID")
    if not session_id:
        print(
            "Error: POESESSID required. Pass --session or set POESESSID env var.\n"
            "Get it from: pathofexile.com → login → DevTools → Application → "
            "Cookies → POESESSID",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.char:
        data = fetch_character(args.account, args.char, session_id)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(summarize_character(data))
            if args.analyze:
                print()
                print("--- Quick Analysis ---")
                print(analyze_build(data))
    else:
        chars = list_characters(args.account, session_id)
        if args.json:
            print(json.dumps(chars, indent=2))
        else:
            if not chars:
                print("No characters found on this account.")
                return
            for c in chars:
                print(
                    f"  Lv.{c.get('level', '?'):3d}  "
                    f"{c.get('class', '?'):12s}  "
                    f"{c.get('name', '?')}"
                )


if __name__ == "__main__":
    cli()
