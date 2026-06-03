# GGG PoE2 Build Planner Format

## Overview

Path of Exile 2's official build planner uses a compressed XML format for
import/export. This reference documents the encoding and structure.

## Encoding Pipeline

```
XML → Deflate (zlib) → Base64 (URL-safe) → Build String
```

To encode:
1. Build an XML document with `<Build>` as root
2. Serialize to string
3. Deflate (zlib compress) the string bytes
4. Base64 encode, using URL-safe variant (`-` for `+`, `_` for `/`)

To decode:
1. Replace `-` → `+`, `_` → `/`
2. Base64 decode
3. Inflate (zlib decompress)
4. Parse XML from the resulting string

## XML Schema

### Root: `<Build>`

Attributes:
- `className`: Class name (e.g., "Witch", "Warrior", "Mercenary")
- `ascendClassName`: Ascendancy name (e.g., "Infernalist", "Titan")
- `level`: Character level (1-100)
- `mainSocketGroup`: Index of active socket group (default "1")

### `<Items>`

Container for all equipment items.
- `activeItemSet`: Index of active item set (default "1")

Child: `<Item>` elements, one per equipment slot.
- `id`: Slot identifier (equipment slot name or item ID)

The item text content is the item string representation (like in-game copy).

### `<Skills>`

Container for skill gem setups.
- `activeSkillSet`: Index of active skill set (default "1")

Child: `<SkillSet>` elements.
- `title`: Name of the skill set

Child of `<SkillSet>`: `<Skill>` elements.
- `mainActiveSkill`: Index of the main skill
- `mainActiveSkillCalcs`: Index for skill calculations

Child of `<Skill>`: `<Gem>` elements.
- `gemId`: Item ID of the gem
- `level`: Gem level
- `quality`: Gem quality (0-20)

### `<Passives>`

Passive skill tree allocations.

Child: `<Variant>` elements (one per tree variant).
- `name`: Variant name

Child of `<Variant>`: `<Node>` elements.
- `id`: Passive node ID (matches data.json node keys)

Each `<Node>` contains child `<Stat>` elements that are empty — the node
ID alone identifies the allocation.

### `<Atlas>`

Atlas passive tree allocations. Same structure as `<Passives>`.

### Other Elements

- `<Notes>`: Text notes for the build
- `<PlayerStat stat="..." value="...">`: Stat overrides
- `<Buffs combatList="..." buffList="...">`: Configuration flags
- `<Jewels>`: Socketed jewels with `<Jewel>` elements containing `<ModRange>` etc.
- `<Slot name="..." itemId="...">`: Equipment-to-item slot mapping
