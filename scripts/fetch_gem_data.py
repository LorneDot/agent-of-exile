#!/usr/bin/env python3
"""PoE2 Gem Data Pack.

Downloads and caches gem data from poe2db.tw for offline use.
If the web fetch fails (poe2db.tw blocks automated requests), falls back
to a built-in tag-based reference with common gem patterns.

Usage:
    python fetch_gem_data.py           # fetch and cache
    python fetch_gem_data.py --force   # force re-fetch
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "poe2-theory-crafter"
GEMS_CACHE = CACHE_DIR / "gems.json"
POE2DB_GEMS_URL = "https://poe2db.tw/us/Gem"


def fetch_from_poe2db() -> dict | None:
    """Try to fetch gem data from poe2db.tw. Returns None if blocked."""
    try:
        req = urllib.request.Request(
            POE2DB_GEMS_URL,
            headers={"User-Agent": "agent-of-exile/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  poe2db.tw fetch failed: {e}", file=sys.stderr)
        return None

    # poe2db.tw is a JS SPA — the HTML won't contain structured gem data.
    # We'd need a headless browser to scrape it. Instead, use the built-in
    # tag reference and note that poe2db.tw requires manual lookup.
    print("  poe2db.tw page fetched but is a JS app — cannot extract data.",
          file=sys.stderr)
    print("  Use the built-in tag reference instead.", file=sys.stderr)
    return None


def build_tag_reference() -> dict:
    """Build a tag-based gem reference from known PoE2 patterns.

    This provides enough data for the gem linker to match supports to skills
    by tag compatibility. Not exhaustive, but covers the most common cases.
    """
    # Common support gem patterns: name → [tags_it_supports, effect_type]
    support_patterns = {
        # Fire
        "FirePenetration": (["Fire"], "penetration"),
        "FireAttunement": (["Fire"], "more_damage"),
        "IgniteProliferation": (["Fire", "Ignite"], "ailment_spread"),
        "BurningDamage": (["Fire", "DamageOverTime"], "more_damage"),
        # Cold
        "ColdPenetration": (["Cold"], "penetration"),
        "Hypothermia": (["Cold", "Chill"], "more_damage"),
        "IceBite": (["Cold", "Freeze"], "added_damage"),
        # Lightning
        "LightningPenetration": (["Lightning"], "penetration"),
        "Overcharge": (["Lightning", "Shock"], "ailment_effect"),
        "Innervate": (["Lightning", "Shock"], "added_damage"),
        # Physical
        "Brutality": (["Physical"], "more_damage"),
        "MeleePhysicalDamage": (["Physical", "Melee"], "more_damage"),
        "Maim": (["Physical", "Attack"], "debuff"),
        "Impale": (["Physical", "Attack"], "impale"),
        # Chaos
        "ChaosPenetration": (["Chaos"], "penetration"),
        "VoidManipulation": (["Chaos"], "more_damage"),
        "DeadlyAilments": (["DamageOverTime", "Ailment"], "more_damage"),
        # Projectile
        "GreaterMultipleProjectiles": (["Projectile"], "more_projectiles"),
        "Multishot": (["Projectile", "Crossbow"], "more_projectiles"),
        "Pierce": (["Projectile"], "pierce"),
        "Chain": (["Projectile"], "chain"),
        "Fork": (["Projectile"], "fork"),
        "SlowerProjectiles": (["Projectile"], "more_damage"),
        # AoE
        "IncreasedAreaOfEffect": (["AoE"], "increased_aoe"),
        "ConcentratedEffect": (["AoE"], "more_damage"),
        "MagnifiedArea": (["AoE"], "increased_aoe"),
        # Attack
        "AddedFireDamage": (["Attack", "Physical"], "added_damage"),
        "AddedColdDamage": (["Attack"], "added_damage"),
        "AddedLightningDamage": (["Attack"], "added_damage"),
        "ElementalDamageWithAttacks": (["Attack", "ElementalDamage"], "more_damage"),
        # Spell
        "SpellEcho": (["Spell"], "more_cast_speed"),
        "FasterCasting": (["Spell"], "increased_cast_speed"),
        "ControlledDestruction": (["Spell"], "more_damage"),
        "ArcaneSurge": (["Spell"], "buff"),
        # Minion
        "MinionDamage": (["Minion"], "more_damage"),
        "MinionSpeed": (["Minion"], "increased_speed"),
        "FeedingFrenzy": (["Minion"], "more_damage"),
        # Duration / Cooldown
        "IncreasedDuration": (["Duration"], "increased_duration"),
        "LessDuration": (["Duration"], "more_damage"),
        "SecondWind": (["Cooldown"], "extra_use"),
        # Grenade/Crossbow specific
        "ShortFuse": (["Grenade"], "faster_detonation"),
        "AdhesiveGrenades": (["Grenade"], "utility"),
        "LongFuse": (["Grenade"], "more_damage"),
        "Payload": (["Grenade"], "more_damage"),
        # Generic
        "FasterAttacks": (["Attack"], "increased_speed"),
        "ElementalFocus": (["ElementalDamage"], "more_damage"),
        "Inspiration": (["Any"], "cost_reduction"),
        "Lifetap": (["Any"], "cost_conversion"),
        "ItemRarity": (["Any"], "magic_find"),
        # Detonator / Payoff
        "Deliberation": (["Detonator", "Cooldown"], "more_damage"),
        # Warcry
        "UrgentOrders": (["Warcry"], "increased_speed"),
        "EmpoweredDamage": (["Warcry"], "more_damage"),
        # Totem
        "TotemDamage": (["Totem"], "more_damage"),
        "MultipleTotems": (["Totem"], "extra_totem"),
    }

    return {
        "source": "built-in tag reference",
        "note": "For exact gem data (IDs, level scaling, attribute requirements), use poe2db.tw directly.",
        "support_gems": {
            name: {"tags": tags, "effect": effect}
            for name, (tags, effect) in support_patterns.items()
        },
    }


def get_gem_data(force: bool = False) -> dict:
    """Get gem data, from cache or fresh fetch."""
    if not force and GEMS_CACHE.exists():
        with open(GEMS_CACHE) as f:
            return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Try poe2db.tw first
    data = fetch_from_poe2db()
    if data is None:
        # Fall back to built-in tag reference
        data = build_tag_reference()

    with open(GEMS_CACHE, "w") as f:
        json.dump(data, f, indent=2)

    return data


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Cache PoE2 gem data for offline use"
    )
    parser.add_argument("--force", action="store_true",
                        help="Force re-fetch even if cached")
    parser.add_argument("--stats", action="store_true",
                        help="Show cache statistics")
    args = parser.parse_args()

    data = get_gem_data(force=args.force)

    if args.stats:
        supports = data.get("support_gems", {})
        print(f"Source: {data.get('source', 'unknown')}")
        print(f"Support gems indexed: {len(supports)}")
        effects = set(v.get("effect", "?") for v in supports.values())
        print(f"Effect types: {', '.join(sorted(effects))}")


if __name__ == "__main__":
    cli()
