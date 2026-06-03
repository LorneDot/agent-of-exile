---
name: poe2-theory-crafter
description: "Use when the user asks to theory-craft, design, plan, or create a Path of Exile 2 build — from any starting point: a specific skill gem, a class, an ascendancy, a playstyle, or an unconventional off-meta concept. Computes character stats (EHP, resists, DPS, mana) and outputs GGG-compatible build planner files."
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [poe2, path-of-exile-2, theory-crafting, build-planner, arpg, gaming, stats]
    related_skills: []
---

# PoE2 Theory Crafter

## Overview

Design Path of Exile 2 builds from any starting point — a skill gem, a class,
an ascendancy, or a playstyle archetype. This skill gives you comprehensive
knowledge of PoE2 mechanics, stat formulas, and build design principles to
create viable, well-rounded builds. Outputs a GGG-compatible build planner
file that can be imported into the official planner or any compatible tool.

**Knowledge grounding:** Every mechanic in this skill is traceable to a
documented source — GGG patch notes, developer posts, in-game tooltips, or
the official `poe2-skilltree-export` data. When you make a claim, cite your
source. When a mechanic is unverified, mark it clearly as `[ESTIMATED]`.

## When to Use

Trigger on any of these:

- "theory craft a PoE2 build for..."
- "design a build using [skill gem]"
- "what class works best with [skill]?"
- "make a tanky [class] build"
- "hardcore viable [archetype]"
- "SSF league starter using [skill]"
- "glass cannon [ascendancy] for bossing"
- "can you make a [class] that uses [skill] work?" (unconventional / off-meta)
- "is it possible to do [weird idea] in PoE2?"
- "meme build" or "off-meta build"
- User mentions PoE2 builds, passives, skill gems in a planning context
- User asks to calculate stats, EHP, DPS for a build

Don't use for: PoE2 lore questions, boss strategy guides, trade price checks,
or non-build mechanics questions.

## Quick Start

```bash
cd scripts
python fetch_tree.py --force  # one-time: fetch 5102-node skill tree
```

Tree data caches at `~/.cache/poe2-theory-crafter/tree-data.json`.

## Source Citation System

Every mechanic claim must cite its source using these tags:

| Tag        | Source                                   | Confidence |
|-----------|------------------------------------------|------------|
| `[GGG-IG]`  | In-game tooltip / character panel       | Confirmed  |
| `[GGG-PN]`  | Official patch notes from pathofexile2.com | Confirmed |
| `[GGG-DEV]` | Developer post, interview, or manifesto   | Confirmed  |
| `[TREE]`    | poe2-skilltree-export data.json          | Confirmed  |
| `[COMM]`    | Community-verified (wiki, maxroll, PoB2) | High confidence |
| `[ESTIMATED]` | Reasonable estimate, not confirmed    | Speculative |

**Critical rule:** If you cannot cite a source for a mechanic, state that
explicitly and mark it `[ESTIMATED]`. Never present speculation as fact.
When the user asks about an unverified mechanic, tell them it's unverified.

## Multi-Entry Workflows

The user can start from three different entry points. Detect which one
they're using and follow the corresponding workflow.

### Entry A: Skill-First ("I want a build using Fireball")

1. **Identify the skill gem** — what tags does it have? (fire, spell, projectile, AoE, etc.)
2. **Find synergies** — what ascendancy passives, support gems, and items amplify this skill?
3. **Pick the best class/ascendancy** — which ascendancy provides the most synergy?
   - Does it scale with crit? Look for crit ascendancies.
   - Does it use minions? Infernalist, Feral Druid.
   - Does it chain/projectile? Deadeye.
   - Is it a lightning spell? Stormweaver.
4. **Build the tree outward** from the chosen class start, prioritizing relevant clusters.
5. **Select supports** — supports that provide "more" multipliers matching the skill's tags.
6. **Design defense** — what defensive layers make sense for this skill's playstyle?
7. **Compute stats** — run `calc_stats.py` on the build spec.
8. **Generate output** — produce the build file + summary.

### Entry B: Class-First ("I want a Witch build")

