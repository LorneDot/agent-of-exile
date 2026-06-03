# Agent of Exile

A **harness-agnostic** agent instruction set for designing Path of Exile 2
builds using verified data sources, not memorized mechanics. Works with
Hermes, OpenClaw, Claude Code, Codex, or any agent that can run Python
scripts and read files.

## What it does

- **Multi-entry design:** Skill-first, class-first, ascendancy-first, off-meta
- **Character audit:** Import your live PoE2 character from the API and get
  tiered upgrade suggestions with sourced justifications
- **Source-driven:** Every mechanic looked up from poe2db.tw, data.json, or
  GGG documentation — never recited from stale memory
- **Stat calculation:** Computes life, ES, mana, EHP, resists, armour reduction,
  DPS estimates using formulas confirmed by GGG
- **GGG-compatible output:** Generates importable build files for the official
  PoE2 build planner

## Design Philosophy

Agent of Exile does NOT hardcode PoE2 mechanics. Instead, it teaches the agent
**where to look**:

- **Skill tree data** → `data.json` from GGG's GitHub
- **Gems, mods, uniques, crafting** → poe2db.tw
- **Live characters** → pathofexile.com API (POESESSID)
- **Mechanics formulas** → on-demand reference file
- **Patch notes & league content** → pathofexile2.com

The 11KB SKILL.md is a workflow engine + source directory. It stays lean
and never rots because it doesn't contain stale numbers.

## Quick Install

```bash
# Clone the repo
git clone https://github.com/YOU/agent-of-exile.git ~/workspace/agent-of-exile
cd ~/workspace/agent-of-exile/scripts

# One-time: fetch PoE2 skill tree data
python fetch_tree.py --force
```

**Per-harness setup:**

- **Hermes:** `cp -r ~/workspace/agent-of-exile ~/.hermes/skills/gaming/agent-of-exile`
  (Skill auto-loads on trigger. See `adapters/hermes.md`.)
- **OpenClaw:** Add `SKILL.md` path to workspace project context.
  (See `adapters/openclaw.md`.)
- **Claude Code / Codex / standalone:** No setup needed. Read SKILL.md as
  system prompt and run scripts directly.

## Usage

**Theory-craft:** "design a Lightning Arrow Deadeye for mapping"
→ Agent looks up Lightning Arrow on poe2db.tw, checks Deadeye passives,
draws tree path from Ranger start, selects supports by tags, looks up
bow/quiver mods, computes stats, generates build.txt.

**Off-meta:** "make a melee Witch work"
→ Agent identifies the constraint (INT start, melee = STR area), finds
bridges (Infernalist fire scaling on attacks? Unique conversion item?),
calculates the travel tax, honestly rates viability.

**Character audit:** "audit my level 78 Witch on my account"
→ Agent fetches live character from PoE2 API, identifies gaps (empty
jewel sockets, uncapped resists, wrong support gems), suggests upgrades
tiered by cost, recomputes stats post-changes.

## Project Structure

```
agent-of-exile/
├── SKILL.md                        # Workflow engine (~250 lines)
├── README.md
├── scripts/
│   ├── fetch_tree.py               # Cache GGG skill tree data
│   ├── fetch_character.py          # PoE2 API — import live characters
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

## Requirements

- Python 3.9+
- No external dependencies (stdlib only)
- POESESSID cookie (for character audit — from pathofexile.com login)

## License

MIT
