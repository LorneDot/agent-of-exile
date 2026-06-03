# PoE2 Theory Crafter

A Hermes Agent skill that theory-crafts Path of Exile 2 builds from any
starting point — a skill gem, a class, an ascendancy, or a playstyle.
Computes character stats (EHP, resists, DPS, mana) and outputs
GGG-compatible build planner files you can import into the official planner.

## What it does

- **Multi-entry design:** Start from a skill, class, ascendancy, or risk profile
- **Stat calculation:** Computes life, ES, mana, resistances, armour reduction,
  effective DPS, and effective HP using documented PoE2 formulas
- **League-aware:** Optimizes for Softcore, Hardcore, SSF, or trade league
- **Risk profiles:** Glass cannon, balanced, tanky, or HC-viable with explicit
  survival targets
- **Source-cited mechanics:** Every claim traced to GGG patch notes, in-game
  tooltips, developer posts, or the official skill tree data
- **GGG-compatible output:** Generates deflate+base64 encoded build strings
  for the official PoE2 build planner

## Quick Install

```bash
git clone https://github.com/YOU/poe2-theory-crafter.git \
  ~/.hermes/skills/gaming/poe2-theory-crafter

cd ~/.hermes/skills/gaming/poe2-theory-crafter/scripts
python fetch_tree.py --force
```

## Usage

Once installed, ask Hermes:

> "Theory craft a Lightning Arrow Deadeye for mapping — balanced risk"

> "I want a build using Fireball. SSF viable."

> "Design a hardcore Infernalist build with good survivability"

The agent will:
1. Analyze the entry point (skill-first, class-first, ascendancy-first)
2. Load the 5,102-node skill tree data
3. Design passives, skill gems, supports, and gear
4. Compute stats with `calc_stats.py`
5. Generate an importable `build.txt` + human-readable summary

### Standalone Scripts

```bash
# Fetch/update tree data
python scripts/fetch_tree.py --force

# Generate a build from a JSON spec
python scripts/generate_build.py examples/example_build.json -o build.txt

# See the raw XML
python scripts/generate_build.py examples/example_build.json --xml

# Decode a build string back to XML
python scripts/build_codec.py decode build.txt

# Compute character stats from a build spec
python scripts/calc_stats.py examples/example_build.json --detail
```

## Project Structure

```
poe2-theory-crafter/
├── SKILL.md              # Hermes skill (mechanics, workflows, formulas)
├── README.md             # This file
├── scripts/
│   ├── build_codec.py    # Encode/decode GGG build format
│   ├── fetch_tree.py     # Fetch & cache skill tree data
│   ├── generate_build.py # JSON spec → GGG build file
│   └── calc_stats.py     # Character stat calculator (EHP, DPS, resists)
├── references/
│   ├── build-format.md   # GGG build XML schema
│   └── skill-tree-format.md  # Tree JSON schema
└── examples/
    └── example_build.json    # Sample spec
```

## Build Format

```
XML → Deflate (zlib) → Base64 (URL-safe) → Import String
```

Reverse-engineered from the Maxroll planner. See `references/build-format.md`.

## Skill Tree Data

GGG publishes the 5,102-node PoE2 passive tree at:
[grindinggear/poe2-skilltree-export](https://github.com/grindinggear/poe2-skilltree-export)

## Requirements

- Python 3.9+
- No external dependencies (stdlib only)

## License

MIT
