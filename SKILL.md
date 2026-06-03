---
name: poe2-theory-crafter
description: "Use when the user asks to theory-craft, design, plan, or create a Path of Exile 2 build — from any starting point: a specific skill gem, a class, an ascendancy, a playstyle, or an unconventional off-meta concept. Computes character stats and outputs GGG-compatible build planner files. Sources mechanics from verified GGG data and poe2db, not memory."
version: 3.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [poe2, path-of-exile-2, theory-crafting, build-planner, arpg, gaming, stats]
    related_skills: []
---

# PoE2 Theory Crafter

## Overview

Design Path of Exile 2 builds using verified data sources, not memorized
mechanics. This skill teaches a workflow for theory-crafting builds from
any entry point, sourcing every claim from GGG-published data, datamined
game files (poe2db.tw), or community-verified information.

**Core principle:** Never recite mechanics from memory. Look them up.

## When to Use

- "theory craft a PoE2 build..."
- "design a build using [skill]"
- "what class works with [archetype]?"
- "hardcore/SSF/league starter build"
- "can you make [class] use [skill]?" (off-meta)
- "meme build" / unconventional
- Computing stats or generating a build file

Don't use for: lore, boss guides, trade prices.

## Source System

Every claim must be sourced. Here's how to find information:

| When you need...                  | Go to...                          | Tag       |
|----------------------------------|-----------------------------------|-----------|
| Skill tree (classes, nodes, ascendancies) | `data.json` via `fetch_tree.py` | `[TREE]` |
| Gem data (skills, supports, tags, requirements) | poe2db.tw → Gems | `[POE2DB]` |
| Mods (prefix/suffix per slot, tiers) | poe2db.tw → Mods | `[POE2DB]` |
| Unique items (stats, drop sources) | poe2db.tw → Uniques | `[POE2DB]` |
| Crafting (essences, omens, bench crafts) | poe2db.tw → Crafting | `[POE2DB]` |
| Item bases (requirements, implicits) | poe2db.tw → Items | `[POE2DB]` |
| Mechanics formulas (life, damage, resists) | `skill_view(file_path='references/verified-mechanics.md')` | `[GGG-IG]` |
| Patch notes, league content | pathofexile2.com | `[GGG-PN]` |
| Developer statements | PoE forum / GGG tracker | `[GGG-DEV]` |
| Atlas passive tree | `grindinggear/atlastree-export` | `[ATLAS]` |

Load `references/sources.md` for the complete source directory.

**Load verified mechanics on demand only.** Don't load the full mechanics
reference into context unless the agent needs specific formulas. Use:
```
skill_view(name='poe2-theory-crafter', file_path='references/verified-mechanics.md')
```

**Golden rule:** If you can't find a source for a claim, mark it `[ESTIMATED]`.
PoE1 knowledge is NOT PoE2 knowledge without explicit GGG confirmation.

## Quick Start

```bash
cd scripts
python fetch_tree.py --force   # get current tree data (5K+ nodes)
python generate_build.py spec.json --xml  # test a build spec
python calc_stats.py spec.json --detail  # compute character stats
```

## Build Design Workflow

Detect the entry point from the user's prompt and follow the corresponding
workflow. Risk profiles (glass cannon, balanced, tanky, hardcore, SSF) are
applied as design principles on top of any entry point — see Entry D.

### Entry A: Skill-First

1. Look up the skill gem on poe2db.tw → Gems. Note: tags, damage type,
   effectiveness, attribute requirements, level scaling.
2. Find which ascendancy passives and support gems amplify those tags.
3. Pick the class/ascendancy with the most synergy.
4. Load `fetch_tree.py` output. Trace the tree path from class start to
   relevant damage and defense clusters.
5. Select supports from poe2db.tw — prioritize "more" multipliers.
6. Look up gear mods on poe2db.tw → Mods for each equipment slot.
7. Compute stats with `calc_stats.py`.
8. Generate build file with `generate_build.py`.

### Entry B: Class-First

1. Read the class entry from data.json for base attributes and ascendancy list.
2. Look up each ascendancy's mechanics (poe2db.tw or community guides).
3. Ask the user which archetype (caster, melee, minion, DoT, etc.).
4. Select synergistic skills from poe2db.tw that match the archetype.
5. Build tree, supports, gear, stats, output.

### Entry C: Ascendancy-First

1. Identify the class from data.json ascendancy list.
2. Look up the ascendancy's defining passives (poe2db.tw).
3. Find skills that maximize those passives' effects.
4. Build everything around the ascendancy's core mechanic.
5. Tree, supports, gear, stats, output.

