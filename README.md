<p align="center">
  <img src="https://img.shields.io/badge/poe2-0.5-red?style=flat-square" alt="PoE2 0.5">
  <img src="https://img.shields.io/badge/python-3.9+-blue?style=flat-square" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT">
  <img src="https://img.shields.io/badge/harness-agnostic-purple?style=flat-square" alt="Harness-agnostic">
</p>

# Agent of Exile

A **harness-agnostic** agent instruction set and toolkit for designing
Path of Exile 2 builds. Works with Hermes, OpenClaw, Claude Code, Codex,
or any agent that can read files and run Python.

Every mechanic is sourced from verified data — GGG's skill tree JSON,
poe2db.tw (datamined game files), and the official PoE2 API. Nothing is
recited from stale memory.

---

## What it does

| Capability | How |
|---|---|
| **Build design** | 5 entry points: skill-first, class-first, ascendancy-first, risk profile, off-meta |
| **Passive tree routing** | BFS graph traversal with auto-trim to point budget, leveling guide, ascendancy pathing |
| **Stat calculation** | EHP, resists, armour formula, DPS estimates, danger thresholds per map tier, gear gap targeter |
| **Gem linking** | Auto-matches support gems by tag compatibility from 54-indexed reference |
| **Build comparison** | Side-by-side ascendancy/class diff with stat deltas |
| **Character audit** | Live PoE2 API import — fetches gear, passives, gems, suggests tiered upgrades |
| **Atlas planning** | 8 strategy presets for atlas passive tree routing |
| **Build export** | GGG-compatible build.txt for import into official planner |

---

## Quick Start

```bash
# Clone
git clone https://github.com/LorneDot/agent-of-exile.git ~/workspace/agent-of-exile
cd ~/workspace/agent-of-exile/scripts

# One-time setup
python fetch_tree.py --force      # 5,102-node skill tree
python fetch_gem_data.py --force  # 54-support gem cache

# Route a build
python route_tree.py --class Mercenary --ascendancy "Gemling Legionnaire" \
  --targets 58714 29514 17882 64119 --level 80 --trim --leveling

# Find support gems
python gem_linker.py --skill "Explosive Grenade" --max 6

# Check if your build survives T16 maps
python calc_stats.py spec.json --danger

# Compare two ascendancies
python compare_builds.py --class-a Mercenary --asc-a "Gemling Legionnaire" \
  --class-b Mercenary --asc-b Witchhunter --targets "58714 29514 17882"

# Plan your atlas
python atlas_route.py --strategy expedition --level 40

# Export for import
python generate_build.py spec.json --summary --import-instructions
```

**Per-harness setup:**
- **Hermes:** `cp -r ~/workspace/agent-of-exile ~/.hermes/skills/gaming/agent-of-exile`
- **OpenClaw:** Add `SKILL.md` path to workspace project context. See `adapters/openclaw.md`.
- **Claude Code / Codex / standalone:** Read `SKILL.md` as system prompt.

---

## Tool Reference

### `route_tree.py` — Passive Tree Router
```
python route_tree.py --class Mercenary --ascendancy "Gemling Legionnaire" \
  --targets 58714 29514 17882 --level 80 --trim --leveling
```

Runs BFS graph traversal from your class start through the 5,102-node tree.
Finds shortest paths to all targets, includes every travel node, enforces
point budgets, and auto-trims low-priority nodes if over budget.

| Flag | What it does |
|------|-------------|
| `--trim` | Auto-cut lowest-impact notables to fit budget |
| `--leveling` | Split allocation into 5 level bands (1-20, 20-40, 40-60, 60-80, 80+) |
| `--ascendancy` | Route ascendancy notables on separate point pool |
| `--budget` | Show point budget details |
| `--json` | Machine-readable output |

### `gem_linker.py` — Support Gem Matcher
```
python gem_linker.py --skill "Explosive Grenade" --max 6
```

Matches skill gem tags to compatible supports. 54 support gems indexed with
tag requirements and effect priorities. No browser needed — works offline
after `fetch_gem_data.py --force`.

### `calc_stats.py` — Stat Calculator
```
python calc_stats.py spec.json --danger --targets '{"life":4000,"fire_res":75}'
```

