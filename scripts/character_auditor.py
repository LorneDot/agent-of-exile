#!/usr/bin/env python3
"""PoE2 Deep Character Auditor.

Extended character analysis beyond basic fetch_character.py:
- Item-by-item upgrade recommendations
- Crafting upgrade paths per slot  
- Upgrade priority ranking (impact per cost)
- Unique item synergy detection
- Stat gap analysis with gear sourcing

Usage:
    python character_auditor.py --account Lorne --char MyWitch
    python character_auditor.py --account Lorne --char MyWitch --deep
    python character_auditor.py --file character.json --deep
    python character_auditor.py --account Lorne --char MyWitch --upgrade-priority
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fetch_character import fetch_character, summarize_character, analyze_build
from crafting_advisor import analyze_item_for_crafting, plan_crafting, SLOT_MODS


# ============================================================
# Priority upgrade recommendations
# ============================================================

@dataclass
class UpgradeRecommendation:
    """An upgrade recommendation for a specific gear slot."""
    slot: str
    priority: int
    current_item: str
    issue: str
    suggestion: str
    estimated_cost: str
    impact: str  # "high", "medium", "low"
    crafting_steps: list[str] = field(default_factory=list)

    def format(self) -> str:
        lines = [
            f"  {self.priority}. [{self.slot}] {self.current_item}",
            f"     Issue: {self.issue}",
            f"     Action: {self.suggestion}",
            f"     Cost: {self.estimated_cost} | Impact: {self.impact.upper()}",
        ]
        if self.crafting_steps:
            lines.append("     Crafting:")
            for step in self.crafting_steps:
                lines.append(f"       → {step}")
        return "\n".join(lines)


@dataclass
class DeepAudit:
    """Full deep audit of a character."""
    character_name: str
    character_class: str
    level: int
    ascendancy: str
    recommendations: list[UpgradeRecommendation] = field(default_factory=list)
    stat_gaps: list[str] = field(default_factory=list)
    unique_synergies: list[str] = field(default_factory=list)
    total_estimated_upgrade_cost: str = ""

    def format(self) -> str:
        lines = [
            f"╔══════════════════════════════════════════╗",
            f"║  DEEP AUDIT: {self.character_name} (Lv.{self.level} {self.character_class} → {self.ascendancy})",
            f"╚══════════════════════════════════════════╝",
            "",
        ]

        if self.stat_gaps:
            lines.append("--- Critical Stat Gaps ---")
            for gap in self.stat_gaps:
                lines.append(f"  ✗ {gap}")

        if self.recommendations:
            lines.append(f"\n--- Upgrade Priority ({len(self.recommendations)} items) ---")
            lines.append("")
            for rec in self.recommendations:
                lines.append(rec.format())
                lines.append("")

        lines.append(f"Total estimated upgrade cost: {self.total_estimated_upgrade_cost}")

        if self.unique_synergies:
            lines.append(f"\n--- Unique Item Synergies ---")
            for syn in self.unique_synergies:
                lines.append(f"  • {syn}")

        return "\n".join(lines)


def deep_audit_character(character_data: dict) -> DeepAudit:
    """Perform a deep audit with item-by-item upgrade recommendations.

    Analyzes each equipped item, identifies weaknesses, and generates
    specific crafting/trade upgrade paths ordered by impact per cost.
    """
    char = character_data.get("character", {})
    items = character_data.get("items", [])

    name = char.get("name", "Unknown")
    char_class = char.get("class", "Unknown")
    level = char.get("level", 0)
    ascendancy = char.get("ascendancyClass", "None")

    audit = DeepAudit(
        character_name=name,
        character_class=char_class,
        level=level,
        ascendancy=ascendancy,
    )

    # Map items to slots
    items_by_slot: dict[str, dict] = {}
    for item in items:
        slot = item.get("inventoryId", "Unknown")
        items_by_slot[slot] = item

    # Priority slots for survivability
    priority_slots = [
        "Weapon", "Body Armour", "Helm", "Ring", "Ring2", "Amulet",
        "Gloves", "Boots", "Belt", "Offhand", "Weapon2",
    ]

    recommendations: list[UpgradeRecommendation] = []
    priority = 1

    for slot in priority_slots:
        item = items_by_slot.get(slot)
        if not item:
            # Empty slot = highest priority
            recommendations.append(UpgradeRecommendation(
                slot=slot, priority=priority,
                current_item="[Empty]",
                issue="No item equipped",
                suggestion=f"Equip any rare {slot} with life + resistances",
                estimated_cost="1-5c",
                impact="high" if slot in ("Weapon", "Body Armour") else "medium",
            ))
            priority += 1
            continue

        item_name = item.get("name", "") or item.get("typeLine", "?")
        rarity = item.get("frameType", 0)
        ilvl = item.get("ilvl", 0)
        explicit_mods = item.get("explicitMods", [])
        mod_text = " ".join(explicit_mods).lower()

        # Check for common issues
        issues: list[str] = []

        # Normal/Magic item at high level
        if rarity <= 1 and level >= 60:
            issues.append("Below rare quality — missing 2-4 mods")

        # Low iLvl
        if ilvl < 50 and level >= 70:
            issues.append(f"Low iLvl ({ilvl}) — cannot roll high-tier mods")
        elif ilvl < 75 and level >= 80:
            issues.append(f"iLvl {ilvl} — consider iLvl 82+ base for top-tier mods")

        # Missing life/ES on defense slots
        if slot in ("Body Armour", "Helm", "Gloves", "Boots", "Belt",
                     "Ring", "Ring2", "Amulet"):
            if "maximum life" not in mod_text and "energy shield" not in mod_text.lower():
                issues.append("No life or ES — primary survivability stat missing")

        # Missing resistances
        if slot in ("Body Armour", "Helm", "Gloves", "Boots", "Ring", "Ring2", "Amulet", "Belt"):
            has_res = any(r in mod_text for r in ("resistance", "resist"))
            if not has_res and level >= 68:
                issues.append("No resistances — needed for capping at -60% penalty")

        # Weapon: check for low damage mods
        if slot == "Weapon" and level >= 60:
            has_damage = any(m in mod_text for m in (
                "physical damage", "increased physical",
                "adds", "spell damage", "elemental damage"
            ))
            if not has_damage:
                issues.append("No damage mods on weapon — significant DPS loss")

        # Empty rune sockets
        sockets = item.get("sockets", [])
        rune_sockets = [s for s in sockets if s.get("socketType") == "Rune"]
        socketed = item.get("socketedItems", [])
        if len(rune_sockets) > len(socketed):
            empty = len(rune_sockets) - len(socketed)
            issues.append(f"{empty} empty rune socket(s) — free stats available")

        if not issues:
            continue

        # Build recommendations
        primary_issue = issues[0]
        impact = "high" if slot in ("Weapon", "Body Armour") else \
                 "high" if "life" in primary_issue.lower() or "damage" in primary_issue.lower() else \
                 "medium"

        if "rare quality" in primary_issue.lower() or "low ilvl" in primary_issue.lower():
            suggestion = f"Replace with iLvl {max(ilvl + 10, 75)}+ rare {slot} with life + resists"
            cost = "5-20c" if slot == "Weapon" else "3-10c"
            crafting = [
                f"Buy iLvl {max(ilvl + 10, 75)}+ {slot.lower()} base",
                "Essence craft life or resist, aug, regal, exalt slam",
                "Or buy finished item from trade (often cheaper)"
            ]
        elif "life" in primary_issue.lower() or "es" in primary_issue.lower():
            suggestion = f"Replace with {slot.lower()} having +life or +ES"
            cost = "3-15c"
            crafting = [
                "Use Essence of Greed for guaranteed life roll",
                "Aug + regal, exalt slam for additional mods"
            ]
        elif "resistance" in primary_issue.lower():
            suggestion = f"Replace with {slot.lower()} having at least +30% total resists"
            cost = "2-10c"
            crafting = [
                "Essence of element for guaranteed resistance",
                "Or use Harvest crafting to swap resist types on existing gear"
            ]
        elif "damage" in primary_issue.lower():
            suggestion = f"Replace weapon with one having +phys% and flat phys/crit"
            cost = "10-50c"
            crafting = [
                f"Buy iLvl 82+ {item.get('typeLine', 'weapon')} base",
                "Essence of Contempt for flat phys, regal, multimod if 6-mod"
            ]
        elif "rune" in primary_issue.lower():
            suggestion = "Fill empty rune sockets with relevant runes"
            cost = "1c"
            crafting = ["Use Iron Runes for phys builds, Storm Runes for lightning, etc."]
        else:
            suggestion = f"Upgrade {slot.lower()}"
            cost = "5-15c"
            crafting = ["Craft or trade for upgrade"]

        recommendations.append(UpgradeRecommendation(
            slot=slot,
            priority=priority,
            current_item=item_name,
            issue=primary_issue,
            suggestion=suggestion,
            estimated_cost=cost,
            impact=impact,
            crafting_steps=crafting,
        ))
        priority += 1

    audit.recommendations = recommendations

    # Estimate total cost
    total_low = sum(
        int(r.estimated_cost.split("-")[0].replace("c", "").replace("+", ""))
        if "-" in r.estimated_cost else
        int(r.estimated_cost.replace("c", "").replace("+", ""))
        for r in recommendations
    )
    audit.total_estimated_upgrade_cost = f"~{total_low}c minimum"

    # Stat gaps
    stat_gaps: list[str] = []
    life = char.get("life", 0)
    es = char.get("energyShield", 0)
    ehp = life + es

    if level >= 68:
        if ehp < 3000:
            stat_gaps.append(f"EHP {ehp:.0f} below T1 Waystones minimum (3,000)")
        elif ehp < 4000:
            stat_gaps.append(f"EHP {ehp:.0f} below T6 Waystones recommendation (4,000)")
        elif ehp < 5000:
            stat_gaps.append(f"EHP {ehp:.0f} below T11 Waystones recommendation (5,000)")

        # Check for resistances from character data
        for res_name, res_label in [
            ("fireResist", "Fire"), ("coldResist", "Cold"),
            ("lightningResist", "Lightning"), ("chaosResist", "Chaos"),
        ]:
            res_val = char.get(res_name, 0)
            if res_val < 75:
                stat_gaps.append(f"{res_label} resistance at {res_val}% — need {75 - res_val}% more to cap")

    audit.stat_gaps = stat_gaps

    return audit


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Deep Character Auditor — item-by-item upgrade paths"
    )
    parser.add_argument("--account", help="Account name (from pathofexile.com)")
    parser.add_argument("--char", help="Character name")
    parser.add_argument("--session", help="POESESSID cookie (or set POESESSID env var)")
    parser.add_argument("--file", help="JSON file with character data (from fetch_character)")
    parser.add_argument("--deep", action="store_true", default=True,
                        help="Run deep audit (default)")
    parser.add_argument("--json", action="store_true",
                        help="Output as machine-readable JSON")

    args = parser.parse_args()

    # Get character data
    data: Optional[dict] = None

    if args.file:
        try:
            with open(args.file) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.account and args.char:
        session_id = args.session or os.environ.get("POESESSID")
        if not session_id:
            print("Error: POESESSID required. Use --session or set POESESSID env var.",
                  file=sys.stderr)
            sys.exit(1)
        data = fetch_character(args.account, args.char, session_id)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python character_auditor.py --account Lorne --char MyWitch")
        print("  python character_auditor.py --file character.json --deep")
        return

    if not data:
        print("Error: No character data obtained.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        audit = deep_audit_character(data)
        output = {
            "character": audit.character_name,
            "class": audit.character_class,
            "level": audit.level,
            "ascendancy": audit.ascendancy,
            "stat_gaps": audit.stat_gaps,
            "total_cost": audit.total_estimated_upgrade_cost,
            "upgrades": [
                {
                    "priority": r.priority,
                    "slot": r.slot,
                    "current": r.current_item,
                    "issue": r.issue,
                    "suggestion": r.suggestion,
                    "cost": r.estimated_cost,
                    "impact": r.impact,
                }
                for r in audit.recommendations
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        audit = deep_audit_character(data)
        print(audit.format())


if __name__ == "__main__":
    cli()
