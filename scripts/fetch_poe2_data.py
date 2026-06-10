#!/usr/bin/env python3
"""PoE2 Comprehensive Data Fetcher.

Fetches and caches item base data from Path of Building 2 Community repo.
Combines with GGG skill tree data and built-in references.

Data sources:
  - PoB2 Lua base files: all item types, stats, requirements, implicits
  - GGG skill tree: nodes, classes, ascendancies
  - Built-in: mod tiers, crafting data, skill gem tags
  - craftofexile PoE1/PoE2 combined: mod weights (when available)

Usage:
    python fetch_poe2_data.py --force    # rebuild all caches
    python fetch_poe2_data.py --bases    # just item bases
    python fetch_poe2_data.py --stats    # show cache status
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional

POB2_BASE = "https://raw.githubusercontent.com/PathOfBuildingCommunity/PathOfBuilding-PoE2/dev"
CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
BASES_CACHE = CACHE_DIR / "poe2-bases.json"
MOD_WEIGHTS_CACHE = CACHE_DIR / "poe2-mod-weights.json"

# Slot → PoB2 base file name
SLOT_FILES: dict[str, str] = {
    "Amulet": "amulet.lua",
    "Belt": "belt.lua",
    "Ring": "ring.lua",
    "Body Armour": "body.lua",
    "Boots": "boots.lua",
    "Gloves": "gloves.lua",
    "Helm": "helmet.lua",
    "Shield": "shield.lua",
    "Crossbow": "crossbow.lua",
    "Bow": "bow.lua",
    "Staff": "staff.lua",
    "One Hand Mace": "mace.lua",
    "Two Hand Mace": "mace.lua",
    "Sword": "sword.lua",
    "Claw": "claw.lua",
    "Dagger": "dagger.lua",
    "Spear": "spear.lua",
    "Flail": "flail.lua",
    "Focus": "focus.lua",
    "Quiver": "quiver.lua",
    "Sceptre": "sceptre.lua",
}


def parse_lua_table(text: str) -> dict:
    """Parse PoB2 Lua item base table into Python dict.

    Handles the format:
        itemBases["Name"] = { key = value, ... }
    """
    items: dict[str, dict] = {}

    # Match itemBases["Name"] = { ... }
    pattern = r'itemBases\[\"([^\"]+)\"\]\s*=\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
    for match in re.finditer(pattern, text, re.DOTALL):
        name = match.group(1)
        body = match.group(2)
        item: dict = {"name": name}
        item.update(_parse_fields(body))
        items[name] = item

    return items


def _parse_fields(body: str) -> dict:
    """Parse the fields within a Lua table body."""
    result: dict = {}

    # type = "Crossbow"
    type_match = re.search(r'type\s*=\s*"([^"]+)"', body)
    if type_match:
        result["type"] = type_match.group(1)

    # req = { level = 10, str = 13, dex = 13 }
    req_match = re.search(r'req\s*=\s*\{([^}]+)\}', body)
    if req_match:
        reqs: dict = {}
        for m in re.finditer(r'(\w+)\s*=\s*(\d+)', req_match.group(1)):
            reqs[m.group(1)] = int(m.group(2))
        result["requirements"] = reqs

    # implicit = "text"
    imp_match = re.search(r'implicit\s*=\s*"([^"]*)"', body)
    if imp_match and imp_match.group(1):
        result["implicit"] = imp_match.group(1)

    # implicitModTypes
    if "implicitModTypes" in body:
        result["has_implicit_mods"] = True

    # weapon stats
    weapon_match = re.search(r'weapon\s*=\s*\{([^}]+)\}', body)
    if weapon_match:
        weapon: dict = {}
        for m in re.finditer(r'(\w+)\s*=\s*([\d.]+)', weapon_match.group(1)):
            key = m.group(1)
            val = m.group(2)
            try:
                weapon[key] = float(val) if '.' in val else int(val)
            except ValueError:
                weapon[key] = val
        result["weapon"] = weapon

    # armour stats
    armour_match = re.search(r'armour\s*=\s*\{([^}]+)\}', body)
    if armour_match:
        armour: dict = {}
        for m in re.finditer(r'(\w+)\s*=\s*([\d.]+)', armour_match.group(1)):
            try:
                armour[m.group(1)] = int(m.group(2))
            except ValueError:
                pass
        result["armour"] = armour

    # tags
    tags_match = re.search(r'tags\s*=\s*\{([^}]+)\}', body)
    if tags_match:
        tags: list[str] = []
        for m in re.finditer(r'(\w+)\s*=\s*true', tags_match.group(1)):
            tags.append(m.group(1))
        result["tags"] = tags

    # socketLimit
    socket_match = re.search(r'socketLimit\s*=\s*(\d+)', body)
    if socket_match:
        result["socket_limit"] = int(socket_match.group(1))

    return result


def fetch_bases(force: bool = False) -> dict:
    """Fetch and parse all PoE2 item bases from PoB2 repo."""
    if not force and BASES_CACHE.exists():
        with open(BASES_CACHE) as f:
            return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_bases: dict[str, dict] = {}
    fetched = 0
    failed = 0

    for slot_name, filename in SLOT_FILES.items():
        url = f"{POB2_BASE}/src/Data/Bases/{filename}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agent-of-exile/4.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except Exception:
            failed += 1
            continue

        items = parse_lua_table(text)
        for name, data in items.items():
            data["slot"] = slot_name
            all_bases[name] = data
        fetched += len(items)

    result = {
        "source": "PathOfBuildingCommunity/PathOfBuilding-PoE2",
        "fetched_at": None,
        "total_items": len(all_bases),
        "slots_fetched": fetched,
        "slots_failed": failed,
        "items": all_bases,
    }

    with open(BASES_CACHE, "w") as f:
        json.dump(result, f, indent=2)

    return result


def build_mod_weights(force: bool = False) -> dict:
    """Build mod weight data from built-in reference + PoB2 export data.

    Returns a dict mapping mod names to weight/group/tier data.
    """
    if not force and MOD_WEIGHTS_CACHE.exists():
        with open(MOD_WEIGHTS_CACHE) as f:
            return json.load(f)

    # Built-in mod weight data (community-sourced, approximate)
    # Format: mod_group -> {slot: [(tag, weight), ...]}
    weights: dict[str, dict[str, list[tuple[str, int]]]] = {
        # Life prefixes
        "IncreasedLife": {
            "Body Armour": [("life_flat", 1000), ("life_flat_hybrid", 500)],
            "Helm": [("life_flat", 800)],
            "Gloves": [("life_flat", 600)],
            "Boots": [("life_flat", 600)],
            "Belt": [("life_flat", 1000)],
            "Ring": [("life_flat", 600)],
            "Amulet": [("life_flat", 600)],
            "Shield": [("life_flat", 800)],
        },
        # Energy Shield
        "IncreasedEnergyShield": {
            "Body Armour": [("es_flat", 1000), ("es_flat_hybrid", 500), ("es_percent", 250)],
            "Helm": [("es_flat", 800)],
            "Gloves": [("es_flat", 600)],
            "Boots": [("es_flat", 600)],
            "Shield": [("es_flat", 800), ("es_percent", 250)],
        },
        # Armour
        "IncreasedArmour": {
            "Body Armour": [("armour_flat", 1000), ("armour_percent", 250)],
            "Helm": [("armour_flat", 800)],
            "Gloves": [("armour_flat", 600)],
            "Boots": [("armour_flat", 600)],
            "Shield": [("armour_flat", 800), ("armour_percent", 250)],
        },
        # Evasion
        "IncreasedEvasion": {
            "Body Armour": [("evasion_flat", 1000), ("evasion_percent", 250)],
            "Helm": [("evasion_flat", 800)],
            "Gloves": [("evasion_flat", 600)],
            "Boots": [("evasion_flat", 600)],
            "Shield": [("evasion_flat", 800), ("evasion_percent", 250)],
        },
        # Resistances (suffix)
        "FireResistance": {
            "Body Armour": [("fire_res", 1000)],
            "Helm": [("fire_res", 1000)],
            "Gloves": [("fire_res", 1000)],
            "Boots": [("fire_res", 1000)],
            "Ring": [("fire_res", 1000)],
            "Amulet": [("fire_res", 800)],
            "Belt": [("fire_res", 1000)],
            "Shield": [("fire_res", 1000)],
        },
        "ColdResistance": {
            "Body Armour": [("cold_res", 1000)],
            "Helm": [("cold_res", 1000)],
            "Gloves": [("cold_res", 1000)],
            "Boots": [("cold_res", 1000)],
            "Ring": [("cold_res", 1000)],
            "Amulet": [("cold_res", 800)],
            "Belt": [("cold_res", 1000)],
            "Shield": [("cold_res", 1000)],
        },
        "LightningResistance": {
            "Body Armour": [("light_res", 1000)],
            "Helm": [("light_res", 1000)],
            "Gloves": [("light_res", 1000)],
            "Boots": [("light_res", 1000)],
            "Ring": [("light_res", 1000)],
            "Amulet": [("light_res", 800)],
            "Belt": [("light_res", 1000)],
            "Shield": [("light_res", 1000)],
        },
        "ChaosResistance": {
            "Body Armour": [("chaos_res", 250)],
            "Helm": [("chaos_res", 250)],
            "Gloves": [("chaos_res", 250)],
            "Boots": [("chaos_res", 250)],
            "Ring": [("chaos_res", 250)],
            "Amulet": [("chaos_res", 250)],
            "Belt": [("chaos_res", 250)],
            "Shield": [("chaos_res", 250)],
        },
        # Attributes (suffix)
        "Strength": {
            "Body Armour": [("strength", 500)],
            "Helm": [("strength", 500)],
            "Gloves": [("strength", 500)],
            "Boots": [("strength", 500)],
            "Ring": [("strength", 500)],
            "Amulet": [("strength", 1000)],
            "Belt": [("strength", 1000)],
        },
        "Dexterity": {
            "Body Armour": [("dexterity", 500)],
            "Helm": [("dexterity", 500)],
            "Gloves": [("dexterity", 500)],
            "Boots": [("dexterity", 500)],
            "Ring": [("dexterity", 500)],
            "Amulet": [("dexterity", 1000)],
            "Belt": [("dexterity", 1000)],
        },
        "Intelligence": {
            "Body Armour": [("intelligence", 500)],
            "Helm": [("intelligence", 500)],
            "Gloves": [("intelligence", 500)],
            "Boots": [("intelligence", 500)],
            "Ring": [("intelligence", 500)],
            "Amulet": [("intelligence", 1000)],
            "Belt": [("intelligence", 1000)],
        },
        # Weapon mods
        "PhysicalDamage": {
            "Weapon": [("increased_phys", 1000), ("flat_phys", 1000),
                       ("flat_phys_hybrid", 500), ("phys_percent_hybrid", 250)],
        },
        "AttackSpeed": {
            "Weapon": [("attack_speed", 1000)],
            "Gloves": [("attack_speed", 250)],
        },
        "CriticalStrikeChance": {
            "Weapon": [("crit_chance", 1000)],
            "Helm": [("crit_chance", 250)],
        },
        "SpellDamage": {
            "Weapon": [("spell_damage", 1000), ("spell_damage_hybrid", 500)],
            "Shield": [("spell_damage", 500)],
            "Amulet": [("spell_damage", 250)],
        },
        "MovementSpeed": {
            "Boots": [("movement_speed", 1000)],
        },
        # Elemental damage (weapons)
        "AddedFireDamage": {
            "Weapon": [("flat_fire", 1000)],
            "Gloves": [("flat_fire", 500)],
            "Ring": [("flat_fire", 250)],
        },
        "AddedColdDamage": {
            "Weapon": [("flat_cold", 1000)],
            "Gloves": [("flat_cold", 500)],
            "Ring": [("flat_cold", 250)],
        },
        "AddedLightningDamage": {
            "Weapon": [("flat_lightning", 1000)],
            "Gloves": [("flat_lightning", 500)],
            "Ring": [("flat_lightning", 250)],
        },
        # Spirit
        "Spirit": {
            "Body Armour": [("spirit", 250)],
            "Helm": [("spirit", 100)],
            "Amulet": [("spirit", 500)],
            "Shield": [("spirit", 500)],
        },
        # Rarity
        "ItemRarity": {
            "Body Armour": [("rarity", 500)],
            "Helm": [("rarity", 500)],
            "Gloves": [("rarity", 500)],
            "Boots": [("rarity", 500)],
            "Ring": [("rarity", 500)],
            "Amulet": [("rarity", 500)],
        },
    }

    data = {
        "source": "built-in + community estimates",
        "note": "Exact weights may vary per patch. Update from craftofexile when available.",
        "version": 1,
        "weights": weights,
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MOD_WEIGHTS_CACHE, "w") as f:
        json.dump(data, f, indent=2)

    return data


def get_weights_for_slot(slot: str, weights_data: Optional[dict] = None) -> list[tuple[str, int]]:
    """Get all mod weights for a slot, sorted by weight descending."""
    if weights_data is None:
        weights_data = build_mod_weights()

    all_mods: list[tuple[str, int]] = []
    weights = weights_data.get("weights", {})

    for group_name, slot_data in weights.items():
        if slot in slot_data:
            all_mods.extend(slot_data[slot])

    all_mods.sort(key=lambda x: x[1], reverse=True)
    return all_mods


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch PoE2 comprehensive data caches"
    )
    parser.add_argument("--force", action="store_true", help="Force rebuild all caches")
    parser.add_argument("--bases", action="store_true", help="Fetch only item bases")
    parser.add_argument("--weights", action="store_true", help="Build only mod weights")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")

    args = parser.parse_args()

    if args.stats:
        if BASES_CACHE.exists():
            with open(BASES_CACHE) as f:
                bases = json.load(f)
            print(f"Item bases: {bases.get('total_items', 0)} items "
                  f"(from {bases.get('source', '?')})")
        else:
            print("Item bases: not cached (run --bases)")

        if MOD_WEIGHTS_CACHE.exists():
            with open(MOD_WEIGHTS_CACHE) as f:
                weights = json.load(f)
            groups = len(weights.get("weights", {}))
            print(f"Mod weights: {groups} groups (from {weights.get('source', '?')})")
        else:
            print("Mod weights: not cached (run --weights)")
        return

    if args.bases:
        data = fetch_bases(force=args.force)
        print(f"Fetched {data['total_items']} item bases "
              f"({data['slots_fetched']} slots, {data['slots_failed']} failed)")
    elif args.weights:
        data = build_mod_weights(force=args.force)
        print(f"Built mod weights: {len(data['weights'])} groups")
    else:
        # Fetch everything
        bases = fetch_bases(force=args.force)
        print(f"Bases: {bases['total_items']} items")
        weights = build_mod_weights(force=args.force)
        print(f"Weights: {len(weights['weights'])} groups")
        print("Done.")


if __name__ == "__main__":
    cli()