1. **List ascendancy options** for the class (from `data.json`).
2. **Present archetypes** — what does each ascendancy excel at?
3. **Ask clarifying question** — "What playstyle: caster, minion, DoT, hit-based?"
4. **Select skills** that match the ascendancy's strengths.
5. **Build tree** starting from the class position.
6. **Design defense** appropriate for the class's attribute alignment.
7. **Compute stats + generate output.**

### Entry C: Ascendancy-First ("I want an Infernalist build")

1. **Confirm the class** (Infernalist → Witch).
2. **Summarize ascendancy mechanics** — what makes this ascendancy special?
3. **List synergistic skills** — what skills benefit most from the ascendancy?
4. **Design around ascendancy keystones** — the build must leverage the
   ascendancy's defining passives.
5. **Build tree + select supports + design defense.**
6. **Compute stats + generate output.**

### Entry D: Risk Profile / League Mode (applied on top of A/B/C)

When the user specifies a risk profile or league mode, use these as design
guidelines — not hard requirements. PoE2's meta shifts with every league,
and what was "tanky" in one patch may be "barely surviving" in the next.
Treat these as directional preferences, not pass/fail gates.

**Risk Profiles — design principles, not rules:**

| Profile     | Direction | Playstyle Notes |
|------------|-----------|-----------------|
| Glass Cannon | Favor damage over defense. Accept dying occasionally. | Kills before being killed. Softcore only. May use 6-portal defense. |
| Balanced     | Roughly even split between offense and defense. | Standard mapping. Can take some hits. |
| Tanky        | Lean into defense. Accept slower clear speed. | Prioritizes not dying. Good for bossing, simulacrum, deep delve. |
| Hardcore     | Maximum survivability. Every gear slot has life/ES. | Avoid ALL rippy content. Overcap resists. Multiple layered defenses. |