### Entry D: Risk Profile & League Mode

Design principles, not hard numbers — the meta shifts with patches.

| Profile      | Principle |
|-------------|-----------|
| Glass Cannon | Favor damage. Accept deaths. Softcore only. |
| Balanced     | Roughly even offense/defense split. |
| Tanky        | Lean into defense. Slower clear is OK. |
| Hardcore     | Maximum survivability. Every slot has life/ES. |
| SSF          | No trade-only uniques. Deterministic crafting priority. |

When designing for HC or SSF, apply these directional principles. Look up
current meta expectations from community sources rather than hardcoding
EHP/resist targets that may be wrong next patch.

### Entry E: Unconventional / Off-Meta

1. **Identify the constraint** — wrong tree position? Wrong attributes?
   Wrong ascendancy synergy?
2. **Find the bridge** — what mechanic makes it possible?
   - Search poe2db.tw → Uniques for build-enabling items
   - Keystones that flip rules (CI, MoM, Avatar of Fire, Blood Magic)
   - Ascendancy passives with cross-mechanic synergy
   - Trigger gems and weapon-swap tech
3. **Trace the tree path** — map the travel cost from class start.
4. **Calculate the tax** — quantify lost passives vs conventional path.
5. **Find the payoff** — why do this instead of the obvious class?
6. **Be honest about viability** — meme-tier vs surprisingly good.
7. **Cover defense gaps** — unconventional paths leave holes.

## Generating the Build Output

```python
from generate_build import generate_build_string
from pathlib import Path

spec = {
    "className": "Witch",
    "ascendClassName": "Infernalist",
    "level": 80,
    "passives": ["node_id_1", "node_id_2", ...],  # from data.json
    "skills": [{
        "setName": "Default",
        "skills": [{
            "gems": [
                {"id": "Metadata/Items/Gems/SkillGemFireball",
                 "level": 20, "quality": 20},
                {"id": "Metadata/Items/Gems/SupportGemSpellEcho",
                 "level": 20, "quality": 20},
            ]
        }]
    }],
    "notes": "Build guide notes here"
}

build_string = generate_build_string(spec)
Path("build.txt").write_text(build_string)
```

The build string imports into any GGG-compatible planner. Format is
`XML → deflate → base64(URL-safe)`.

See `references/build-format.md` for the full XML schema.

## Output Summary Template

Always produce a structured summary containing:
- Class → Ascendancy, level, entry point, risk profile
- Stat estimates from `calc_stats.py`
- Ascendancy node choices with rationale
- Skill gem setup (main skill + supports, auras)
- Passive tree overview (keystones, key notables, defense clusters)
- Gear recommendations per slot with prefix/suffix priorities
- Crafting strategy and key unique drop sources
- Playstyle notes
- Source citations for all claims

## Common Pitfalls

1. **Don't recite mechanics from memory.** Look them up from poe2db.tw or
   verified-mechanics.md. PoE1 knowledge ≠ PoE2 knowledge.
2. **Node IDs must be strings from data.json.** Never guess or invent.
3. **Ascendancy names are case-sensitive and exact.** From data.json.
4. **Skill gem IDs use Metadata/ paths.** Get from poe2db.tw, not memory.
5. **Resistance penalty is -60% at endgame.** Need 135% total to cap.
6. **"More" versus "increased"** — the most important PoE distinction.
   More is multiplicative, increased is additive.
7. **CI = 1 life.** No life gear. Blood Magic = no mana. No mana gear.
8. **Mark estimates clearly.** If poe2db.tw doesn't have it and GGG hasn't
   confirmed it, it's `[ESTIMATED]`. Say so.
9. **Load references on demand.** Don't load verified-mechanics.md into
   context unless you need the formulas. The source directory tells you
   where to go for everything else.
10. **Don't hardcode gear mods as facts.** Look up current mods on poe2db.tw
    each time. Mod pools change between leagues.

## Verification Checklist

- [ ] Tree data current (`python fetch_tree.py --stats`)
- [ ] All passives are real node IDs from data.json
- [ ] Gem IDs verified from poe2db.tw
- [ ] Gear mods sourced from poe2db.tw Mods
- [ ] All mechanics claims have source tags
- [ ] `[ESTIMATED]` used where unverifiable
- [ ] Resistance penalty accounted for
- [ ] HC/SSF design principles applied
- [ ] Build spec validates with `generate_build.py --xml`
- [ ] Human-readable summary covers all sections
