#!/usr/bin/env python3
"""PoE2 Unique Item Analyzer.

Analyzes unique items for build-around potential, synergy with skills
and ascendancies, and recommends complementary items.

Usage:
    python unique_analyzer.py --unique "The Three Dragons"
    python unique_analyzer.py --skill "Explosive Grenade" --find-uniques
    python unique_analyzer.py --ascendancy "Gemling Legionnaire" --find-uniques
    python unique_analyzer.py --tag "attribute_stacking" --find-uniques
    python unique_analyzer.py --build "lightning caster" --suggest-uniques
    python unique_analyzer.py --slot "Body Armour" --find-uniques
    python unique_analyzer.py --compare "Mageblood" "Headhunter"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CACHE_FILE = Path.home() / ".cache" / "poe2-theory-crafter" / "uniques.json"


# Ascendancy → known archetypes (for broader matching)
ASCENDANCY_ARCHETYPES: dict[str, list[str]] = {
    "Stormweaver": ["lightning", "elemental", "caster", "spell", "mana", "shock"],
    "Infernalist": ["fire", "ignite", "minion", "elemental", "caster"],
    "Blood Mage": ["physical", "bleed", "life", "crit", "spell"],
    "Chronomancer": ["cooldown", "duration", "caster", "time"],
    "Titan": ["melee", "physical", "slam", "life", "armour", "stun"],
    "Warbringer": ["warcry", "melee", "physical", "fire", "totem"],
    "Deadeye": ["bow", "projectile", "speed", "elemental", "accuracy"],
    "Pathfinder": ["bow", "flask", "chaos", "poison", "speed"],
    "Witchhunter": ["crossbow", "grenade", "physical", "elemental", "explosion"],
    "Gemling Legionnaire": ["attribute", "stat_stacking", "gem", "crossbow"],
    "Invoker": ["elemental", "melee", "staff", "crit", "cold", "lightning"],
    "Acolyte of Chayula": ["chaos", "melee", "darkness", "life"],
}


SKILL_ARCHETYPES: dict[str, list[str]] = {
    "explosive grenade": ["fire", "aoe", "grenade", "crossbow", "detonator"],
    "spark": ["lightning", "spell", "projectile", "duration", "caster"],
    "fireball": ["fire", "spell", "aoe", "projectile", "caster"],
    "lightning arrow": ["lightning", "bow", "projectile", "aoe", "attack"],
    "ice shot": ["cold", "bow", "projectile", "aoe", "attack"],
    "earthquake": ["physical", "melee", "slam", "aoe", "duration"],
    "essence drain": ["chaos", "spell", "projectile", "dot", "caster"],
    "cyclone": ["physical", "melee", "aoe", "attack", "movement"],
    "arc": ["lightning", "spell", "chain", "caster"],
    "infernal cry": ["warcry", "fire", "aoe", "melee", "duration"],
    "skeletal warrior": ["minion", "physical", "spell", "duration"],
}


@dataclass
class UniqueMatch:
    """A unique item matched to a build."""
    name: str
    slot: str
    score: int
    match_reasons: list[str]
    key_mechanics: list[str]
    stats: list[str] = field(default_factory=list)


@dataclass
class BuildUniqueProfile:
    """Full unique item analysis for a build."""
    query: str
    query_type: str  # "skill", "ascendancy", "tag", "build", "slot"
    matches: list[UniqueMatch] = field(default_factory=list)
    build_enablers: list[UniqueMatch] = field(default_factory=list)
    complementary: list[UniqueMatch] = field(default_factory=list)

    def format(self) -> str:
        lines = [
            f"=== Unique Analysis: {self.query} ({self.query_type}) ===\n",
        ]

        if self.build_enablers:
            lines.append("--- Build-Enabling Uniques (high synergy) ---")
            for m in self.build_enablers:
                lines.append(f"\n  ★ {m.name} ({m.slot}) — Score: {m.score}")
                for reason in m.match_reasons:
                    lines.append(f"    ↳ {reason}")
                if m.key_mechanics:
                    lines.append(f"    Mechanics: {'; '.join(m.key_mechanics)}")
                if m.stats:
                    lines.append(f"    Key stats: {'; '.join(m.stats[:3])}")

        if self.complementary:
            lines.append("\n\n--- Complementary Uniques ---")
            for m in self.complementary:
                lines.append(f"\n  • {m.name} ({m.slot}) — Score: {m.score}")
                for reason in m.match_reasons:
                    lines.append(f"    ↳ {reason}")

        if not self.build_enablers and not self.complementary:
            lines.append("No matching uniques found.")
            lines.append("Try broader search terms or check poe2db.tw for the full unique list.")

        return "".join(lines)


def load_unique_data() -> dict:
    """Load unique item data from cache or build it."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    # Fall back to building from fetch_unique_data
    from fetch_unique_data import build_unique_reference
    return build_unique_reference()


