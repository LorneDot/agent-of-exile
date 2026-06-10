# PoE2 Skill Tree Data Format

## Source

GGG publishes the PoE2 passive skill tree data at:
<https://github.com/grindinggear/poe2-skilltree-export>

The main file is `data.json` in the repository root. Current version:
0.5 "Return of the Ancients" / "Runes of Aldur" (as of 2026-06-02).

## Top-Level Structure

```json
{
  "tree": "Default",
  "classes": [...],
  "groups": {...},
  "nodes": {...},
  "edges": [...],
  "skillOverrides": {...},
  "jewelSlots": [...],
  "min_x": -25000, "min_y": -12000,
  "max_x": 25000, "max_y": 12000
}
```

## Classes

Each class entry:
```json
{
  "name": "Witch",
  "base_str": 7,
  "base_dex": 7,
  "base_int": 15,
  "image": "Art/2DArt/BaseClassIllustrations/WitchBaseIllustration.png",
  "image_offset_x": 0,
  "image_offset_y": 0,
  "overridePairs": {
    "4739": 17306,
    ...
  },
  "ascendancies": [
    {
      "id": "Witch1",
      "name": "Infernalist",
      "image": "...",
      "offsetX": 0,
      "offsetY": 1332,
      "flavourText": "...",
      "flavourTextColour": "ffa57e",
      "flavourTextSize": 135,
      "flavourTextRect": {"x": 0, "y": 400, "width": 1000, "height": 500},
      "overridePairs": {...}
    }
  ]
}
```

- `overridePairs` maps node IDs → replacement node IDs for that class's
  starting position on the tree. Each class sees a personalized subset
  of the shared tree.
- Some classes have no ascendancies (Marauder, Duelist, Shadow, Templar
  as of 0.5.0) — these are not yet released.

### Current Ascendancies (from data.json 0.5.0)

| Class      | Ascendancies |
|-----------|-------------|
| Warrior   | Titan, Warbringer, Smith of Kitava |
| Witch     | Infernalist, Blood Mage, Lich, Abyssal Lich |
| Ranger    | Deadeye, Pathfinder |
| Sorceress | Stormweaver, Chronomancer, Disciple of Varashta |
| Huntress  | Amazon, Spirit Walker, Ritualist |
| Mercenary | Tactician, Witchhunter, Gemling Legionnaire |
| Monk      | Martial Artist, Invoker, Acolyte of Chayula |
| Druid     | Oracle, Shaman |
| Marauder  | (not yet released) |
| Duelist   | (not yet released) |
| Shadow    | (not yet released) |
| Templar   | (not yet released) |

Always fetch the latest data.json for current ascendancy lists — these
change between patches.

## Nodes

Each node is keyed by its **string** ID (e.g., "42761", "root"):

```json
{
  "id": "dexterity102",
  "skill": 58397,
  "name": "Proficiency",
  "icon": "Art/2DArt/SkillIcons/passives/plusdexterity.png",
  "stats": ["+25 to Dexterity"],
  "group": 1377,
  "orbit": 0,
  "orbitIndex": 0,
  "x": 8692.14,
  "y": 1153.21,
  "out": ["19338", "31647", "2334"],
  "in": ["24070"],
  "edges": [5289, 5362, 5363, 5364],
  "isNotable": true,
  "isKeystone": false,
  "isJewelSocket": false,
  "isAscendancyStart": false,
  "isMastery": false,
  "isFree": false,
  "isGenericAttribute": false,
  "keystonesInRadius": [34497],
  "recipe": ["ConcentratedLiquidFear", "DilutedLiquidGuilt", "LiquidParanoia"],
  "grantedPassivePoints": null,
  "grantedSkill": null,
  "ascendancyId": null,
  "activeEffectImage": null,
  "flavourText": null,
  "hideConnection": null,
  "unlockConstraint": null
}
```

### Key Node Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Internal identifier (e.g., "dexterity102") |
| `skill` | int | Numeric skill/node ID |
| `name` | string | Display name (e.g., "Proficiency") |
| `stats` | string[] | Human-readable stat descriptions |
| `group` | int | Index into `groups` dict |
| `orbit` | int | Orbit position (0 = closest to center) |
| `orbitIndex` | int | Position along the orbit |
| `x`, `y` | float | Pixel position on tree canvas |
| `out` | string[] | Connected node IDs (outgoing) |
| `in` | string[] | Connected node IDs (incoming) |
| `edges` | int[] | Edge indices (into the `edges` array) |
| `isNotable` | bool | Medium-sized passive (notable) |
| `isKeystone` | bool | Build-defining keystone passive |
| `isJewelSocket` | bool | Jewel socket |
| `isAscendancyStart` | bool | Ascendancy starting node |
| `isMastery` | bool | Mastery passive (choice node) |
| `isFree` | bool | Granted automatically (no point cost) |
| `isGenericAttribute` | bool | +5 attribute travel node |
| `keystonesInRadius` | int[] | Keystone node IDs within radius |
| `recipe` | string[] | Node recipe data (not used for anointing in PoE2) |
| `grantedPassivePoints` | int? | Free points granted |
| `ascendancyId` | string? | Which ascendancy this belongs to |

## Groups

Each group is keyed by integer index and defines a cluster on the tree:

```json
{
  "x": -22597.4,
  "y": -2727.53,
  "orbits": [0],
  "nodes": ["42761"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `x`, `y` | float | Center position on canvas |
| `orbits` | int[] | Orbit radii for this cluster |
| `nodes` | string[] | Node IDs in this cluster |

## Edges

Edges is a **list** (not a dict) of edge objects connecting nodes:

```json
[
  {"from": "root", "to": 50459},
  {"from": "root", "to": 47175},
  ...
]
```

| Field | Type | Description |
|-------|------|-------------|
| `from` | string | Source node ID |
| `to` | int | Target node skill ID |

Note: `to` is an integer (skill ID), not a string node key. Cross-reference
with node `skill` fields when needed.

## Jewel Slots

`jewelSlots` is a list of integer node/skill IDs that are jewel sockets:

```json
[26725, 28475, 48768, ...]
```

## Usage in Build Generation

When generating a build, the allocated passive nodes are the string node
keys from `nodes`. The planner loads `data.json` and interprets which
nodes are allocated based on user selections.

For node traversal during tree pathing:
1. Start from the class root node (found in class `overridePairs`)
2. Follow `out` arrays to reach connected nodes
3. Use `group` and `orbit` to understand cluster layout
4. Check `isNotable` and `isKeystone` for cluster value assessment
5. Use `stats` strings for human-readable node descriptions
