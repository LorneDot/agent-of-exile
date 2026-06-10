#!/usr/bin/env python3
"""PoE2 Build Orchestration Pipeline.

Chains tools together into end-to-end build generation.

Subcommands:
    full-build          Route → Gems → DPS → Gear → Craft → Trade → Export
    character-upgrade   Fetch → Audit → Craft → Trade
    validate            Route → Stats → DPS → Danger check
    craft-vs-buy        Advisor → Simulator → Trade
    quick-check         Fast pass: stats + DPS + danger

Usage:
    python build_pipeline.py full-build --class Mercenary \
        --ascendancy "Gemling Legionnaire" --skill "Explosive Grenade" \
        --targets 58714 29514 17882 --level 80

    python build_pipeline.py validate --spec build.json

    python build_pipeline.py character-upgrade --account Lorne --char MyWitch

    python build_pipeline.py craft-vs-buy --slot "Ring" --desired-mods life_flat fire_res cold_res
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ============================================================
# Unified BuildSpec
# ============================================================

@dataclass
class BuildSkill:
    """A skill gem with support gems."""
    id: str
    name: str = ""
    level: int = 20
    quality: int = 20
    supports: list[str] = field(default_factory=list)


@dataclass
class BuildAura:
    """An aura or buff."""
    name: str
    enabled: bool = True


@dataclass
class BuildGearItem:
    """A single equipped item."""
    slot: str
    name: str = ""
    base: str = ""
    ilvl: int = 0
    rarity: str = "Rare"  # Normal, Magic, Rare, Unique
    explicit_mods: list[str] = field(default_factory=list)
    implicit_mods: list[str] = field(default_factory=list)


@dataclass
class BuildCraftPlan:
    """Crafting plan for a slot."""
    slot: str
    desired_mods: list[str] = field(default_factory=list)
    method: str = "essence_regal_exalt"
    success_probability: float = 0.0
    expected_attempts: float = 0.0
    estimated_cost: str = ""


@dataclass
class BuildTradeLink:
    """Trade search for a slot."""
    slot: str
    url: str = ""
    estimated_price: str = ""


@dataclass
class BuildDps:
    """DPS simulation result."""
    skill: str = ""
    base_dps: float = 0.0
    raw_dps: float = 0.0
    effective_dps: float = 0.0
    pinnacle_dps: float = 0.0
    monster_tier: str = "T16"
    active_auras: list[str] = field(default_factory=list)
    active_charges: dict[str, int] = field(default_factory=dict)


@dataclass
class BuildStats:
    """Computed defensive/offensive stats."""
    life: float = 0.0
    es: float = 0.0
    ehp: float = 0.0
    fire_res: float = 0.0
    cold_res: float = 0.0
    lightning_res: float = 0.0
    chaos_res: float = 0.0
    armour: float = 0.0
    evasion: float = 0.0
    dps: float = 0.0
    danger_summary: str = ""


@dataclass
class BuildSpec:
    """Complete build specification shared across all tools."""
    # Meta
    class_name: str = ""
    ascendancy: str = ""
    level: int = 80
    risk_profile: str = "balanced"  # glass_cannon, balanced, tanky, hardcore, ssf
    notes: str = ""

    # Tree
    allocated_passives: list[str] = field(default_factory=list)
    ascendancy_nodes: list[str] = field(default_factory=list)
    travel_efficiency_grade: str = ""
    clusters: list[dict] = field(default_factory=list)

    # Skills
    main_skill: Optional[BuildSkill] = None
    aura_setup: list[BuildAura] = field(default_factory=list)

    # Gear
    gear: dict[str, BuildGearItem] = field(default_factory=dict)

    # Results (populated by pipeline)
    stats: BuildStats = field(default_factory=BuildStats)
    dps: BuildDps = field(default_factory=BuildDps)
    crafting_plans: dict[str, BuildCraftPlan] = field(default_factory=dict)
    trade_links: dict[str, BuildTradeLink] = field(default_factory=dict)
    unique_recommendations: list[str] = field(default_factory=list)

    # Meta
    pipeline_stages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict, skipping None/unset."""
        d: dict = {}
        # Meta
        d["class_name"] = self.class_name
        d["ascendancy"] = self.ascendancy
        d["level"] = self.level
        d["risk_profile"] = self.risk_profile
        if self.notes:
            d["notes"] = self.notes

        # Tree
        d["allocated_passives"] = self.allocated_passives
        if self.ascendancy_nodes:
            d["ascendancy_nodes"] = self.ascendancy_nodes
        if self.travel_efficiency_grade:
            d["travel_efficiency_grade"] = self.travel_efficiency_grade
        if self.clusters:
            d["clusters"] = self.clusters

        # Skills
        if self.main_skill:
            d["main_skill"] = asdict(self.main_skill)

        # Auras
        if self.aura_setup:
            d["auras"] = [asdict(a) for a in self.aura_setup]

        # Gear
        if self.gear:
            d["gear"] = {k: asdict(v) for k, v in self.gear.items()}

        # Stats
        d["stats"] = asdict(self.stats)

        # DPS
        if self.dps.skill:
            d["dps"] = asdict(self.dps)

        # Crafting
        if self.crafting_plans:
            d["crafting"] = {k: asdict(v) for k, v in self.crafting_plans.items()}

        # Trade
        if self.trade_links:
            d["trade"] = {k: asdict(v) for k, v in self.trade_links.items()}

        # Uniques
        if self.unique_recommendations:
            d["unique_recommendations"] = self.unique_recommendations

        d["pipeline_stages"] = self.pipeline_stages
        if self.errors:
            d["errors"] = self.errors

        return d

    def save(self, path: str) -> None:
        """Save build spec to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "BuildSpec":
        """Load build spec from JSON file."""
        with open(path) as f:
            d = json.load(f)

        spec = cls(
            class_name=d.get("class_name", ""),
            ascendancy=d.get("ascendancy", ""),
            level=d.get("level", 80),
            risk_profile=d.get("risk_profile", "balanced"),
            notes=d.get("notes", ""),
            allocated_passives=d.get("allocated_passives", []),
            ascendancy_nodes=d.get("ascendancy_nodes", []),
            travel_efficiency_grade=d.get("travel_efficiency_grade", ""),
            clusters=d.get("clusters", []),
            pipeline_stages=d.get("pipeline_stages", []),
            errors=d.get("errors", []),
        )

        # Main skill
        ms = d.get("main_skill")
        if ms:
            spec.main_skill = BuildSkill(**ms)

        # Auras
        for a in d.get("auras", []):
            spec.aura_setup.append(BuildAura(**a))

        # Gear
        for slot, gd in d.get("gear", {}).items():
            spec.gear[slot] = BuildGearItem(**gd)

        # Stats
        if "stats" in d:
            spec.stats = BuildStats(**d["stats"])

        # DPS
        if "dps" in d:
            spec.dps = BuildDps(**d["dps"])

        # Crafting
        for slot, cd in d.get("crafting", {}).items():
            spec.crafting_plans[slot] = BuildCraftPlan(**cd)

        # Trade
        for slot, td in d.get("trade", {}).items():
            spec.trade_links[slot] = BuildTradeLink(**td)

        # Uniques
        spec.unique_recommendations = d.get("unique_recommendations", [])

        return spec


# ============================================================
# Pipeline stages
# ============================================================

def stage_tree(spec: BuildSpec, targets: list[str]) -> bool:
    """Stage 1: Route the passive tree."""
    try:
        import subprocess
        cwd = Path(__file__).parent
        result = subprocess.run([
            sys.executable, str(cwd / "route_tree.py"),
            "--class", spec.class_name,
            "--targets", *targets,
            "--level", str(spec.level),
            "--json",
        ], capture_output=True, text=True, cwd=str(cwd))
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            spec.allocated_passives = [str(p) for p in data.get("path", [])]
            spec.pipeline_stages.append("tree")
            return True
        else:
            spec.errors.append(f"Tree routing failed: {result.stderr[:200]}")
    except Exception as e:
        spec.errors.append(f"Tree routing failed: {e}")
    return False


def stage_gems(spec: BuildSpec) -> bool:
    """Stage 2: Analyze gems and find supports."""
    if not spec.main_skill:
        spec.errors.append("No main skill specified")
        return False
    try:
        from gem_analyzer import simulate_dps, optimize_links
        sim = simulate_dps(spec.main_skill.name, spec.main_skill.level,
                          max(spec.main_skill.level // 10 + 3, 4))
        spec.main_skill.supports = sim.supports
        spec.dps.skill = spec.main_skill.name
        spec.dps.base_dps = sim.estimated_dps
        spec.pipeline_stages.append("gems")
        return True
    except Exception as e:
        spec.errors.append(f"Gem analysis failed: {e}")
    return False


def stage_dps(spec: BuildSpec) -> bool:
    """Stage 3: Full DPS simulation."""
    if not spec.main_skill:
        return False
    try:
        from dps_simulator import simulate_full_dps
        aura_names = [a.name for a in spec.aura_setup if a.enabled]
        result = simulate_full_dps(
            spec.main_skill.name,
            gem_level=spec.main_skill.level,
            links=len(spec.main_skill.supports) + 1,
            auras=aura_names,
            monster_tier="T16",
        )
        spec.dps.raw_dps = result.raw_dps
        spec.dps.effective_dps = result.effective_dps
        spec.dps.pinnacle_dps = result.pinnacle_dps
        spec.dps.monster_tier = "T16"
        spec.dps.active_auras = aura_names
        spec.stats.dps = result.effective_dps
        spec.pipeline_stages.append("dps")
        return True
    except Exception as e:
        spec.errors.append(f"DPS simulation failed: {e}")
    return False


def stage_craft(spec: BuildSpec) -> bool:
    """Stage 4: Generate crafting plans for key slots."""
    key_slots = ["Body Armour", "Helm", "Ring", "Amulet", "Boots", "Gloves", "Belt"]
    if spec.main_skill and "attack" in str(spec.main_skill.tags if hasattr(spec.main_skill, 'tags') else "").lower():
        key_slots.insert(0, "Weapon")

    try:
        from craft_simulator import simulate_craft

        for slot in key_slots[:5]:  # Top 5 slots
            # Default desired mods per slot
            if slot == "Weapon":
                desired = ["increased_phys", "flat_phys", "attack_speed"]
            elif slot in ("Ring", "Amulet"):
                desired = ["life_flat", "fire_res", "cold_res"]
            else:
                desired = ["life_flat", "fire_res", "cold_res"]

            sim = simulate_craft(slot, desired, "essence_regal_exalt")
            spec.crafting_plans[slot] = BuildCraftPlan(
                slot=slot,
                desired_mods=desired,
                method=sim.method.name,
                success_probability=sim.overall_success_probability,
                expected_attempts=sim.expected_attempts,
                estimated_cost=sim.estimated_total_cost,
            )

        spec.pipeline_stages.append("craft")
        return True
    except Exception as e:
        spec.errors.append(f"Craft planning failed: {e}")
    return False


def stage_trade(spec: BuildSpec) -> bool:
    """Stage 5: Generate trade search links."""
    try:
        from trade_finder import build_trade_url

        for slot, plan in list(spec.crafting_plans.items())[:5]:
            url = build_trade_url(slot, plan.desired_mods)
            spec.trade_links[slot] = BuildTradeLink(slot=slot, url=url)

        spec.pipeline_stages.append("trade")
        return True
    except Exception as e:
        spec.errors.append(f"Trade search failed: {e}")
    return False


def stage_stats(spec: BuildSpec) -> bool:
    """Stage 6: Compute stats."""
    try:
        from calc_stats import compute_stats

        stats_input = {
            "className": spec.class_name,
            "ascendClassName": spec.ascendancy,
            "level": spec.level,
        }
        result = compute_stats(stats_input)
        spec.stats.life = result.defence.life
        spec.stats.es = result.defence.energy_shield
        spec.stats.ehp = result.defence.ehp
        spec.stats.fire_res = result.defence.fire_res
        spec.stats.cold_res = result.defence.cold_res
        spec.stats.lightning_res = result.defence.lightning_res
        spec.stats.chaos_res = result.defence.chaos_res
        spec.stats.armour = result.defence.armour
        spec.stats.evasion = result.defence.evasion
        spec.pipeline_stages.append("stats")
        return True
    except Exception as e:
        spec.errors.append(f"Stats calculation failed: {e}")
    return False


def stage_uniques(spec: BuildSpec) -> bool:
    """Stage 7: Find unique item synergies."""
    try:
        from unique_analyzer import find_uniques_by_ascendancy, load_unique_data
        unique_data = load_unique_data()
        profile = find_uniques_by_ascendancy(spec.ascendancy, unique_data)
        spec.unique_recommendations = [
            m.name for m in profile.build_enablers[:3]
        ]
        spec.pipeline_stages.append("uniques")
        return True
    except Exception as e:
        spec.errors.append(f"Unique analysis failed: {e}")
    return False


# ============================================================
# Pipeline runners
# ============================================================

def pipeline_full_build(
    class_name: str,
    ascendancy: str,
    skill_name: str,
    targets: list[str],
    level: int = 80,
    auras: Optional[list[str]] = None,
    risk_profile: str = "balanced",
) -> BuildSpec:
    """Run the full build pipeline."""
    print(f"\n{'='*60}")
    print(f"  AGENT OF EXILE — FULL BUILD PIPELINE")
    print(f"  {class_name} → {ascendancy} | {skill_name} | Level {level}")
    print(f"{'='*60}\n")

    spec = BuildSpec(
        class_name=class_name,
        ascendancy=ascendancy,
        level=level,
        risk_profile=risk_profile,
    )

    # Main skill
    from gem_analyzer import SKILL_GEM_DATA
    skill_data = SKILL_GEM_DATA.get(skill_name)
    spec.main_skill = BuildSkill(
        id=f"SkillGem{skill_name.replace(' ', '')}",
        name=skill_name,
        level=20,
        quality=20,
    )

    # Auras
    if auras:
        spec.aura_setup = [BuildAura(name=a) for a in auras]

    stages = [
        ("1/7  Tree Routing", lambda: stage_tree(spec, targets)),
        ("2/7  Gem Analysis", lambda: stage_gems(spec)),
        ("3/7  DPS Simulation", lambda: stage_dps(spec)),
        ("4/7  Craft Planning", lambda: stage_craft(spec)),
        ("5/7  Trade Search", lambda: stage_trade(spec)),
        ("6/7  Stat Calculation", lambda: stage_stats(spec)),
        ("7/7  Unique Synergies", lambda: stage_uniques(spec)),
    ]

    for label, fn in stages:
        print(f"  {label}...", end=" ", flush=True)
        ok = fn()
        print("✓" if ok else "✗")
        if not ok:
            for err in spec.errors[-1:]:
                print(f"    → {err}")

    return spec


def pipeline_validate(spec_path: str) -> BuildSpec:
    """Validate an existing build spec."""
    print(f"\n{'='*60}")
    print(f"  BUILD VALIDATION")
    print(f"{'='*60}\n")

    spec = BuildSpec.load(spec_path)
    print(f"  Build: {spec.class_name} → {spec.ascendancy} (Lv.{spec.level})")

    # Run stat + DPS checks
    print(f"  Stats...", end=" ", flush=True)
    ok = stage_stats(spec)
    print("✓" if ok else "✗")

    if spec.stats.ehp > 0:
        print(f"    EHP: {spec.stats.ehp:.0f}")
        if spec.stats.ehp < 3000:
            print(f"    ⚠ Below T1 minimum (3,000)")
        elif spec.stats.ehp < 5000:
            print(f"    ⚠ Below T11 recommendation (5,000)")
        else:
            print(f"    ✓ Above T11 threshold")

    if spec.main_skill:
        print(f"  DPS...", end=" ", flush=True)
        ok = stage_dps(spec)
        print("✓" if ok else "✗")
        if spec.dps.pinnacle_dps > 0:
            print(f"    Raw: {spec.dps.raw_dps:.0f} | Effective: {spec.dps.effective_dps:.0f}")
            print(f"    Pinnacle: {spec.dps.pinnacle_dps:.0f}")
            if spec.dps.pinnacle_dps < 500:
                print(f"    ⚠ Very low pinnacle DPS — needs upgrades")

    return spec


def pipeline_character_upgrade(account: str, char_name: str) -> str:
    """Run character upgrade pipeline."""
    print(f"\n{'='*60}")
    print(f"  CHARACTER UPGRADE: {char_name}")
    print(f"{'='*60}\n")

    try:
        import subprocess
        # Step 1: Fetch
        print("  1/3  Fetching character...", end=" ", flush=True)
        result = subprocess.run([
            sys.executable, "-m", "fetch_character",
            "--account", account, "--char", char_name,
            "--json",
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode != 0:
            print("✗")
            return "Character fetch failed. Set POESESSID or pass --session."
        print("✓")
        char_data = json.loads(result.stdout)

        # Save temp JSON
        tmp_path = f"/tmp/char_{char_name}.json"
        with open(tmp_path, "w") as f:
            json.dump(char_data, f)

        # Step 2: Deep audit
        print("  2/3  Deep audit...", end=" ", flush=True)
        from character_auditor import deep_audit_character
        audit = deep_audit_character(char_data)
        print("✓")

        # Step 3: Trade suggestions
        print("  3/3  Trade suggestions...", end=" ", flush=True)
        from trade_finder import suggest_upgrades
        trade_out = suggest_upgrades(char_data)
        print("✓")

        output = f"\n{audit.format()}\n\n{trade_out}"
        return output
    except Exception as e:
        return f"Pipeline failed: {e}"


def pipeline_craft_vs_buy(slot: str, desired_mods: list[str], budget: float = 100) -> str:
    """Run craft vs buy comparison."""
    print(f"\n{'='*60}")
    print(f"  CRAFT VS BUY: {slot}")
    print(f"{'='*60}\n")

    parts: list[str] = []

    # Step 1: Crafting plan
    print("  1/3  Crafting plan...", end=" ", flush=True)
    try:
        from crafting_advisor import plan_crafting
        plan = plan_crafting(slot, desired_mods=desired_mods)
        parts.append(plan.format())
        print("✓")
    except Exception as e:
        parts.append(f"Crafting plan failed: {e}")
        print("✗")

    # Step 2: Probability simulation
    print("  2/3  Probability simulation...", end=" ", flush=True)
    try:
        from craft_simulator import craft_vs_buy as cvb
        sim_out = cvb(slot, desired_mods, budget)
        parts.append(sim_out)
        print("✓")
    except Exception as e:
        parts.append(f"Simulation failed: {e}")
        print("✗")

    # Step 3: Trade URL
    print("  3/3  Trade search...", end=" ", flush=True)
    try:
        from trade_finder import build_trade_url
        url = build_trade_url(slot, desired_mods)
        parts.append(f"\nTrade search: {url}")
        print("✓")
    except Exception as e:
        parts.append(f"Trade search failed: {e}")
        print("✗")

    return "\n\n".join(parts)


# ============================================================
# CLI
# ============================================================

def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="PoE2 Build Orchestration Pipeline"
    )
    sub = parser.add_subparsers(dest="command")

    # full-build
    fb = sub.add_parser("full-build", help="Route → Gems → DPS → Gear → Craft → Trade → Export")
    fb.add_argument("--class", dest="class_name", required=True)
    fb.add_argument("--ascendancy", required=True)
    fb.add_argument("--skill", required=True)
    fb.add_argument("--targets", nargs="+", required=True)
    fb.add_argument("--level", type=int, default=80)
    fb.add_argument("--auras", nargs="+")
    fb.add_argument("--risk-profile", default="balanced")
    fb.add_argument("-o", "--output", help="Save spec to JSON file")

    # validate
    val = sub.add_parser("validate", help="Validate existing build spec")
    val.add_argument("spec", help="Build spec JSON file")

    # character-upgrade
    cu = sub.add_parser("character-upgrade", help="Fetch → Audit → Craft → Trade")
    cu.add_argument("--account", required=True)
    cu.add_argument("--char", required=True, dest="char_name")

    # craft-vs-buy
    cvb = sub.add_parser("craft-vs-buy", help="Advisor → Simulator → Trade")
    cvb.add_argument("--slot", required=True)
    cvb.add_argument("--desired-mods", nargs="+", required=True)
    cvb.add_argument("--budget", type=float, default=100)

    args = parser.parse_args()

    if args.command == "full-build":
        spec = pipeline_full_build(
            class_name=args.class_name,
            ascendancy=args.ascendancy,
            skill_name=args.skill,
            targets=args.targets,
            level=args.level,
            auras=args.auras,
            risk_profile=args.risk_profile,
        )

        print(f"\n{'='*60}")
        print(f"  SUMMARY")
        print(f"{'='*60}")
        print(f"  Stages completed: {', '.join(spec.pipeline_stages)}")
        if spec.errors:
            print(f"  Errors: {', '.join(spec.errors)}")
        print(f"  EHP: {spec.stats.ehp:.0f} | DPS: {spec.stats.dps:.0f}")
        print(f"  Unique recommendations: {', '.join(spec.unique_recommendations[:3])}")

        if args.output:
            spec.save(args.output)
            print(f"\n  Build saved to {args.output}")

    elif args.command == "validate":
        spec = pipeline_validate(args.spec)
        if args.spec:
            spec.save(args.spec)  # Update in place
            print(f"\n  Updated {args.spec}")

    elif args.command == "character-upgrade":
        output = pipeline_character_upgrade(args.account, args.char_name)
        print(output)

    elif args.command == "craft-vs-buy":
        output = pipeline_craft_vs_buy(args.slot, args.desired_mods, args.budget)
        print(output)

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