def find_uniques_by_skill(skill_name: str, unique_data: dict) -> BuildUniqueProfile:
    """Find uniques that synergize with a specific skill."""
    skill_lower = skill_name.lower().strip()
    archetypes = SKILL_ARCHETYPES.get(skill_lower, [])

    if not archetypes:
        # Try partial match
        for key, vals in SKILL_ARCHETYPES.items():
            if skill_lower in key or key in skill_lower:
                archetypes = vals
                break

    if not archetypes:
        return BuildUniqueProfile(query=skill_name, query_type="skill")

    profile = BuildUniqueProfile(
        query=skill_name,
        query_type="skill",
    )
    _score_uniques(profile, archetypes, unique_data, skill_name)
    return profile


def find_uniques_by_ascendancy(asc_name: str, unique_data: dict) -> BuildUniqueProfile:
    """Find uniques that synergize with a specific ascendancy."""
    archetypes = ASCENDANCY_ARCHETYPES.get(asc_name, [])

    if not archetypes:
        # Case-insensitive match
        for key, vals in ASCENDANCY_ARCHETYPES.items():
            if key.lower() == asc_name.lower():
                archetypes = vals
                asc_name = key
                break

    profile = BuildUniqueProfile(
        query=asc_name,
        query_type="ascendancy",
    )
    _score_uniques(profile, archetypes, unique_data, asc_name)
    return profile


def find_uniques_by_tag(tag: str, unique_data: dict) -> BuildUniqueProfile:
    """Find uniques matching a mechanic tag."""
    profile = BuildUniqueProfile(query=tag, query_type="tag")

    uniques = unique_data.get("uniques", {})
    for name, info in uniques.items():
        tags = [t.lower() for t in info.get("tags", [])]
        tag_lower = tag.lower()
        if tag_lower in tags:
            match = UniqueMatch(
                name=name,
                slot=info.get("slot", "?"),
                score=10,
                match_reasons=[f"Tag match: {tag}"],
                key_mechanics=info.get("mechanics", []),
                stats=info.get("stats", []),
            )
            profile.complementary.append(match)

    profile.matches = profile.complementary[:]
    profile.matches.sort(key=lambda x: x.score, reverse=True)
    return profile


def find_uniques_by_slot(slot: str, unique_data: dict) -> BuildUniqueProfile:
    """Find uniques for a specific equipment slot."""
    profile = BuildUniqueProfile(query=slot, query_type="slot")

    uniques = unique_data.get("uniques", {})
    for name, info in uniques.items():
        if info.get("slot", "").lower() == slot.lower():
            match = UniqueMatch(
                name=name,
                slot=info.get("slot", "?"),
                score=5,
                match_reasons=[f"Slot match: {slot}"],
                key_mechanics=info.get("mechanics", []),
                stats=info.get("stats", []),
            )
            profile.complementary.append(match)

    profile.matches = profile.complementary[:]
    profile.matches.sort(key=lambda x: x.score, reverse=True)
    return profile


