# PoE2 Theory Crafter

A Hermes Agent skill for designing Path of Exile 2 builds using **verified
data sources**, not memorized mechanics. Sources every claim from GGG-published
data, poe2db.tw (datamined game files), or community-verified resources.

## What it does

- **Multi-entry design:** Skill-first, class-first, ascendancy-first, or off-meta
- **Source-driven:** Every mechanic looked up from poe2db.tw, data.json, or
  GGG documentation — never recited from stale memory
- **Stat calculation:** Computes life, ES, mana, EHP, resists, armour reduction,
  DPS estimates using formulas confirmed by GGG
- **GGG-compatible output:** Generates importable build files for the official
  PoE2 build planner
- **League-aware design:** Risk profiles and SSF/HC as directional principles

## Design Philosophy

This skill does NOT hardcode PoE2 mechanics. Instead, it teaches the agent
**where to look**:

- **Skill tree data** → `data.json` from GGG's GitHub
- **Gems, mods, uniques, crafting** → poe2db.tw
- **Mechanics formulas** → on-demand reference file
- **Patch notes & league content** → pathofexile2.com

The 8.9KB SKILL.md is a workflow engine + source directory. It stays lean
and never rots because it doesn't contain stale numbers.

## Quick Install

```bash
git clone https://github.com/YOU/poe2-theory-crafter.git \
  ~/.hermes/skills/gaming/poe2-theory-crafter
cd ~/.hermes/skills/gaming/poe2-theory-crafter/scripts
python fetch_tree.py --force
```

## Usage

"theory craft a Lightning Arrow Deadeye for mapping"
→ Agent looks up Lightning Arrow on poe2db.tw, checks Deadeye passives,
draws tree path from Ranger start, selects supports by tags, looks up
bow/quiver mods, computes stats, generates build.txt.

"make a melee Witch work somehow"
→ Agent identifies the constraint (INT start, melee = STR area), finds
bridges (Infernalist fire scaling on attacks? Unique conversion item?),
calculates the travel tax, honestly rates viability.

## Project Structure

```
poe2-theory-crafter/
├── SKILL.md                        # Workflow engine (216 lines)
├── README.md
├── scripts/
│   ├── fetch_tree.py               # Cache GGG skill tree data
│   ├── build_codec.py              # Encode/decode GGG build format
│   ├── generate_build.py           # JSON spec → importable file
│   └── calc_stats.py               # Character stat calculator
├── references/
│   ├── sources.md                  # Complete source directory
│   ├── verified-mechanics.md       # Only GGG-confirmed formulas
│   ├── build-format.md             # GGG build XML schema
│   └── skill-tree-format.md        # Tree JSON schema
└── examples/
    └── example_build.json
```

## Verified Data Sources

| Source | What it provides | Tag |
|--------|-----------------|-----|
| `grindinggear/poe2-skilltree-export` | Classes, nodes, ascendancies, tree layout | `[TREE]` |
| `poe2db.tw` | Gems, mods, uniques, crafting, item bases | `[POE2DB]` |
| `pathofexile2.com` | Patch notes, league content | `[GGG-PN]` |
| GGG developer posts | Mechanics explanations, formulas | `[GGG-DEV]` |
| Maxroll PoE2 planner (JS) | GGG build format | Reverse-engineered |

## Requirements

- Python 3.9+
- No external dependencies (stdlib only)

## License

MIT
