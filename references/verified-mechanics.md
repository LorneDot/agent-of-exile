# PoE2 Verified Mechanics

**Current version: 0.5 "Return of the Ancients" / "Runes of Aldur" league**
(Started 2026-05-29. Always check poe2db.tw for latest patch.)

This file contains only mechanics that are confirmed from GGG sources.
Load it with your native file-reading tool when you need formula-level
detail. (In Hermes: `skill_view(name='agent-of-exile', file_path='references/verified-mechanics.md')`)

Do NOT load this file into context by default — load on demand when
the agent needs specific formulas for stat calculation or build design.

## Confirmed from data.json `[TREE]`

### Class Base Attributes
Straight from `grindinggear/poe2-skilltree-export` data.json `classes` array.

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

No automatic attributes per level — all from tree + gear `[GGG-DEV]`.

### Ascendancy Data
Each class has an `ascendancies` array in data.json with:
- `id`: internal identifier (e.g., "Witch1")
- `name`: display name (e.g., "Infernalist")
- `overridePairs`: node ID overrides for ascendancy skill tree

### Skill Tree Stats
- Total nodes: varies by patch (check data.json `nodes` count)
- Total groups: varies (check data.json `groups` count)
- Node structure: `group`, `orbit`, `orbitIndex`, `out`, `in`, `edges`

## Confirmed from GGG Developer Sources `[GGG-DEV]`

### Attribute Bonuses
- +2 max life per Strength `[GGG-IG]`
- +5 accuracy per Dexterity `[GGG-IG]`
- +2 max mana per Intelligence `[GGG-IG]`

### Spirit System
- Base: 100 Spirit gained through campaign `[GGG-DEV]`
- Spirit from: gear affixes, passive tree, ascendancy nodes
- Used by: auras, heralds, meta gems, persistent buffs
- Reservation is flat (not % of mana) — each skill reserves a specific amount

### Weapon Swap
- Dual weapon setups with instant swap `[GGG-DEV]`
- Separate passive tree allocations per weapon set
- Skills assignable to specific weapon sets

### Armour Formula
```
Damage Reduction % = Armour / (Armour + 5 × RawHitDamage)
```
Confirmed same as PoE1 formula `[GGG-DEV]`.

### Evasion Formula
```
Chance to Evade = 1 - Acc / (Acc + (Eva × 0.25)^0.8)
```
Entropy system confirmed `[GGG-IG]`.

## Confirmed from In-Game `[GGG-IG]`

### Life Formula
```
Total Life = (BASE + LEVEL×12 + STR×2 + flat_gear) × (1 + %inc/100)
BASE = 40 at level 1
```

### Mana Formula
```
Total Mana = (BASE + LEVEL×6 + INT×2 + flat_gear) × (1 + %inc/100)
BASE = 40 at level 1
```

### Energy Shield
```
Total ES = flat_ES × (1 + (%inc_tree + INT×0.2)/100)
Recharge: 33%/sec after 2s of no damage
```

### Damage Formula
```
Hit: (Base + AddedFlat) × (1 + Σinc/100) × Π(1 + more/100) × effectiveness
DoT: (Base + AddedFlat) × (1 + Σinc/100) × Π(1 + more/100) × (1 + DoT_multi/100)
```

### Resistance System
- Campaign penalty: -60% to elemental resists at endgame
- Chaos res has no penalty (starts at 0%)
- Default cap: 75%, hard cap: 90%
- "increased" = additive with existing %, "more" = multiplicative

### Ailments
- Ignite: 90% of base fire hit/sec for 4s
- Shock: +20% dmg taken, +5% per 5% shock effect (max 50%)
- Chill: 10-30% slow based on cold dmg vs enemy life
- Freeze: immobilize, duration based on damage
- Bleed: 70% phys DoT moving, 10% stationary
- Poison: 20% phys+chaos hit/sec for 2s (stacking)
- Corrupted Blood: stacking phys DoT, removed by staunching
- Non-damaging ailments require minimum % of enemy life threshold

### Charges
- Endurance: PDR, ele res | Frenzy: AS/CS, damage | Power: crit chance
- Default max: 3 each (extendable)
- NOT auto-generated — need generation mechanism
- ~10s base duration, refreshed on new gain

### Mind Over Matter
- 40% damage taken from mana before life

### Block
- Shield block: negates all damage from a hit
- Default cap: 75% `[COMM]`
- Glancing Blows: double block chance, take 65% of blocked damage

### Leech
- NOT instant — recovers over time
- Default rate cap: 20% max life/sec, 20% max mana/sec
- Leech instances stack up to the cap

## Currency & Crafting Materials `[GGG-IG]` `[GGG-DEV]`

This section establishes what currencies and crafting materials exist so
the agent knows what to look up on poe2db.tw for specific mod pools, tier
names, and current league availability.

### Core Crafting Currencies

These modify items directly. All confirmed `[GGG-IG]` unless noted.

