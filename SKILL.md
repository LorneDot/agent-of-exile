---
name: agent-of-exile
description: "Use when the user asks to theory-craft, design, plan, audit, or create a Path of Exile 2 build. Agent of Exile sources mechanics from verified GGG data and poe2db, not memory. Computes character stats, imports live characters from the PoE2 API, and outputs GGG-compatible build planner files."
version: 4.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [poe2, path-of-exile-2, theory-crafting, build-planner, arpg, gaming, stats]
    related_skills: []
---

# Agent of Exile

## Overview

Design Path of Exile 2 builds using verified data sources, not memorized
mechanics. This is a **harness-agnostic agent instruction set** — it works
with Hermes, OpenClaw, Claude Code, Codex, or any agent that can run
Python scripts and read files.

**Core principle:** Never recite mechanics from memory. Look them up.

## Harness Compatibility

This skill uses plain Python scripts + markdown references. No harness-specific
dependencies. For integration details per harness, see the adapter files:

| Harness | Adapter | How to use |
|---------|---------|------------|
| Hermes Agent | `adapters/hermes.md` | Install to `~/.hermes/skills/gaming/agent-of-exile/` |
| OpenClaw | `adapters/openclaw.md` | Load as project context in workspace |
| Claude Code | Use directly | Read SKILL.md as system prompt, run scripts/ with Bash tool |
| Codex CLI | Use directly | Read SKILL.md, use terminal for scripts |
| Standalone | Use directly | Read SKILL.md, execute scripts with `python scripts/...` |

### How to load references (harness-agnostic)

Each harness has its own way to read files. The skill references these files:

| Reference | Path | When to load |
|-----------|------|-------------|
| Source directory | `references/sources.md` | First session, to learn where to look |
| Verified mechanics | `references/verified-mechanics.md` | On demand, when formulas needed |
| Crafting basics | `references/crafting-basics.md` | When planning gear or suggesting crafts |
| Unique synergies | `references/unique-synergies.md` | When finding build-around uniques |
| Build format | `references/build-format.md` | When generating output |
| Skill tree format | `references/skill-tree-format.md` | When navigating data.json |

**In any harness:** read these files with your native file-reading tool
when you need the information. Don't load all of them into context at
once — load on demand.

**Hermes-specific:** use `skill_view(name='agent-of-exile', file_path='references/...')`
**OpenClaw-specific:** see `adapters/openclaw.md`
**Claude Code/Codex:** use your native `Read` tool or `cat` via terminal
**Standalone:** `cat references/sources.md`

## When to Use

- "theory craft a PoE2 build..."
- "design a build using [skill]"
- "what class works with [archetype]?"
- "hardcore/SSF/league starter build"
- "can you make [class] use [skill]?" (off-meta)
- "meme build" / unconventional
- "audit my [character]" / "improve my build" / "what should I upgrade?"
- "look up my [class] on my account" / "analyze my PoE2 character"
- "how do I craft [item]?" / "what mods can I get on [slot]?"
- "what uniques work with [build/skill/ascendancy]?"
- "optimize my gem links" / "what supports for [skill]?"
- "optimize my passive tree" / "can I fit [node] in my build?"
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
| Mechanics formulas (life, damage, resists) | `references/verified-mechanics.md` | `[GGG-IG]` |
| Patch notes, league content | pathofexile2.com | `[GGG-PN]` |
| Developer statements | PoE forum / GGG tracker | `[GGG-DEV]` |
| Atlas passive tree | `grindinggear/atlastree-export` | `[ATLAS]` |

Load `references/sources.md` for the complete source directory.

**Golden rule:** If you can't find a source for a claim, mark it `[ESTIMATED]`.
PoE1 knowledge is NOT PoE2 knowledge without explicit GGG confirmation.

## Quick Start