def find_uniques_by_build(description: str, unique_data: dict) -> BuildUniqueProfile:
    """Find uniques matching a build description using keyword matching."""
    description_lower = description.lower()
    archetypes = []

    # Build keyword mapping
    keyword_map = {
        "lightning": "lightning", "fire": "fire", "cold": "cold", "chaos": "chaos",
        "physical": "physical", "elemental": "elemental", "poison": "chaos",
        "bleed": "physical", "ignite": "fire", "shock": "lightning", "freeze": "cold",
        "caster": "caster", "spell": "caster", "melee": "melee", "bow": "bow",
        "crossbow": "crossbow", "grenade": "grenade", "minion": "minion",
        "attribute": "attribute_stacking", "stat": "stat_stacking",
        "life": "life", "energy shield": "es", "armour": "armour",
        "evasion": "evasion", "block": "block", "flask": "flask",
        "crit": "crit", "speed": "speed", "aoe": "aoe", "projectile": "projectile",
        "dot": "damage_over_time", "ailment": "ailment",
    }

    for keyword, archetype in keyword_map.items():
        if keyword in description_lower:
            archetypes.append(archetype)

    profile = BuildUniqueProfile(
        query=description,
        query_type="build",
    )
    _score_uniques(profile, archetypes, unique_data, description)
    return profile


def lookup_unique(name: str, unique_data: dict) -> str:
    """Look up detailed info for a specific unique item."""
    uniques = unique_data.get("uniques", {})

    # Exact match
    info = uniques.get(name)
    if not info:
        # Case-insensitive
        for key, val in uniques.items():
            if key.lower() == name.lower():
                info = val
                name = key
                break

    if not info:
        # Partial match
        candidates = [k for k in uniques if name.lower() in k.lower()]
        if candidates:
            lines = [f"Unique '{name}' not found. Did you mean:"]
            for c in candidates:
                lines.append(f"  • {c}")
            return "\n".join(lines)
        return f"Unique '{name}' not found in reference. Check poe2db.tw."

    lines = [
        f"=== {name} ===",
        f"Slot: {info.get('slot', '?')}",
    ]
    if info.get("weapon_type"):
        lines.append(f"Weapon Type: {info['weapon_type']}")
    if info.get("requirement"):
        reqs = ", ".join(
            f"{k.capitalize()}: {v}" for k, v in info["requirement"].items()
        )
        lines.append(f"Requirements: {reqs}")

    if info.get("stats"):
        lines.append("\nStats:")
        for s in info["stats"]:
            lines.append(f"  • {s}")

    if info.get("mechanics"):
        lines.append("\nUnique Mechanics:")
        for m in info["mechanics"]:
            lines.append(f"  • {m}")

    if info.get("build_around"):
        lines.append(f"\nBuild Archetypes: {', '.join(info['build_around'])}")

    if info.get("synergy_skills"):
        skills = ", ".join(info["synergy_skills"])
        lines.append(f"Synergistic Skills: {skills}")

    if info.get("synergy_ascendancies"):
        asc = ", ".join(info["synergy_ascendancies"])
        lines.append(f"Synergistic Ascendancies: {asc}")

    if info.get("tags"):
        lines.append(f"Tags: {', '.join(info['tags'])}")

    return "\n".join(lines)


def compare_uniques(name_a: str, name_b: str, unique_data: dict) -> str:
    """Side-by-side comparison of two unique items."""
    lines = [
        f"=== {name_a} vs {name_b} ===\n",
    ]

    uniques = unique_data.get("uniques", {})

    for name in (name_a, name_b):
        info = uniques.get(name)
        if not info:
            # Try case-insensitive
            for key, val in uniques.items():
                if key.lower() == name.lower():
                    info = val
                    name = key
                    break

        if not info:
            lines.append(f"--- {name}: NOT FOUND ---")
            continue

        lines.append(f"--- {name} ---")
        lines.append(f"  Slot: {info.get('slot', '?')}")
        if info.get("mechanics"):
            lines.append("  Key Mechanics:")
            for m in info["mechanics"]:
                lines.append(f"    • {m}")
        lines.append(f"  Archetypes: {', '.join(info.get('build_around', ['none']))}")
        lines.append("")

    return "\n".join(lines)