| Currency | Effect | Used for |
|----------|--------|----------|
| Orb of Transmutation | Upgrades normal → magic (1 mod) | First craft step on white bases |
| Orb of Augmentation | Adds 1 mod to magic item (2nd mod) | Finishing magic items |
| Regal Orb | Upgrades magic → rare (adds 1 mod, 3 total) | Making rares from good magic items |
| Exalted Orb | Adds 1 random mod to rare item (up to 6) | Filling mod slots on rares |
| Divine Orb | Rerolls numeric values of all mods within their tiers | Optimizing rolled values |
| Chaos Orb | Rerolls all mods on a rare item (full reroll) | Salvaging or re-crafting rares |
| Orb of Scouring | Removes all mods, returns item to normal rarity | Starting over on a base |
| Orb of Alchemy | Upgrades normal → rare (4 random mods) | Quick rare from white base |
| Vaal Orb | Corrupts item — adds implicit OR changes mods OR bricks | High-risk/high-reward final step |
| Orb of Annulment | Removes 1 random mod from a rare | Removing bad mods before exalting |
| Blessed Orb | Rerolls implicit modifier values | Fixing low implicit rolls |

### Quality & Socket Currencies

| Currency | Effect |
|----------|--------|
| Blacksmith's Whetstone | +1% quality on weapon (max 20%) |
| Armourer's Scrap | +1% quality on armour (max 20%) |
| Glassblower's Bauble | +1% quality on flasks (max 20%) |
| Gemcutter's Prism | +1% quality on skill gems (max 20%) |
| Jeweller's Orb | Rerolls number of sockets on item |
| Orb of Fusing | Rerolls links between sockets |
| Chromatic Orb | Rerolls socket colours |

### Essences `[GGG-DEV]`

Essences guarantee a specific mod type when used on a normal item. Each
essence type corresponds to a mod category (e.g., fire damage, life,
resists). Higher tiers (Whispering → Screaming → Shrieking → Deafening)
provide higher-tier mods.

PoE2 essence tiers and names may differ from PoE1. Look up current names
on poe2db.tw → Essences. The principle is what matters: essences are
targeted crafting for a specific mod type. `[POE2DB]`

### Omens `[GGG-DEV]`

Omens are meta-crafting items that modify the behavior of the next currency
used. GGG has confirmed omens exist in PoE2 and serve as the replacement
for PoE1's crafting bench in many cases. Examples of omen effects
(verify specific names on poe2db.tw):

- Remove the lowest-level modifier on next orb use
- Force a specific mod type outcome
- Reduce the risk of destroying an item on corruption
- Influence socket outcomes

Look up current omen names and effects on poe2db.tw → Omens. `[POE2DB]`

### League-Specific Crafting Materials `[ESTIMATED]`

The existence of these mechanics is confirmed from GGG trailers, but
specific item names and interactions may differ from PoE1:

- **Expedition currencies** — used with Expedition vendors for crafting (Rog, etc.)
- **Breach catalysts** — add quality to jewelry, enhancing specific mod types
- **Delirium orbs** — apply Delirium to maps for cluster jewel farming
- **Fracturing orbs** — lock one mod permanently (unconfirmed in PoE2)

For current availability and specific item IDs: poe2db.tw → [league name].

### Currency Usage in Build Planning

When designing a build, mention currency/crafting only in terms of:

1. **What materials are needed to craft key items** — "Use Shrieking Essence
   of Greed on iLvl 82+ armour base for guaranteed life roll"
2. **What the upgrade path costs** — "5-10 Exalts to finish this weapon
   from an Essence base" (use general terms, not market prices)
3. **What's realistic for the budget** — league starters use Essences and
   basic orbs, not Omens and Divine chains

Never quote orb:chaos ratios or market prices — those change hourly.
Refer to poe2db.tw for crafting mod pools and currency mechanics.

### Crafting Process `[GGG-IG]` `[GGG-DEV]`

This section explains HOW to craft, not just what the currencies do.
The specific orbs used are confirmed — the step sequences are general
patterns that apply regardless of patch.

#### The Basic Crafting Chain

PoE2 crafting follows a linear upgrade path for most items:

```
Normal (white) → Magic (blue, 1-2 mods) → Rare (yellow, 3-6 mods)
```

Each step uses a specific currency:

1. **Start with a base** — acquire a normal item with good base type and
   high enough item level for your desired mod tiers. Quality it first
   (Whetstone/Scrap) — quality persists through crafting.

2. **Make it magic** — Orb of Transmutation adds 1 random mod. If the mod
   is bad, Scour and try again (or use another base). If good, use an
   Orb of Augmentation to add a 2nd mod.

3. **Make it rare** — Regal Orb upgrades magic → rare, adding a 3rd mod.
   You now have 3 mods on the item.

4. **Fill mod slots** — Exalted Orbs add mods 4, 5, and 6. Each Exalt
   is a gamble — you can't control which mod you get without Omens.

5. **Fix or restart** — if the item has 3+ good mods but 1-2 bad ones,
   Orb of Annulment removes a random mod (gamble). If the item is mostly
   bad, Chaos Orb to full reroll, or Scour to restart.

6. **Optimize values** — once you have the right mods, Divine Orb rerolls
   the numeric values within their tiers. Save for items worth investing in.

