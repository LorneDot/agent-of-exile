# PoE2 Crafting Reference

Quick reference for crafting decisions. Full data in `scripts/crafting_advisor.py`.

## Mod Types

### Prefixes (up to 3 per rare item)
- `life_flat` — +X to maximum Life
- `es_flat` — +X to maximum Energy Shield
- `armour_flat` / `evasion_flat` — +X to Armour/Evasion
- `life_percent` / `es_percent` — X% increased Life/ES
- `flat_phys` — Adds X to Y Physical Damage
- `increased_phys` — X% increased Physical Damage
- `flat_elemental` — Adds X to Y Fire/Cold/Lightning Damage
- `spell_damage` — X% increased Spell Damage
- `spirit` — +X to Spirit
- `rarity` — X% increased Rarity of Items found

### Suffixes (up to 3 per rare item)
- `resistance` — +X% to Fire/Cold/Lightning Resistance
- `attribute` — +X to Strength/Dexterity/Intelligence
- `attack_speed` — X% increased Attack Speed
- `movement_speed` — X% increased Movement Speed
- `crit_chance` — X% increased Critical Strike Chance
- `crit_multiplier` — +X% to Critical Strike Multiplier

## iLvl Breakpoints

Higher iLvl unlocks higher tiers of mods. Key thresholds:

| Threshold | Unlocks |
|-----------|---------|
| iLvl 60 | T4-T5 mod tiers, decent for early maps |
| iLvl 75 | T2-T3 mod tiers, solid for red maps |
| iLvl 82 | T2 mod tiers, pinnacle-ready |
| iLvl 85+ | T1 mod tiers, best-in-slot |

## Crafting Methods (by budget)

### Low Budget (1-10c)
1. Transmute → Augment → Regal → Exalt
2. Essence craft (Screaming) for 1 guaranteed mod
3. Buy finished item from trade (often cheapest)

### Medium Budget (10-50c)
1. Greater Essence spam for T3+ guaranteed mod
2. Regal → Exalt slam → Annul bad mods
3. Meta-crafting: "Prefixes cannot be changed" + scour for targeted reroll

### High Budget (50c+)
1. Essence spam until 3+ desired mods
2. Multimod: "Can have up to 3 Crafted Modifiers"
3. Divine orbs to perfect roll ranges
4. Vaal orb for corruption implicits (risk/reward)

## Rune Sockets

- Most armor pieces can have 1-2 rune sockets
- Add via Artificer's Orb (~1c)
- Common runes: Iron (phys), Storm (lightning), Cold, Fire
- Rune bonuses are flat stats, not affected by % increases

## Harvest Crafting

- Resistance swaps: fire ↔ cold ↔ lightning (guaranteed)
- Useful for fixing resist imbalances on otherwise good items
- Reforge with [element] mod: full reroll with guaranteed element tag