def _score_uniques(
    profile: BuildUniqueProfile,
    archetypes: list[str],
    unique_data: dict,
    query: str,
) -> None:
    """Score all uniques against a set of archetypes."""
    archetypes_lower = [a.lower() for a in archetypes]
    uniques = unique_data.get("uniques", {})

    for name, info in uniques.items():
        score = 0
        reasons: list[str] = []

        # Check build_around tags
        for ba in info.get("build_around", []):
            ba_lower = ba.lower()
            for archetype in archetypes_lower:
                if archetype in ba_lower or ba_lower in archetype:
                    score += 15
                    reasons.append(f"Build archetype '{ba}' matches '{archetype}'")

        # Check tags
        for tag in info.get("tags", []):
            tag_lower = tag.lower()
            for archetype in archetypes_lower:
                if archetype in tag_lower or tag_lower in archetype:
                    score += 10
                    reasons.append(f"Mechanic tag '{tag}' matches '{archetype}'")

        # Check synergy skills
        for skill in info.get("synergy_skills", []):
            if skill.lower() in query.lower() or query.lower() in skill.lower():
                score += 20
                reasons.append(f"Direct synergy with '{skill}'")

        # Check synergy ascendancies
        for asc in info.get("synergy_ascendancies", []):
            if asc.lower() in query.lower() or query.lower() in asc.lower():
                score += 20
                reasons.append(f"Direct ascendancy synergy: {asc}")

        # Check mechanics text for keyword matches
        mechanic_text = " ".join(info.get("mechanics", [])).lower()
        for archetype in archetypes_lower:
            if archetype in mechanic_text:
                score += 8
                reasons.append(f"Mechanic mentions '{archetype}'")

        if score > 0:
            match = UniqueMatch(
                name=name,
                slot=info.get("slot", "?"),
                score=score,
                match_reasons=reasons[:3],  # top 3 reasons
                key_mechanics=info.get("mechanics", []),
                stats=info.get("stats", []),
            )
            profile.matches.append(match)

    # Sort and categorize
    profile.matches.sort(key=lambda x: x.score, reverse=True)
    profile.build_enablers = [m for m in profile.matches if m.score >= 20]
    profile.complementary = [m for m in profile.matches if m.score < 20]


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Unique Item Analyzer — find build-around uniques",
    )
    parser.add_argument("--unique", help="Look up a specific unique item")
    parser.add_argument("--skill", help="Find uniques for a skill (e.g. 'Explosive Grenade')")
    parser.add_argument("--ascendancy", help="Find uniques for an ascendancy")
    parser.add_argument("--tag", help="Find uniques by mechanic tag")
    parser.add_argument("--build", help="Find uniques matching a build description")
    parser.add_argument("--slot", help="Find uniques for a specific equipment slot")
    parser.add_argument("--compare", nargs=2, metavar=("UNIQUE_A", "UNIQUE_B"),
                        help="Compare two unique items")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh unique data cache")

    args = parser.parse_args()

    # Build/get unique data
    if args.refresh:
        from fetch_unique_data import get_unique_data
        unique_data = get_unique_data(force=True)
    else:
        unique_data = load_unique_data()

    if args.unique:
        if args.json:
            import json
            name = args.unique
            uniques = unique_data.get("uniques", {})
            info = uniques.get(name) or next((v for k,v in uniques.items() if k.lower()==name.lower()), {})
            print(json.dumps(info, indent=2, default=str))
        else:
            print(lookup_unique(args.unique, unique_data))

    elif args.skill:
        profile = find_uniques_by_skill(args.skill, unique_data)
        if args.json:
            import json
            print(json.dumps({
                "query": profile.query,
                "query_type": profile.query_type,
                "build_enablers": [{"name": m.name, "slot": m.slot, "score": m.score} for m in profile.build_enablers],
                "complementary": [{"name": m.name, "slot": m.slot, "score": m.score} for m in profile.complementary],
            }, indent=2))
        else:
            print(profile.format())

    elif args.ascendancy:
        profile = find_uniques_by_ascendancy(args.ascendancy, unique_data)
        print(profile.format())

    elif args.tag:
        profile = find_uniques_by_tag(args.tag, unique_data)
        print(profile.format())

    elif args.build:
        profile = find_uniques_by_build(args.build, unique_data)
        print(profile.format())

    elif args.slot:
        profile = find_uniques_by_slot(args.slot, unique_data)
        print(profile.format())

    elif args.compare:
        print(compare_uniques(args.compare[0], args.compare[1], unique_data))

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python unique_analyzer.py --unique 'The Three Dragons'")
        print("  python unique_analyzer.py --skill 'Explosive Grenade' --find-uniques")
        print("  python unique_analyzer.py --ascendancy 'Gemling Legionnaire' --find-uniques")
        print("  python unique_analyzer.py --compare 'Mageblood' 'Headhunter'")


if __name__ == "__main__":
    cli()
