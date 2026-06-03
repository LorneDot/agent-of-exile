#!/usr/bin/env python3
"""PoE2 Gem Linker — Auto-support matching by tag compatibility.

Given a skill gem name (or its tags), finds compatible support gems
ranked by tag match count and effect type priority.

Usage:
    python gem_linker.py --tags "Attack AoE Projectile Grenade Fire Detonator"
    python gem_linker.py --tags "Spell AoE Fire" --max 10
    python gem_linker.py --skill "Explosive Grenade"  # human-friendly alias
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CACHE_FILE = Path.home() / ".cache" / "poe2-theory-crafter" / "gems.json"

EFFECT_PRIORITY = {
    "more_damage": 10,
    "more_projectiles": 9,
    "penetration": 8,
    "extra_use": 7,
    "added_damage": 7,
    "faster_detonation": 6,
    "pierce": 5,
    "chain": 5,
    "fork": 5,
    "ailment_spread": 5,
    "ailment_effect": 4,
    "impale": 4,
    "increased_speed": 4,
    "increased_aoe": 3,
    "increased_cast_speed": 3,
    "increased_duration": 2,
    "cost_reduction": 2,
    "buff": 2,
    "debuff": 2,
    "utility": 1,
    "cost_conversion": 1,
    "magic_find": 0,
}

# Human-friendly skill name → common tags mapping
SKILL_TAGS: dict[str, list[str]] = {
    "explosive grenade": ["Attack", "AoE", "Projectile", "Grenade", "Fire", "Detonator"],
    "explosive shot": ["Attack", "Projectile", "Fire", "Crossbow"],
    "fireball": ["Spell", "AoE", "Projectile", "Fire"],
    "spark": ["Spell", "Projectile", "Lightning", "Duration"],
    "lightning arrow": ["Attack", "AoE", "Projectile", "Lightning", "Bow"],
    "ice shot": ["Attack", "AoE", "Projectile", "Cold", "Bow"],
    "skeletal warrior": ["Spell", "Minion", "Duration"],
    "flame wall": ["Spell", "AoE", "Fire", "Duration"],
    "arc": ["Spell", "Lightning", "Chain"],
    "essence drain": ["Spell", "Projectile", "Chaos", "DamageOverTime"],
    "contagion": ["Spell", "AoE", "Chaos", "DamageOverTime"],
    "bone storm": ["Spell", "Projectile", "Physical", "Duration"],
    "earthquake": ["Attack", "AoE", "Melee", "Slam", "Duration"],
    "infernal cry": ["Warcry", "AoE", "Fire", "Duration"],
    "shockwave totem": ["Attack", "Totem", "AoE", "Melee", "Slam"],
    "armour breaker": ["Attack", "AoE", "Melee", "Strike", "Physical"],
    "perfect strike": ["Attack", "Melee", "Strike", "Fire"],
    "grenade launcher": ["Attack", "AoE", "Projectile", "Grenade", "Fire"],
    "oil grenade": ["Attack", "AoE", "Projectile", "Grenade", "Fire"],
    "gas grenade": ["Attack", "AoE", "Projectile", "Grenade", "Chaos"],
    "flash grenade": ["Attack", "AoE", "Projectile", "Grenade", "Lightning"],
}


def load_gem_data() -> dict:
    """Load gem data from cache."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    # If no cache, use empty — gem linker will still work with tag matching
    return {"source": "empty", "support_gems": {}}


def find_supports(
    skill_tags: list[str],
    gem_data: dict,
    max_results: int = 10,
) -> list[tuple[str, int, str, str]]:
    """Find compatible support gems ranked by tag match + effect priority.

    Returns list of (gem_name, score, effect, match_reason).
    """
    supports = gem_data.get("support_gems", {})
    results: list[tuple[str, int, str, str]] = []

    skill_tags_lower = [t.lower() for t in skill_tags]

    for gem_name, info in supports.items():
        support_tags = [t.lower() for t in info.get("tags", [])]
        effect = info.get("effect", "unknown")

        # Count matching tags
        matches = sum(1 for t in support_tags if t in skill_tags_lower)

        # If support has "Any" tag, it matches everything at low priority
        if "any" in support_tags:
            matches = 1

        if matches > 0:
            # Score = tag matches × 10 + effect priority
            effect_score = EFFECT_PRIORITY.get(effect, 0)
            score = matches * 10 + effect_score

            # Build match reason
            matched = [t for t in support_tags if t in skill_tags_lower]
            reason = f"Matches tags: {', '.join(matched)}"
            if effect_score >= 8:
                reason += " (high-impact support)"

            results.append((gem_name, score, effect, reason))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:max_results]


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Find compatible support gems for a skill"
    )
    parser.add_argument("--tags", nargs="+",
                        help="Skill gem tags (e.g., Attack AoE Fire)")
    parser.add_argument("--skill",
                        help="Skill name (e.g., 'Explosive Grenade')")
    parser.add_argument("--max", type=int, default=10,
                        help="Maximum results (default: 10)")
    args = parser.parse_args()

    if args.skill:
        skill_lower = args.skill.lower().strip()
        tags = SKILL_TAGS.get(skill_lower)
        if tags:
            print(f"Tags for '{args.skill}': {', '.join(tags)}")
        else:
            print(f"Skill '{args.skill}' not in built-in reference.",
                  file=sys.stderr)
            print("Use --tags to specify tags manually, or look up on poe2db.tw.",
                  file=sys.stderr)
            sys.exit(1)
    elif args.tags:
        tags = args.tags
    else:
        parser.print_help()
        sys.exit(1)

    gem_data = load_gem_data()
    results = find_supports(tags, gem_data, args.max)

    if not results:
        print("No matching supports found in cache.")
        print("Try: python fetch_gem_data.py --force")
        print("Or look up manually: poe2db.tw → Support Gems")
        return

    print(f"\n--- Top {len(results)} Support Gems ---")
    for i, (name, score, effect, reason) in enumerate(results, 1):
        print(f"  {i:2d}. {name} (score: {score})")
        print(f"      Effect: {effect} | {reason}")


if __name__ == "__main__":
    cli()
