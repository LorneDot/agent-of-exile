---
name: poe2-theory-crafter
description: "Use when the user asks to theory-craft, design, plan, or create a Path of Exile 2 build — including passive trees, skill gem setups, ascendancy choices, gearing, and build guide output. Covers any class, ascendancy, or playstyle."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [poe2, path-of-exile-2, theory-crafting, build-planner, arpg, gaming]
    related_skills: []
---

# PoE2 Theory Crafter

## Overview

Design Path of Exile 2 builds from concept to GGG-compatible output file.
This skill gives you the knowledge and workflow to theory-craft PoE2 builds,
then generate a build string that can be imported into the official build
planner (pathofexile2.com/planner) or any compatible tool (Maxroll, PoB2).

You act as an expert PoE2 build designer who understands the skill tree,
gem system, ascendancy classes, gear synergies, and endgame scaling.

## When to Use

- User says "theory craft a PoE2 build for..."
- User says "design a [class] build that..."
- User says "create a build guide for..."
- User says "what's a good build for [archetype]?"
- User mentions PoE2 builds, passives, or skill gems in a planning context

Don't use for general PoE2 questions, lore queries, or patch note summaries.
Only use when the user wants to DESIGN a build.

## Quick Start

Run the setup script once to fetch tree data:

```bash
cd scripts && python fetch_tree.py --force
```

The tree data is cached at `~/.cache/poe2-theory-crafter/tree-data.json`.

## Core Workflow

### Phase 1: Gather Requirements

Ask the user (or infer from their prompt):

1. **Class**: Which base class? (Warrior, Witch, Sorceress, Mercenary, Monk,
   Ranger, Huntress, Druid, Marauder, Duelist, Shadow, Templar)
2. **Ascendancy**: Which specialization? (Titan, Infernalist, Stormweaver, etc.)
3. **Playstyle**: What damage type? What defensive layer? Minion, totem, self-cast,
   attack, trigger, etc.
4. **Budget/League**: League starter vs. endgame? SSF vs. trade?
5. **Target content**: Mapping, bossing, delve, sanctum, etc.

Do NOT ask all 5 questions at once if the user already implied answers.
Extract what you can from their prompt and ask at most 2 clarifying questions.

### Phase 2: Load Tree Data

```python
from fetch_tree import fetch_tree
tree = fetch_tree()
nodes = tree["nodes"]
groups = tree["groups"]
classes = tree["classes"]
```

Find the user's class entry to get starting position, overridePairs, and
ascendancy options. Use this to understand where on the tree they start.

### Phase 3: Design the Passive Tree

Key design principles for PoE2 passive trees:

- **Path efficiency**: Take the shortest path between notable clusters. Every
  travel node costs a skill point — minimize them.
- **Defense layering**: PoE2 punishes one-dimensional defense. Most builds need
  at least 2 layers (e.g., ES + evasion, armor + block, MoM + ES).
- **Attribute requirements**: Skill gems have attribute requirements. Path
  through +30 attribute nodes if needed.
- **Cluster prioritization**: Notable passives > keystones > masteries >
  travel stats. A notable that gives 30% increased damage + utility is worth
  pathing to.
- **Jewel sockets**: At ~2 passive points of travel, a jewel socket is
  almost always worth taking. Prioritize 2-socket clusters.
- **Keystone tradeoffs**: Keystones are build-defining but come with downsides.
  Chaos Inoculation (CI) — immune to chaos but 1 life. Mind Over Matter (MoM) —
  mana before life but less mana regen. Only take keystones that synergize with
  your full build plan.

When selecting nodes, output a list of node IDs that form the allocated path.
Start from the class starting nodes and trace outward. A typical level 80
build has ~95-100 passive points allocated (80 from levels + 24 from quests).

### Phase 4: Select Skill Gems

PoE2's skill gem system:

- **Skill gems** grant active skills. They level up with experience.
- **Support gems** modify linked skill gems. Up to 5 supports per skill gem
  (depending on links).
- Each skill gem can have supports slotted directly into it (no more gear
  socket linking — sockets are on the gem itself).
- **Spirit gems** (auras, heralds, buffs) reserve Spirit instead of mana.

Key gem selection rules:

1. Choose 1-2 main damage skills that synergize with your passive tree
2. Add supports that multiply damage: "more" multipliers > "increased"
3. Include at least 1 movement skill
4. Pick auras/buffs that match your damage type and defensive strategy
5. Consider curses, marks, or exposure for single-target

Use internally known gem IDs. Key prefixes:
- `Metadata/Items/Gems/SkillGem*` for skill gems
- `Metadata/Items/Gems/SupportGem*` for supports
- `Metadata/Items/Gems/SpiritGem*` for spirit gems

### Phase 5: Recommend Gear

For each equipment slot, recommend:

- **Base type**: What base item suits the build's attribute requirements
  and implicit modifiers
- **Key mods**: The 2-3 most important affixes per slot
- **Unique items**: Any build-enabling uniques

