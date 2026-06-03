# PoE2 Verified Mechanics

This file contains only mechanics that are confirmed from GGG sources.
Load it with `skill_view(name='poe2-theory-crafter', file_path='references/verified-mechanics.md')`
when the agent needs formula-level detail.

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

## Where to Find Everything Else

For item mods, gear tiers, gem data, unique items, crafting options, and
league mechanic details — go to poe2db.tw, NOT this file. This file only
contains formulas confirmed by GGG. Everything else is on poe2db.

See `references/sources.md` for the complete source directory.