7. **Final risk** — Vaal Orb as the last step. Can add a powerful implicit,
   reroll mods into corrupted versions, or brick the item entirely.
   Corrupted items cannot be modified further.

#### Targeted Crafting Strategies

**Essence crafting** (most deterministic for league start):
1. Acquire normal base, quality to 20%
2. Use Essence that guarantees your priority mod (e.g., life, flat damage)
3. If the other mods from the essence craft are bad, Scour and try again
4. Once you have the essence mod + 1-2 decent random mods, Regal → Exalt
5. Essence mods cannot be removed by Scouring after the item is rare

**Expedition crafting** (deterministic, mid-budget, SSF-friendly):
1. Use Expedition currency at vendors (primarily Rog for crafting)
2. Rog offers items with specific mod types and can reroll them
3. Tujen provides currency for further crafting
4. More deterministic than Chaos Orbs for building specific items

**Omen-assisted crafting** (high-budget, meta-crafting):
1. Omen of Whittling: next currency removes the lowest-level mod instead
   of adding/rerolling. Use before an Annulment to target bad low-tier mods.
2. Omen of Blanching: next Chromatic Orb produces specific socket colours.
3. Omens are consumed on use — they enable targeted outcomes that basic
   orbs can't achieve.

#### SSF Crafting Strategy

- **Pick up every relevant base.** Volume matters — you'll Scour and retry
  dozens of times.
- **Essences are king.** They're the most deterministic. Prioritize essence
  farming on the Atlas tree.
- **Expedition is second.** Rog crafting provides targeted items.
- **Don't chase perfection.** A 4-mod item with the right mods clears all
  non-pinnacle content. The difference between 4-mod and 6-mod is usually
  a 15-20% power gain for 10× the cost.
- **Bench crafts fill gaps.** If a crafting bench exists in PoE2, use it
  to add a guaranteed mod (typically a resist or attribute) as the last step.
- **Save Divine Orbs for build-defining items.** They're rare in SSF.
- **Corruption is the final gamble.** Only Vaal items you can afford to lose.

### Runes & Socketables `[GGG-DEV]` `[GGG-IG]`

PoE2 introduces Runes as socketable items that go into gear sockets.
This is separate from the skill gem system — gems have their own sockets
in the gem menu. Gear sockets are for runes, soul cores, and similar items.

**Current league (0.5 "Runes of Aldur"):** The league mechanic expands the
rune system significantly with Runeforging, Runeseeker, Runeshape
Combinations, and Kalguuran Skills. League-specific rune mechanics are
temporary — always check poe2db.tw for current rune data.

#### What Runes Are

- Runes are items that socket directly into gear (body armour, helmet,
  weapons, etc.)
- Each piece of gear has a fixed number of rune sockets based on its
  type and item level
- Runes provide stat bonuses: resistances, attributes, damage, life, etc.
- Once socketed, runes cannot be removed (except possibly with specific
  currency or vendor recipes)
- Runes are NOT gems — they don't grant skills

#### Types of Socketables

| Type | What it does | Source |
|------|-------------|--------|
| Runes | Basic stat bonuses (fire res, life, STR, etc.) | Drops, vendors |
| Soul Cores | Advanced/powerful bonuses (build-enabling effects) | Boss drops, league content |
| [ESTIMATED] Other socketables may exist from league mechanics | | |

Runes are a core part of gearing in PoE2. When designing a build, you
must account for what runes to socket in each gear piece — they're not
optional and provide significant stats.

#### Rune Sockets on Gear `[GGG-IG]`

- Weapons: typically 1-2 rune sockets
- Body armour: typically 1-3 rune sockets
- Helmet, gloves, boots: typically 1 rune socket
- Shields: typically 1-2 rune sockets
- Jewelry (rings, amulet, belt): no rune sockets

The exact number depends on item base type and item level. Two-handed
weapons and high-tier body armour get more sockets.

#### Common Rune Stats `[COMM]` — verify on poe2db.tw

Runes typically provide one of:
- Elemental resistance (fire, cold, lightning — 8-15% per rune)
- Attributes (+10-20 STR/DEX/INT per rune)
- Flat life or energy shield
- Flat added damage (elemental or physical)
- Leech (life or mana)
- Increased damage of a specific type

Soul cores provide more powerful or unique effects. Look up current
rune and soul core stats on poe2db.tw → Runes.

#### Runes in Build Planning

When designing a build:
1. **Count available rune sockets** across all gear
2. **Allocate runes to fill resist gaps** first — runes are the most
   flexible way to fix uncapped resistances
3. **Use remaining sockets for damage or attributes** once resists are capped
4. **Account for rune stats in your total** — 6 sockets × 12% fire res =
   72% fire resistance from runes alone

For character audits: check if the character has unused rune sockets.
Empty sockets are the easiest "free" upgrade in the game.

## Where to Find Everything Else

For item mods, gear tiers, gem data, unique items, crafting options, and
league mechanic details — go to poe2db.tw, NOT this file. This file only
contains formulas confirmed by GGG. Everything else is on poe2db.

See `references/sources.md` for the complete source directory.