These numbers shift with patches — use them as rough orientation, not
pass/fail checks. If a new league doubles monster damage, double the EHP
expectation. The principle ("hardcore means prioritize survival over all
else") is what matters, not the specific number.

**Hardcore design principles** `[GGG-IG]`:
- Positive chaos resistance (typically 30%+ in current meta).
- Overcap elemental resists for exposure/curses (how much depends on content).
- At least 2 distinct defensive layers (armour + block, evasion + ES, MoM + regen, etc.).
- Corrupted Blood immunity (jewel implicit or flask).
- Freeze immunity (charm, ascendancy, or flask).
- Life or ES on every gear piece. Damage-only items are a luxury.

**SSF design principles:**
- Avoid trade-only uniques. Boss-drop, divination-card, or target-farmable items only.
- Deterministic crafting over RNG (essences, harvest, expedition).
- More passives into defense since gear will be weaker than trade league.
- Generic damage scaling > highly specialized (easier to gear).

### Entry E: Unconventional / Off-Meta ("make a melee Witch work")

When the user wants to tie nonstandard mechanics together — a class using
skills it wasn't designed for, a defensive archetype using an offensive
ascendancy, or any build that violates normal PoE2 conventions:

1. **Identify the core constraint** — what makes this unconventional?
   - Wrong starting position on the tree (melee Witch starting in INT area)?
   - Wrong attribute alignment (spellcaster Marauder with low INT)?
   - Wrong ascendancy synergy (minion ascendancy with no minion skills)?
   - Anti-synergy mechanics that somehow cancel out?

2. **Find the bridge** — what mechanic allows this to work?
   - **Unique items** that enable the playstyle (e.g., "Your strength provides
     spell damage", specific conversion uniques).
   - **Keystones** that flip normal rules (CI, MoM, Avatar of Fire, Blood
     Magic, Iron Reflexes).
   - **Ascendancy passives** with unusual synergies when combined across
     mechanics.
   - **Cluster jewels / timeless jewels** that provide access to mechanics
     normally out of reach.
   - **Gem interactions** — trigger gems, cast-on-X, weapon-swap tech.

3. **Trace the tree path** — how do you get from the class start to the
   relevant clusters? Is the travel cost worth it? What do you give up?

4. **Calculate the tax** — unconventional builds often pay a heavy travel
   or opportunity cost. Quantify it: "You'll spend ~20 extra passive points
   traveling to the melee area, costing ~30% life and 40% damage compared
   to a Warrior doing the same thing."

5. **Find the payoff** — why do this instead of the conventional approach?
   - Unique ascendancy synergy: "A melee Witch gets Infernalist's fire
     damage scaling on her melee hits."
   - Defensive advantage: "A spellcasting Marauder gets easy access to
     endurance charges and armour."
   - Novel mechanic: "Combining Gemling Legionnaire's gem quality bonus
     with [skill] creates an interaction not possible on other classes."

6. **Be honest about viability** — unconventional builds range from
   "surprisingly good" to "meme-tier." Clearly state where this one falls
   and what content it can realistically handle.

7. **Design defense around the constraint** — the unconventional path
   often leaves defense gaps. Be explicit about how you're covering them.

**Examples of unconventional build bridges:**
- Melee Witch → Infernalist fire damage applies to melee hits → fire-converted
  attack skills.
- Caster Marauder → Chieftain-esque fire spell scaling, strength-stacking
  with unique that gives spell damage per strength.
- Bow Sorceress → Stormweaver elemental scaling on bow attacks using flat
  elemental damage from auras.
- Minion Ranger → Deadeye projectile bonuses don't help minions directly,
  but "minion damage affects you" or link skills could bridge it.
- CI Duelist → Iron Reflexes + CI (travel heavy, but possible with unique
  that grants ES from evasion).

## PoE2 Mechanics Reference

### Attributes `[GGG-IG]`

| Attribute | Grants                                      |
|-----------|----------------------------------------------|
| Strength  | +2 max life per point, melee damage bonus    |
| Dexterity | +5 accuracy per point, evasion bonus         |
| Intelligence | +2 max mana per point, ES bonus          |

PoE2 gives **no automatic attributes per level** `[GGG-DEV]`. All attributes
come from the passive tree (+5 per travel node) and gear.

Base attributes per class `[TREE]`:

| Class      | STR | DEX | INT |
|-----------|-----|-----|-----|
| Warrior   | 15  | 7   | 7   |
| Witch     | 7   | 7   | 15  |
| Ranger    | 7   | 15  | 7   |
| Sorceress | 7   | 7   | 15  |
| Mercenary | 11  | 11  | 7   |
| Monk      | 7   | 11  | 11  |
| Huntress  | 7   | 15  | 7   |
| Druid     | 11  | 7   | 11  |
| Marauder  | 15  | 7   | 7   |
| Duelist   | 11  | 11  | 7   |
| Shadow    | 7   | 11  | 11  |
| Templar   | 11  | 7   | 11  |

### Life, Mana, Energy Shield `[GGG-IG]`

**Life formula:**
```
Total Life = (BASE + LEVEL×12 + STR×2 + flat_gear) × (1 + %increased/100)
```
`BASE = 40` at level 1. No automatic life per passive point `[GGG-DEV]`.

**Mana formula:**
```
Total Mana = (BASE + LEVEL×6 + INT×2 + flat_gear) × (1 + %increased/100)
```
`BASE = 40` at level 1.

**Energy Shield:**
```
Total ES = flat_ES_from_gear × (1 + (%increased_from_tree + INT×0.2)/100)
```
ES recharge: 33% per second after 2 seconds of not taking damage `[GGG-IG]`.
"Faster start of ES recharge" reduces the 2-second delay.

### Spirit System `[GGG-DEV]` `[GGG-IG]`

- Base: 100 Spirit (gained through campaign) `[GGG-DEV]`
- Additional sources: gear affixes, passive tree, ascendancy nodes
- Used by: aura skills, herald skills, meta gems, persistent buffs
- Spirit reservation is flat (not percentage of mana as in PoE1)
- Each aura/herald reserves a specific amount of Spirit

### Damage Formula `[GGG-MAN]` `[COMM]`

**Hit damage:**
```
Damage = (BaseFlat + AddedFlat) × (1 + Σ increased/100) × Π(1 + more/100)
       × effectiveness_of_added_damage
```

- `BaseFlat`: skill gem's base damage at current level
- `AddedFlat`: flat damage from gear, supports, auras (e.g., "Adds 10-20 fire damage")
- `Σ increased`: sum of all "increased" modifiers (additive)
- `Π (1 + more)`: product of all "more" modifiers (multiplicative)
- `effectiveness`: skill-specific multiplier on added damage (e.g., 150% = 1.5×)

**DoT damage:**
```
DoT DPS = (BaseDoT + AddedFlat) × (1 + Σ increased/100)
        × Π(1 + more/100) × (1 + Σ DoT_multi/100)
```
Ignite is 90% of base fire hit per second for 4 seconds `[GGG-IG]`.

**Damage conversion** `[GGG-IG]`:
- Converts at each step: phys→light→cold→fire→chaos (one direction only)
- "Gain X% as extra Y damage" applies at each conversion step
- Converted damage is affected by modifiers to both the original AND resulting type

### Critical Strikes `[GGG-IG]`

- Base crit chance: depends on weapon/skill (typically 5-7% for attacks,
  5-6% for spells) `[COMM]`
- Base crit multiplier: 150% (100% base + 50% bonus)
- Crit chance formula: `base_crit × (1 + Σ %increased_crit_chance/100)`
- "Critical strike chance is lucky" = roll twice, take better `[GGG-IG]`
- Perfect agony keystone: crit multi applies to ailments instead of hits
- Some spells and support gems have specific base crit chances

### Impale `[GGG-IG]` (Physical Attacks Only)

- Each impale stores 10% of physical hit damage
- On next 5 hits against that enemy, deals the stored damage
- Default max: 5 impales per enemy
- "Impales last 1 additional hit" increases the 5-hit counter
- "Impale effect" increases the 10% stored damage
- Impale is reflected damage: ignores your offensive modifiers on the
  trigger hit but respects enemy mitigation `[COMM]`

### Weapon Swap System `[GGG-DEV]`

- PoE2 allows dual weapon setups with instant swap
- Each weapon set can have separate passive tree allocations
- Skills can be assigned to a specific weapon set
- Enables hybrid playstyles (melee swap to ranged, etc.)
- Weapon swap nodes on the tree let you allocate different passives per weapon set

### Defensive Mechanics

#### Armour `[GGG-DEV]` `[COMM]`

```
Damage Reduction % = Armour / (Armour + 5 × RawHitDamage)
```

- Same formula as PoE1, confirmed for PoE2 `[GGG-DEV]`
- Strong vs many small hits, weak vs single large hits
- PDR is calculated per-hit, not as a flat percentage
- Armour does NOT protect against elemental or chaos damage
- "Armour applies to elemental damage" effects exist (e.g., Transcendence keystone-like) `[ESTIMATED]`

#### Evasion `[GGG-DEV]` `[COMM]`

```
Chance to Evade = 1 - AttackerAccuracy / (AttackerAccuracy + (Evasion×0.25)^0.8)
```

- Uses entropy system (prevents streakiness) `[GGG-IG]`
- Evasion checks against attacks only, not spells
- Evasion rating has diminishing returns at very high values
- Blind reduces enemy accuracy (effectively increases your evasion chance)

#### Block `[GGG-IG]`

- Shield block: chance to negate all damage from a hit
- Default block cap: 75% `[COMM]`
- "Recover life on block" or "Recover ES on block" for sustain
- Staff block exists for certain weapon types
- Spell block is separate from attack block
- Glancing Blows keystone: double block chance, take 65% of blocked damage `[GGG-IG]`

#### Spell Suppression `[GGG-IG]` (DEX-adjacent)

- Chance to halve spell damage taken (suppressed)
- Capped at 100%
- Does not stack with spell block; you invest in one
- Accessed via DEX/Shadow area passives and gear suffixes

#### Mind Over Matter `[GGG-IG]`

- 40% of damage taken from mana before life
- Mana recovery becomes a defensive stat
- Pairs with high mana pool + mana regen
- Archmage adds lightning damage based on max mana — strong MoM synergy

#### Resistance Penalties `[GGG-IG]` `[GGG-PN]`

PoE2 applies negative resistance penalties as you progress:
- Act 1-3 (Normal): no penalty (0%)
- Act 1-3 (Cruel): -10%
- Act 4-6: -20% `[COMM]`
- Endgame (maps): -60% total

Chaos resistance does NOT receive the campaign penalty. It starts at 0%
and can go positive or negative from gear/passives.

**Resistance cap:** 75% by default, raised by "+X% to maximum [element] resistance"
mods on gear, passives, and ascendancies. Hard cap at 90% `[GGG-IG]`.

### Ailments `[GGG-IG]`

| Ailment    | Type    | Effect |
|-----------|---------|--------|
| Ignite    | Fire    | 90% of base hit/sec for 4 sec (fire DoT) |
| Shock     | Lightning | +20% damage taken per stack, +5% per 5% shock effect. Max 50% without inc max. |
| Chill     | Cold    | Slow 10-30% based on cold damage vs enemy life |
| Freeze    | Cold    | Completely immobilize, duration based on damage |
| Electrocute | Lightning | Stun-like interrupt based on lightning damage |
| Bleed     | Physical | Physical DoT while moving (70% base for moving, 10% stationary) |
| Poison    | Chaos    | Chaos DoT stacking, 20% of phys+chaos hit/sec for 2 sec (base) |
| Corrupted Blood | Physical | Stacking physical DoT, removed by staunching |

Ailment threshold: Ailments with non-damaging effects (chill, freeze, shock,
electrocute) require a minimum % of enemy life as damage to apply.
Increased ailment effect lowers this threshold `[GGG-IG]`.

### Charges `[GGG-IG]`

| Charge     | Effect per Charge |
|-----------|-------------------|
| Endurance | Physical damage reduction, elemental resistances |
| Frenzy    | Attack/cast speed, damage |
| Power     | Critical strike chance |

- Default max: 3 charges each (extendable via tree/ascendancy)
- Charges are NOT automatically generated. Need a generation mechanism
  (on-kill, on-crit, on-block, warcry, enduring cry, etc.)
- Charge duration: ~10 seconds base, refreshed on new charge gain

### Flasks `[GGG-IG]`

- 2 flask slots (life + mana by default, utility flasks exist)
- Flasks refill from killing monsters (not from town/well)
- Flask modifiers: instant recovery, duration, charges gained, etc.
- Unique flasks provide powerful build-defining effects
- "Mageblood" effect exists on certain uniques (permanent flask uptime)

### Charms `[GGG-IG]` `[ESTIMATED]`

- Equipped in charm slots (from belt implicit)
- Provide conditional immunities or buffs
- Examples: freeze immunity, ignite removal, stun protection
- Up to 3 charm slots on high-end belts

### Leech `[GGG-IG]`

- Life leech: recovers life based on damage dealt
- Mana leech: recovers mana based on damage dealt
- Leech is NOT instant — it recovers over time
- Default leech rate cap: 20% of max life/sec for life, 20% of max mana/sec for mana
- "Increased maximum total recovery per second from life leech" raises the cap
- Leech instances stack, each recovering at the capped rate
- "Instant leech" exists on specific unique items or ascendancy passives

### Minion Mechanics `[GGG-IG]`

- Minion damage scales with your "minion damage" modifiers
- Minions have their own accuracy, crit, and defense stats
- Minion life/resists come from "minion life" and "minion resistances" passives
- Spirit is used to maintain permanent minions (skeletons, zombies, spectres)
- Some minion skills use mana (temporary minions like SRS)
- Minion instability: low-life minions explode for % of their max life as fire damage
- Minion crit scales from your "minion critical strike" modifiers

### Totems, Traps, Mines `[GGG-IG]`

- Totems use your offensive stats but are separate entities
- Ancestral Bond: +1 totem, you deal no damage yourself
- Traps/Mines: thrown skills that trigger on enemy proximity/detonation
- Trap/mine damage scales from "trap damage" and "mine damage" modifiers

### Endgame Systems (relevant for build planning) `[GGG-IG]`

- **Atlas Passive Tree**: separate tree for map modifiers. Has its own points.
  You'll get ~30-40 atlas passive points by endgame.
- **Delirium**: adds difficulty multiplier, more rewards, cluster jewels drop
- **Breach**: density + splinters → breachstones → boss
- **Expedition**: crafting currency + logbooks → bosses
- **Ritual**: tribute system, reroll favors, deferred items
- **Sanctum**: relic-based runs, resolve mechanic (no-hit builds viable)

### Level Scaling `[ESTIMATED]` `[COMM]`

Passive points by level 80:
- 80 points from levels (1 per level starting at level 1)
- 24 points from quest rewards (campaign)
- Total: ~104 passive points at level 80

Passive points by level 100: 124 (100 from levels + 24 from quests)

## Stat Calculation Guide

Use the `calc_stats.py` script to compute numbers from a build spec:

```python
from calc_stats import compute_stats

stats = compute_stats({
    "className": "Witch",
    "ascendClassName": "Infernalist",
    "level": 80,
    "treeAttributes": {"str": 60, "dex": 40, "int": 200},
    "increasedLifeFromTree": 80,
    "flatLifeFromGear": 400,
    "flatESFromGear": 2000,
    "increasedESFromTree": 150,
    "gearResistances": {"fire": 90, "cold": 80, "lightning": 75, "chaos": 30},
    "estimatedMainSkillDPS": 50000,
    "averageHitDamage": 2500,
})

print(stats.summary())
```

The script computes:
- Total life, mana, energy shield
- Effective HP vs elemental damage (accounting for average resists)
- Resistance totals after campaign penalties
- Armour damage reduction against specific hit sizes
- Estimated DPS with crit and accuracy factored in

**Important:** The user must provide reasonable estimates for `flatLifeFromGear`,
`increasedLifeFromTree`, `estimatedMainSkillDPS`, etc. You guide them on
reasonable values based on the build's budget and archetype.

### Reasonable Stat Ranges `[COMM]`

| Stat                 | League Starter | Mid-Budget  | Mirror-Tier  |
|---------------------|---------------|-------------|--------------|
| Life at Lv80         | 2,500-3,500  | 3,500-5,000 | 5,000-7,000  |
| ES at Lv80           | 3,000-5,000  | 5,000-8,000 | 8,000-15,000 |
| Combined EHP         | 4,000-5,500  | 6,000-9,000 | 10,000-20,000|
| Ele Res (after pen)  | 75%          | 75%         | 80-85%       |
| Chaos Res            | 0-20%        | 30-60%      | 75%          |
| Main Skill DPS       | 10K-50K      | 50K-200K    | 200K-1M+     |
| Attacks/Casts per sec| 1.5-3.0      | 3.0-6.0    | 6.0-12.0     |

## Build Output Format

### Phase 7: Generate the Build File

After designing the build, produce the GGG-compatible file:

```python
from generate_build import generate_build_string

spec = {
    "className": "Witch",
    "ascendClassName": "Infernalist",
    "level": 80,
    "passives": ["50459", "47175", ...],  # Real node IDs from data.json
    "skills": [
        {
            "setName": "Default",
            "skills": [{
                "gems": [
                    {"id": "Metadata/Items/Gems/SkillGemFireball",
                     "level": 20, "quality": 20},
                    {"id": "Metadata/Items/Gems/SupportGemSpellEcho",
                     "level": 20, "quality": 20},
                ]
            }]
        }
    ],
    # Optional stat estimation fields for the calculator:
    "treeAttributes": {"str": 80, "dex": 80, "int": 180},
    "increasedLifeFromTree": 60,
    "flatLifeFromGear": 400,
    "flatESFromGear": 1500,
    "increasedESFromTree": 120,
    "gearResistances": {"fire": 90, "cold": 90, "lightning": 90, "chaos": 35},
    "estimatedMainSkillDPS": 120000,
    "averageHitDamage": 3500,
    "campaignProgress": "endgame",
    "notes": "Build guide notes here"
}

build_string = generate_build_string(spec)
Path("build.txt").write_text(build_string)
```

### Human-Readable Summary

Always produce a structured summary:

```
╔══════════════════════════════════════════╗
║        [BUILD NAME]                      ║
║  [Class] → [Ascendancy] | Level [X]     ║
║  Risk: [Glass/Balanced/Tanky/HC/SSF]    ║
╚══════════════════════════════════════════╝

STARTING POINT: [skill-first / class-first / ascendancy-first]

--- STAT ESTIMATES ---
[Summary from calc_stats.py]
EHP: X | Res: F/C/L/Ch | DPS: X

--- ASCENDANCY ---
Node 1: [name] — [effect]
Node 2: [name] — [effect]
...

--- SKILL GEMS ---
Main: [SkillGem] (Lv.20/Q20)
  ↳ [SupportGem] — [what it adds]
  ↳ [SupportGem] — [what it adds]
  ↳ [SupportGem] — [what it adds]

Auras/Buffs:
  ↳ [SpiritGem] — [reserves X Spirit]
  ↳ [SpiritGem] — [reserves X Spirit]

--- PASSIVE TREE ---
[X] points allocated
Keystones: [list with brief rationale]
Key notables: [list]
Defense clusters: [list]

--- GEAR PRIORITIES ---
Weapon:   [base type] — [key mods]
Offhand:  [shield/focus/2nd weapon]
Helm:     [base] — [key mods]
Amulet:   [base] — [key mods]
Rings:    [base] — [key mods]
Belt:     [base] — [key mods]
...

--- PLAYSTYLE ---
[Brief description of how to play the build]

--- IMPORT ---
Build file: build.txt
Copy the contents and paste into the PoE2 planner import dialog.
```

## Common Pitfalls

1. **Don't hallucinate node IDs.** Only use IDs from the actual `data.json`.
   Fetch with `fetch_tree.py --force` if unsure. Node IDs are strings like
   "50459", never integers or made-up names.

2. **Ascendancy names must match exactly.** Case-sensitive. Get them from the
   `ascendancies` array in the class's `data.json` entry. "Infernalist" not
   "infernalist" or "Infernalist Ascendancy".

3. **Skill gem IDs use Metadata paths.** Examples:
   - Skill: `Metadata/Items/Gems/SkillGemFireball`
   - Support: `Metadata/Items/Gems/SupportGemSpellEcho`
   - Spirit: `Metadata/Items/Gems/SpiritGemHeraldOfAsh`
   These are internal IDs, not display names. Verify from game data when possible.

4. **Resistance penalties must be accounted for.** The -60% endgame penalty
   means you need 135% total resistance per element to cap at 75%. If your
   build summary shows 75% fire res from gear, clarify whether that's the
   total or the post-penalty value.

5. **"More" vs "Increased" is the most important distinction in PoE.**
   "More" is multiplicative — 5 support gems with 30% more = 1.3^5 = 3.71×.
   "Increased" is additive — 5 passives with 30% increased = 1 + 1.5 = 2.5×.
   This is why support gems are build-defining and "increased" has
   diminishing returns `[GGG-IG]`.

6. **Chaos inoculation means 1 life.** CI builds are ES-only. You cannot
   have both CI and life nodes. Don't recommend life gear for CI builds.

7. **Blood Magic = no mana.** Skills cost life instead. Mana-based
   mechanics (Archmage, MoM) don't work. Mana flasks are useless.

8. **Avatar of Fire = only fire damage.** 50% of phys/cold/light converted
   to fire, BUT you deal no non-fire damage. Chaos damage, added cold, etc.
   are wasted.

9. **Don't theory-craft without tree data.** If the cache is empty or stale,
   run `python fetch_tree.py --force` first. Never guess at node IDs.

10. **Attribute requirements matter.** Skill gems require minimum attributes
    to use. A level 20 Fireball might need 150 INT. Verify your build can
    equip its own gems — especially for hybrid classes stretching into
    off-attribute areas.

11. **Mark estimates clearly.** When providing DPS, EHP, or other computed
    values, cite whether they're from `calc_stats.py` (formula-based) or
    rough estimates. Never present an estimate as a precise calculation.

## Verification Checklist

- [ ] Tree data fetched and current (`python fetch_tree.py --stats`)
- [ ] All passives use real node IDs from data.json
- [ ] Ascendancy name matches exactly (case-sensitive)
- [ ] Skill gem IDs use correct Metadata/ paths
- [ ] All mechanics claims have source citations
- [ ] `[ESTIMATED]` tag used where mechanics are unverified
- [ ] Resistance totals account for -60% endgame penalty
- [ ] Hardcore builds: chaos res ≥ 0, overcapped ele res, 2+ defense layers
- [ ] SSF builds: no trade-only uniques
- [ ] Stats computed with `calc_stats.py` where possible
- [ ] Build spec validates: `python generate_build.py spec.json --xml`
- [ ] Human-readable summary covers all sections