```bash
cd scripts
python fetch_poe2_data.py --force      # item bases + mod weights (1,600+ items, 21 groups)
python fetch_tree.py --force           # skill tree data (5K+ nodes)
python fetch_gem_data.py --force       # cache gem data
python fetch_unique_data.py --force    # cache unique item data

# Build design
python route_tree.py --class Mercenary --ascendancy "Gemling Legionnaire" \
  --targets 58714 29514 17882 --level 80 --trim --leveling

# Gem optimization + DPS simulation
python gem_analyzer.py --skill "Explosive Grenade" --simulate-dps --links 5
python dps_simulator.py --skill "Explosive Grenade" --auras "Herald of Ash" \
  --monster-tier T16 --charges frenzy:3  # full DPS with auras/charges/resists

# Crafting simulation
python crafting_advisor.py --slot "Body Armour" --desired-mods life_flat resistance
python craft_simulator.py --slot "Ring" --desired-mods life_flat fire_res cold_res \
  --method essence_regal  # probability + cost simulation

# Trade search
python trade_finder.py --slot "Body Armour" --mods life_flat fire_res\
  --max-price 50  # search poe2 trade for items

# Unique analysis
python unique_analyzer.py --ascendancy "Gemling Legionnaire"

# Tree optimization
python build_optimizer.py --spec spec.json --travel-report

# Stats + audit
python calc_stats.py spec.json --danger
python character_auditor.py --account Lorne --char MyWitch

# Compare + export
python compare_builds.py --class-a Mercenary --asc-a "Gemling Legionnaire" \
  --class-b Mercenary --asc-b Witchhunter --targets "58714 29514"
python atlas_route.py --strategy expedition --level 40
python generate_build.py spec.json --summary --import-instructions
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
   relevant damage and defense clusters. **Verify connectivity** using
   `out`/`in` fields — every node must be reachable from root. Include
   travel nodes in your list (not just notables). Budget 3-7 travel nodes
   between clusters.
5. **Check point budget.** Total allocated nodes (notables + travel) must
   not exceed available points. Level 80 = 103 points (79 levels + 24 quests).
   Cut lowest-impact nodes if over budget.
6. Select supports from poe2db.tw — prioritize "more" multipliers.
7. Look up gear mods on poe2db.tw → Mods for each equipment slot.
8. Compute stats with `calc_stats.py`.
9. Generate build file with `generate_build.py`.

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

### Entry F: Character Audit ("audit my Witch on my account")

When the user wants to analyze and improve an existing character from
their PoE2 account, fetch the live character data and suggest upgrades.

**Prerequisites:** The user must provide their POESESSID cookie (from
pathofexile.com → DevTools → Application → Cookies → POESESSID).
Store it as `POESESSID` environment variable or pass via `--session`.

1. **Fetch the character:**
   ```bash
   python scripts/fetch_character.py --account <name> --char <name>
   ```

2. **Parse the current state:**
   - What level, class, ascendancy?
   - What gear is equipped in each slot? (rarity, iLvl, sockets, links)
   - What passives are allocated? (from `passives.hashes`)
   - What gems are socketed? (from `items[].socketedItems`)

3. **Compute current stats** from the fetched data using `calc_stats.py`
   with the character's actual gear values extracted from the API response.

4. **Identify gaps** — compare to what's expected for the level/content:
   - Missing life/ES on gear slots?
   - Unallocated jewel sockets?
   - Low-level gems that need upgrading?
   - Empty flask/charm slots?
   - Resistances not capped for current content?
   - Wasted passive nodes (inefficient pathing)?
   - Support gems not matching main skill tags?

5. **Suggest upgrades** — ordered by impact per cost:
   - **Free wins:** allocate unused passives, swap gem levels, fix support
     gem tags, use empty jewel sockets
   - **Cheap upgrades:** essence-craft life/resists on worst rare piece,
     buy level 20 gems, add runes to empty rune sockets
   - **Mid-budget:** replace worst-in-slot rare, upgrade weapon
   - **Expensive:** chase uniques, 6-link, Vaal orb corrupt

6. **For each suggestion, explain:** what to change, why, what source
   confirms the improvement (poe2db.tw for mod availability), and
   estimated cost (in chaos/divine or crafting materials).

7. **Recompute stats** post-changes to show the delta.

For the POESESSID: never log or display it. The user should set it as
an environment variable: `export POESESSID=...`

### Entry G: Crafting & Gear Planning

When the user asks how to craft an item or plan gear:

1. Load `references/crafting-basics.md` for crafting systems reference.
2. Use `crafting_advisor.py`:
   ```bash
   python scripts/crafting_advisor.py --slot "<slot>" --desired-mods <mod1> <mod2> ...
   python scripts/crafting_advisor.py --list-mods          # all mod tier breakpoints
   python scripts/crafting_advisor.py --list-bases          # all item bases
   python scripts/crafting_advisor.py --slot-bases "<slot>" # bases for a slot
   ```
3. The advisor returns: recommended base item, target iLvl, step-by-step
   crafting process with currency costs, and alternatives (trade, Expedition Rog, Harvest resistance swaps).
4. For item analysis: `python scripts/crafting_advisor.py --item <item.json>`
   (JSON from `fetch_character.py` output).
5. Key concepts: prefixes (up to 3), suffixes (up to 3), iLvl thresholds
   for mod tiers, rune sockets via Artificer's Orbs.

### Entry H: Unique Item Analysis

When the user asks about unique items or build-around synergies:

1. Ensure cache: `python scripts/fetch_unique_data.py --force`
2. Use `unique_analyzer.py`:
   ```bash
   python scripts/unique_analyzer.py --unique "<name>"            # detailed lookup
   python scripts/unique_analyzer.py --ascendancy "<name>"        # find synergies
   python scripts/unique_analyzer.py --skill "<name>"             # skill synergies
   python scripts/unique_analyzer.py --build "<description>"       # description match
   python scripts/unique_analyzer.py --compare "<A>" "<B>"         # side-by-side
   ```
3. The analyzer scores uniques by: direct ascendancy synergy, mechanic overlap,
   tag matching, archetype alignment.
4. Load `references/unique-synergies.md` for common synergy patterns.
5. In build design, integrate unique recommendations into the gear section.
   Mark which slots use uniques vs rares — never sacrifice life/resists on
   too many slots for unique effects.

### Entry I: Gem Optimization

When the user asks to optimize gem links or compare skills:

1. Use `gem_analyzer.py` (extends `gem_linker.py`):
   ```bash
   python scripts/gem_analyzer.py --skill "<name>" --simulate-dps --links 5
   python scripts/gem_analyzer.py --skill "<name>" --optimize-links 5
   python scripts/gem_analyzer.py --skill "<name>" --check-requirements --str X --dex Y --int Z
   python scripts/gem_analyzer.py --skill "<name>" --matrix       # full synergy matrix
   python scripts/gem_analyzer.py --compare "<A>" "<B>"            # skill comparison
   ```
2. DPS simulation uses: base damage × effectiveness × APS × level scaling
   × quality bonus × support multipliers.
3. Support selection: greedy algorithm — best damage supports first,
   then utility/defense. At most 4 pure damage supports to avoid
   diminishing returns.
4. Check attribute requirements: STR/DEX/INT scale with gem level (~5% more
   per level). Flag gaps and suggest gear/passive solutions.

### Entry J: Passive Tree Optimization

When the user asks to optimize or audit their passive tree:

1. Use `build_optimizer.py`:
   ```bash
   python scripts/build_optimizer.py --spec spec.json --travel-report
   python scripts/build_optimizer.py --spec spec.json --find-clusters
   python scripts/build_optimizer.py --spec spec.json --what-if <old> --replace-with <new>
   python scripts/build_optimizer.py --spec spec.json --optimize-budget <max_points>
   python scripts/build_optimizer.py --spec spec.json --consolidate
   ```
2. Travel report: analyzes travel node %, notables-per-travel ratio,
   dead-end paths, and assigns efficiency grade (A-F).
3. Cluster discovery: groups nearby notables into efficiency-scored clusters.
   High-value clusters are compact notables with few travel nodes.
4. Node swap simulation: "what if we drop X for Y?" — shows point savings
   and connectivity impact.
5. Budget optimization: removes lowest-value nodes to fit a point budget
   while preserving connectivity.

### Entry K: Crafting Probability Simulation

When the user asks about crafting cost, odds, or craft vs buy:

1. Use `craft_simulator.py`:
   ```bash
   python scripts/craft_simulator.py --slot "<slot>" --desired-mods <mod1> <mod2> ...
   python scripts/craft_simulator.py --slot "<slot>" --desired-mods ... --method essence_spam
   python scripts/craft_simulator.py --slot "<slot>" --desired-mods ... --vs-buy --budget 100
   ```
2. The simulator shows: per-mod hit probability, overall success chance,
   expected crafting attempts, estimated currency cost, and alternative
   method comparisons.
3. Uses mod weights from `fetch_poe2_data.py` (21 groups, community-sourced).
4. For craft vs buy: compares crafting cost to trade estimates and
   recommends which approach.

### Entry L: Trade Search

When the user wants to find items on trade:

1. Use `trade_finder.py`:
   ```bash
   python scripts/trade_finder.py --slot "<slot>" --mods <mod1> <mod2> --max-price 50
   python scripts/trade_finder.py --slot "<slot>" --mods ... --url-only  # browser URL
   ```
2. Generates a poe2 trade search URL with mod filters.
3. With POESESSID: performs live API search and returns top listings.
4. For character upgrades: `python scripts/trade_finder.py --upgrade-for <char> --account <name>`

### Entry M: Enhanced DPS Simulation

When the user wants accurate DPS estimates:

1. Use `dps_simulator.py`:
   ```bash
   python scripts/dps_simulator.py --skill "<name>" --links 5 \
     --auras "Herald of Ash" "Anger" --monster-tier T16
   python scripts/dps_simulator.py --skill "<name>" --charges frenzy:3,power:3
   python scripts/dps_simulator.py --skill "<name>" --list-auras
   ```
2. Factors in: support gem multipliers, aura/buff effects, charge bonuses,
   conditional damage (full life, shocked, etc.), penetration, monster
   resistances per Waystone tier, and pinnacle boss DPS.
3. Shows raw DPS, effective DPS vs chosen content tier, and pinnacle DPS.

### Entry N: Data Caching

Before any build work, ensure caches are fresh:

1. `python scripts/fetch_poe2_data.py --force` — item bases + mod weights
2. `python scripts/fetch_tree.py --force` — skill tree (5K+ nodes)
3. `python scripts/fetch_gem_data.py --force` — gem tag reference
4. `python scripts/fetch_unique_data.py --force` — unique item reference

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
11. **Use crafting_advisor.py for crafting plans**, not memorized recipes.
    iLvl breakpoints, mod pool availability, and crafting costs shift.
12. **Unique items: don't recommend more than 2-3 per build.** Uniques
    trade stats for mechanics — rares fill life/resist gaps.
13. **Never skip attribute requirement checks.** Gems scale requirements
    with level — use `gem_analyzer.py --check-requirements`.
14. **Homebrew is not a reliable installer on macOS.** If you get weird C++
    compiler or OpenSSL errors when installing something, use pip in your
    active venv, conda install, or nix profile install before trying
    brew install. brew is a last resort.

## Verification Checklist

- [ ] Data caches fresh (`python fetch_poe2_data.py --stats`)
- [ ] Tree data current (`python fetch_tree.py --stats`)
- [ ] Unique data cached (`python fetch_unique_data.py --stats`)
- [ ] All passives are real node IDs from data.json
- [ ] Gem IDs verified from poe2db.tw or gem_analyzer.py matrix
- [ ] Attribute requirements checked (`--check-requirements`)
- [ ] Auras and buffs factored into DPS (`dps_simulator.py`)
- [ ] Monster resistance accounted for in DPS estimates
- [ ] Gear mods sourced from poe2db.tw Mods or crafting_advisor.py
- [ ] Crafting plans generated via crafting_advisor.py
- [ ] Crafting probabilities simulated via craft_simulator.py
- [ ] Trade searches generated via trade_finder.py where applicable
- [ ] Unique synergies analyzed via unique_analyzer.py
- [ ] Tree travel efficiency graded (build_optimizer.py --travel-report)
- [ ] All mechanics claims have source tags
- [ ] `[ESTIMATED]` used where unverifiable
- [ ] Resistance penalty accounted for
- [ ] HC/SSF design principles applied
- [ ] Build spec validates with `generate_build.py --xml`
- [ ] Human-readable summary covers all sections
