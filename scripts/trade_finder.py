#!/usr/bin/env python3
"""PoE2 Trade API Integration.

Searches the official Path of Exile 2 trade site for items matching
desired mods, price checks items, and suggests upgrades.

Usage:
    python trade_finder.py --slot "Body Armour" --mods life_flat fire_res cold_res
    python trade_finder.py --slot "Ring" --mods life_flat fire_res cold_res lightning_res --max-price 50
    python trade_finder.py --upgrade-for "MyWitch" --account Lorne
    python trade_finder.py --price-check item.json
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================
# Trade API constants
# ============================================================

TRADE_API_BASE = "https://www.pathofexile.com/api/trade2"
SEARCH_URL = f"{TRADE_API_BASE}/search/Standard"
FETCH_URL = f"{TRADE_API_BASE}/fetch"

# Slot mapping to trade API filters
SLOT_FILTER: dict[str, str] = {
    "Body Armour": "body_armour",
    "Helm": "helmet",
    "Gloves": "gloves",
    "Boots": "boots",
    "Ring": "ring",
    "Amulet": "amulet",
    "Belt": "belt",
    "Weapon": "weapon",
    "Shield": "shield",
    "Crossbow": "weapon.crossbow",
    "Bow": "weapon.bow",
    "Staff": "weapon.warstaff",
    "One Hand Mace": "weapon.onemace",
    "Two Hand Mace": "weapon.twomace",
    "Quiver": "weapon.quiver",
}

# Mod name → trade API stat ID (common PoE2 mods)
MOD_STAT_MAP: dict[str, str] = {
    "life_flat": "explicit.stat_3299347043",        # +X to maximum Life
    "es_flat": "explicit.stat_3489782002",           # +X to maximum Energy Shield
    "fire_res": "explicit.stat_3372524247",          # +X% Fire Resistance
    "cold_res": "explicit.stat_4220027924",          # +X% Cold Resistance
    "light_res": "explicit.stat_1671376347",         # Lightning
    "chaos_res": "explicit.stat_2923486259",         # +X% Chaos Resistance
    "strength": "explicit.stat_4080418644",          # +X Strength
    "dexterity": "explicit.stat_3261801346",         # +X Dexterity
    "intelligence": "explicit.stat_328541901",       # +X Intelligence
    "movement_speed": "explicit.stat_2250533757",    # % Movement Speed
    "increased_phys": "explicit.stat_1509134228",    # % Physical Damage
    "flat_phys": "explicit.stat_1940865751",         # Adds X-Y Physical
    "attack_speed": "explicit.stat_210067635",       # % Attack Speed
    "spell_damage": "explicit.stat_2974417149",      # % Spell Damage
    "crit_chance": "explicit.stat_587431675",        # % Crit Chance
    "rarity": "explicit.stat_3917489142",            # % Rarity
    "spirit": "explicit.stat_1707539490",            # +X Spirit
}


@dataclass
class TradeResult:
    """A single trade search result."""
    name: str
    price: str
    seller: str
    whisper: str
    item_level: int
    mods: list[str]

    def format(self) -> str:
        lines = [
            f"  {self.name} — {self.price}",
            f"    iLvl: {self.item_level} | Seller: {self.seller}",
        ]
        for mod in self.mods[:4]:
            lines.append(f"    • {mod}")
        if len(self.mods) > 4:
            lines.append(f"    ... and {len(self.mods) - 4} more mods")
        return "\n".join(lines)


@dataclass
class TradeSearch:
    """Results from a trade search."""
    slot: str
    desired_mods: list[str]
    results: list[TradeResult] = field(default_factory=list)
    total_listings: int = 0
    search_url: str = ""

    def format(self) -> str:
        lines = [
            f"=== Trade Search: {self.slot} ===",
            f"Desired mods: {', '.join(self.desired_mods)}",
            f"Total listings: {self.total_listings}",
            "",
        ]
        if self.search_url:
            lines.append(f"Trade site: {self.search_url}")
            lines.append("")

        if not self.results:
            lines.append("No results found. Try relaxing mod requirements.")
            return "\n".join(lines)

        lines.append(f"Top {len(self.results)} results:")
        for r in self.results:
            lines.append(r.format())
            lines.append("")

        return "\n".join(lines)


def build_trade_url(
    slot: str,
    mods: list[str],
    max_price_chaos: Optional[int] = None,
) -> str:
    """Build a poe2 trade search URL from slot + mods.

    Returns a URL that can be opened in a browser.
    """
    league = "Standard"
    base_url = f"https://www.pathofexile.com/trade2/search/poe2/{league}"

    # Build query JSON
    query: dict = {
        "query": {
            "status": {"option": "online"},
            "filters": {},
        },
        "sort": {"price": "asc"},
    }

    # Slot filter
    slot_key = SLOT_FILTER.get(slot)
    if slot_key:
        if "type_filters" not in query["query"]:
            query["query"]["type_filters"] = {}
        query["query"]["type_filters"]["category"] = {"option": slot_key.split(".")[0]}
        if "." in slot_key:
            query["query"]["type_filters"]["subcategory"] = {"option": slot_key.split(".")[1]}

    # Mod filters
    if mods:
        stats_filter: list[dict] = []
        for mod in mods:
            stat_id = MOD_STAT_MAP.get(mod)
            if stat_id:
                stats_filter.append({
                    "type": "and",
                    "filters": [],
                    "disabled": False,
                })
        if stats_filter:
            query["query"]["stats"] = [{"type": "and", "filters": stats_filter}]

    # Price filter
    if max_price_chaos:
        query["query"]["filters"]["trade_filters"] = {
            "filters": {
                "price": {
                    "min": None,
                    "max": max_price_chaos,
                    "option": "chaos",
                }
            }
        }

    query_str = json.dumps(query, separators=(",", ":"))
    return f"{base_url}?q={urllib.parse.quote(query_str)}"


def search_trade(
    slot: str,
    desired_mods: list[str],
    max_price_chaos: Optional[int] = None,
    session_id: Optional[str] = None,
) -> TradeSearch:
    """Search the PoE2 trade API for items matching mods.

    Requires POESESSID for API access (same as character fetch).
    Falls back to generating a trade site URL if no session.
    """
    search = TradeSearch(
        slot=slot,
        desired_mods=desired_mods,
        search_url=build_trade_url(slot, desired_mods, max_price_chaos),
    )

    if not session_id:
        # No API access — just provide the URL
        search.results = []
        search.total_listings = 0
        return search

    # Build query for API
    league = "Standard"
    query = {
        "query": {
            "status": {"option": "online"},
        },
        "sort": {"price": "asc"},
    }

    # Slot
    slot_key = SLOT_FILTER.get(slot)
    if slot_key:
        query["query"]["type"] = slot_key

    # Mods
    stat_filters: list[dict] = []
    for mod in desired_mods:
        stat_id = MOD_STAT_MAP.get(mod)
        if stat_id:
            stat_filters.append({
                "id": stat_id,
                "value": {"min": 0},
                "disabled": False,
            })

    if stat_filters:
        query["query"]["stats"] = [{"type": "and", "filters": stat_filters}]

    if max_price_chaos:
        query["query"]["filters"] = {
            "trade_filters": {
                "filters": {
                    "price": {"min": None, "max": max_price_chaos, "option": "chaos"}
                }
            }
        }

    # Execute search
    try:
        req = urllib.request.Request(
            SEARCH_URL,
            data=json.dumps(query).encode(),
            headers={
                "Content-Type": "application/json",
                "Cookie": f"POESESSID={session_id}",
                "User-Agent": "agent-of-exile/4.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)

        search_id = data.get("id")
        result_ids = data.get("result", [])[:10]  # top 10
        search.total_listings = data.get("total", 0)

        if search_id and result_ids:
            # Fetch item details
            fetch_query = ",".join(result_ids)
            fetch_req = urllib.request.Request(
                f"{FETCH_URL}/{fetch_query}?query={search_id}",
                headers={
                    "Cookie": f"POESESSID={session_id}",
                    "User-Agent": "agent-of-exile/4.0",
                },
            )
            with urllib.request.urlopen(fetch_req, timeout=15) as resp:
                fetch_data = json.load(resp)

            for item_result in fetch_data.get("result", []):
                item = item_result.get("item", {})
                listing = item_result.get("listing", {})

                name = item.get("name", "") or item.get("typeLine", "?")
                price_data = listing.get("price", {})
                price = f"{price_data.get('amount', '?')} {price_data.get('currency', '?')}"
                seller = listing.get("account", {}).get("lastCharacterName", "?")
                whisper = listing.get("whisper", "")
                ilvl = item.get("ilvl", 0)

                # Extract explicit mods
                mods = []
                for mod in item.get("explicitMods", [])[:6]:
                    mods.append(mod)

                search.results.append(TradeResult(
                    name=name,
                    price=price,
                    seller=seller,
                    whisper=whisper,
                    item_level=ilvl,
                    mods=mods,
                ))

    except Exception as e:
        # Fall back to URL-only
        pass

    return search


def suggest_upgrades(
    character_data: dict,
    budget: int = 50,
    session_id: Optional[str] = None,
) -> str:
    """Suggest trade upgrades for a character based on their current gear."""
    items = character_data.get("items", [])
    char = character_data.get("character", {})

    lines = [
        f"=== Trade Upgrades for {char.get('name', '?')} ===",
        f"Budget per slot: {budget}c",
        "",
    ]

    priority_slots = [
        "Weapon", "Body Armour", "Helm", "Ring", "Ring2",
        "Amulet", "Gloves", "Boots", "Belt",
    ]

    for slot in priority_slots:
        item = next((i for i in items if i.get("inventoryId") == slot), None)
        if not item:
            lines.append(f"[{slot}] Empty — equip any rare with life+resists")
            continue

        item_name = item.get("name", "") or item.get("typeLine", "?")
        ilvl = item.get("ilvl", 0)
        rarity = item.get("frameType", 0)

        if rarity < 2:  # Normal or Magic
            lines.append(f"[{slot}] {item_name} (iLvl {ilvl}) — Normal/Magic")
            lines.append(f"  → Search trade for rare {slot} with life + resists ({budget}c)")
        elif ilvl < 60:
            lines.append(f"[{slot}] {item_name} (iLvl {ilvl}) — Low iLvl")
            lines.append(f"  → Search trade for iLvl 75+ {slot} ({budget}c)")

    lines.append(f"\n--- Generic Upgrade Searches ---")
    lines.append(f"Trade site: https://www.pathofexile.com/trade2/search/poe2/Standard")
    lines.append(f"(Set POESESSID for automated trade search)")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="PoE2 Trade Finder — search trade site for items"
    )
    parser.add_argument("--slot", help="Equipment slot")
    parser.add_argument("--mods", nargs="+", help="Desired mod IDs")
    parser.add_argument("--max-price", type=int, help="Max price in chaos")
    parser.add_argument("--session",
                        help="POESESSID cookie for live trade search")
    parser.add_argument("--upgrade-for", dest="char_name",
                        help="Character name for upgrade suggestions")
    parser.add_argument("--account", help="Account name (with --upgrade-for)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--url-only", action="store_true",
                        help="Only generate trade URL, don't search")

    args = parser.parse_args()

    session_id = args.session or os.environ.get("POESESSID")

    if args.char_name:
        if not args.account:
            print("Error: --account required with --upgrade-for", file=sys.stderr)
            sys.exit(1)


    if args.char_name and args.account:
        # Character upgrade mode
        from fetch_character import fetch_character
        try:
            if not session_id:
                print("Warning: No POESESSID — upgrade suggestions limited.\n"
                      "Set POESESSID for live trade search.", file=sys.stderr)
                print(suggest_upgrades({"character": {"name": args.char_name}, "items": []}))
                return
            data = fetch_character(args.account, args.char_name, session_id)
            print(suggest_upgrades(data, session_id=session_id))
        except Exception as e:
            print(f"Error fetching character: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.slot or not args.mods:
        parser.print_help()
        print("\nExamples:")
        print("  python trade_finder.py --slot 'Body Armour' --mods life_flat fire_res cold_res")
        print("  python trade_finder.py --slot 'Ring' --mods life_flat fire_res cold_res lightning_res")
        print("  python trade_finder.py --slot 'Body Armour' --mods life_flat fire_res --url-only")
        return

    if args.url_only:
        url = build_trade_url(args.slot, args.mods, args.max_price)
        print(f"Trade URL: {url}")
        return

    result = search_trade(args.slot, args.mods, args.max_price, session_id)
    if args.json:
        import json
        print(json.dumps({
            "slot": result.slot,
            "desired_mods": result.desired_mods,
            "total_listings": result.total_listings,
            "search_url": result.search_url,
            "results": [
                {"name": r.name, "price": r.price, "seller": r.seller,
                 "ilvl": r.item_level, "mods": r.mods}
                for r in result.results
            ],
        }, indent=2))
    else:
        print(result.format())


if __name__ == "__main__":
    cli()