| Flag | What it does |
|------|-------------|
| `--detail` | Full stat breakdown |
| `--danger` | Defense thresholds: T1→T16→Pinnacle boss |
| `--targets` | Reverse calculator — "how much life do I need from gear?" |

### `compare_builds.py` — Build Comparator
```
python compare_builds.py --class-a Mercenary --asc-a "Gemling Legionnaire" \
  --class-b Mercenary --asc-b Witchhunter --targets "58714 29514"
```

Side-by-side comparison: EHP, DPS, defensive layers, travel efficiency,
node overlap, ascendancy advantage. Same skill, different ascendancy —
see the tradeoffs quantified.

### `atlas_route.py` — Atlas Tree Planner
```
python atlas_route.py --strategy expedition --level 40
```

8 strategy presets with pre-selected notable/keystone targets:
`expedition` `breach` `delirium` `ritual` `essence` `harvest` `bossing` `general`

Fetches atlas tree data from `grindinggear/atlastree-export`. Routes shortest
path, enforces atlas point budget (~30-40 from map completion).

### `fetch_character.py` — Live Character Import
```
export POESESSID=your_cookie
python fetch_character.py --account Lorne --char MyWitch --analyze
```

Fetches live character data from the PoE2 API. Shows equipped gear, passive
allocations, socketed gems. `--analyze` flags empty slots, low EHP, uncapped
resists, unused jewel sockets.

### `generate_build.py` — Build Export
```
python generate_build.py spec.json --summary --import-instructions
```

Converts JSON build spec to GGG-compatible import string (deflate + base64
encoded XML). `--summary` includes stat estimates. `--import-instructions`
prints copy-paste steps for the official planner.

---

## Verified Data Sources

| Source | What | Tag |
|--------|------|-----|
| `grindinggear/poe2-skilltree-export` | 5,102-node tree, classes, ascendancies | `[TREE]` |
| `grindinggear/atlastree-export` | Atlas passive tree | `[ATLAS]` |
| `poe2db.tw` | Gems, mods, uniques, crafting, currencies | `[POE2DB]` |
| `pathofexile2.com` | Patch notes, league content | `[GGG-PN]` |
| GGG developer posts | Mechanics explanations, formulas | `[GGG-DEV]` |
| PoE2 API (pathofexile.com) | Live character data | `[GGG-API]` |

---

## Design Philosophy

Agent of Exile does **not** hardcode PoE2 mechanics. Instead, it teaches
the agent **where to look** and provides tools to verify. The SKILL.md is a
296-line workflow engine that stays lean because it doesn't contain numbers
that will rot between patches.

For every claim: source it or tag it `[ESTIMATED]`. PoE1 knowledge is not
PoE2 knowledge without explicit GGG confirmation.

---

## Project Structure

```
agent-of-exile/
├── SKILL.md                         # Workflow engine (296 lines)
├── README.md                        # This file
├── adapters/
│   ├── hermes.md                    # Hermes Agent integration
│   └── openclaw.md                  # OpenClaw integration
├── references/
│   ├── sources.md                   # Complete source directory
│   ├── verified-mechanics.md        # GGG-confirmed formulas only
│   ├── build-format.md              # GGG build XML schema
│   └── skill-tree-format.md         # Tree JSON schema (from data.json)
├── scripts/
│   ├── route_tree.py                # Tree router + leveling + ascendancy
│   ├── gem_linker.py                # Support gem auto-matcher
│   ├── calc_stats.py                # Stats + danger + gear targeter
│   ├── compare_builds.py            # Side-by-side build comparison
│   ├── atlas_route.py               # Atlas passive tree planner
│   ├── fetch_tree.py                # Skill tree data cache
│   ├── fetch_gem_data.py            # Gem data cache
│   ├── fetch_character.py           # PoE2 API character import
│   ├── generate_build.py            # Build spec → GGG file
│   └── build_codec.py               # GGG format encode/decode
└── examples/
    └── example_build.json
```

---

## Requirements

- Python 3.9+ (stdlib only, zero dependencies)
- POESESSID cookie for character audit (from pathofexile.com login)
- Internet access for initial data fetch (tree data, gem cache)

## License

MIT