Priority order: Weapon(s) → Body Armour → Helmet → Amulet → Rings → Belt →
Gloves → Boots → Flasks → Charms → Jewels

### Phase 6: Generate Output File

Assemble the build spec and generate the GGG-compatible file:

```python
from generate_build import generate_build_string

spec = {
    "className": "Witch",
    "ascendClassName": "Infernalist",
    "level": 80,
    "passives": ["50459", "47175", ...],
    "skills": [...],
    "items": {...},
    "notes": "Build guide notes here"
}

build_string = generate_build_string(spec)

# Write for import into the official planner
with open("build.txt", "w") as f:
    f.write(build_string)
```

The output file `build.txt` can be:
- Copy-pasted directly into the PoE2 planner's import dialog
- Shared as a text file
- Uploaded to build-sharing platforms

Present the build string and the raw XML (with `--xml` flag) to the user.

### Phase 7: Write Build Guide Summary

Output a human-readable build summary:

```
=== [Build Name] ===
Class: Witch → Infernalist
Level: 80 | League: [type]

--- Passive Tree ---
[Number] points allocated
Keystones: [list]
Key clusters: [list]

--- Skill Gems ---
Main: [skill] - [supports]
Auras: [list]

--- Gear Priorities ---
Weapon: [base + mods]
...

--- Playstyle ---
[Brief rotation and playstyle notes]

--- Import ---
Build file: build.txt
```

## PoE2 Quick Reference

### Classes & Ascendancies (as of 0.5.0)

| Base Class   | Attribute Split | Ascendancies                                      |
|-------------|----------------|---------------------------------------------------|
| Warrior     | STR            | Titan, Warbringer, Ancestral Commander            |
| Witch       | INT            | Infernalist, Blood Mage, Lich, Abyssal Lich      |
| Ranger      | DEX            | Deadeye, Pathfinder                               |
| Sorceress   | INT            | Stormweaver, Chronomancer, Spellblade             |
| Mercenary   | STR/DEX        | Witchhunter, Gemling Legionnaire, Tactician       |
| Monk        | DEX/INT        | Invoker, Acolyte of Chayula                       |
| Huntress    | DEX            | Ritualist, Amazon, Spirit Walker                  |
| Druid       | STR/INT        | Feral, Elementalist                               |
| Duelist     | STR/DEX        | Gladiator (upcoming)                              |
| Shadow      | DEX/INT        | Assassin (upcoming)                               |
| Marauder    | STR            | (upcoming)                                         |
| Templar     | STR/INT        | (upcoming)                                         |

### Defense Types

| Layer       | Works Against     | Key Attribute |
|------------|-------------------|---------------|
| Armour     | Physical hits     | STR           |
| Evasion    | Attacks           | DEX           |
| Energy Shield | All damage      | INT           |
| Block      | Attacks/Spells    | Shield/Staff  |
| Mind Over Matter | All damage  | Mana pool     |
| Chaos Inoculation | Chaos      | ES pool       |

### Elemental Ailments

- **Ignite** (Fire): Damage over time based on hit damage
- **Shock** (Lightning): Increases damage taken by up to 50%
- **Chill/Freeze** (Cold): Slow / immobilize
- **Electrocute** (Lightning): Stun-like interrupt
- **Bleed** (Physical): Damage over time while moving
- **Poison** (Chaos): Stacking damage over time

## Common Pitfalls

1. **GGG format is base64-encoded XML, not plain XML.** Always run through
   `generate_build.py` for the final output. Raw XML won't import.

2. **Node IDs must be string keys from data.json.** The passives list in the
   spec must use the exact node IDs from the tree data. Don't guess or invent IDs.

3. **Ascendancy names must match exactly.** Use the names from the class's
   `ascendancies` array — case-sensitive, exact string match.

4. **Skill gem IDs use the Metadata/ path.** Gems are identified by their
   internal path, not display name. The `gemId` attribute must be the
   full `Metadata/Items/Gems/...` path.

5. **Level + ascension are separate.** The `level` attribute is character level.
   Ascendancy points come from labyrinth/trials. A level 80 character has all
   8 ascendancy points regardless of level.

6. **Passive tree data updates with patches.** Always fetch the latest tree
   data with `--force` after a major PoE2 patch. Node IDs can change.

7. **Item text format matters.** The `<Item>` text content should match the
   in-game item copy format for proper parsing. Use the standard item string
   representation.

8. **Don't theory-craft without tree data.** If the tree data isn't cached,
   fetch it first. Builds designed without real node IDs are useless.

## Verification Checklist

- [ ] Tree data fetched and cached (`python fetch_tree.py --stats`)
- [ ] All passives use real node IDs from data.json
- [ ] Ascendancy name matches exactly
- [ ] Build spec validated with `python generate_build.py spec.json --xml`
- [ ] Generated build string can be imported into a planner
- [ ] Build summary covers all key decisions
- [ ] Gear recommendations are realistic for the budget/league
