# PoE2 Skill Tree Data Format

## Source

GGG publishes the PoE2 passive skill tree data at:
<https://github.com/grindinggear/poe2-skilltree-export>

The main file is `data.json` in the repository root.

## Top-Level Structure

```json
{
  "tree": "Default",
  "classes": [...],
  "groups": {...},
  "nodes": {...},
  "edges": {...},
  "skillOverrides": {...},
  "jewelSlots": [...],
  "min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0
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
  "image": "...",
  "image_offset_x": 0,
  "image_offset_y": 0,
  "overridePairs": {...},
  "ascendancies": [...]
}
```

`overridePairs` maps node IDs to replacement node IDs for that class's
starting position on the tree.

### Ascendancies

Each ascendancy:
```json
{
  "id": "Witch1",
  "name": "Infernalist",
  "image": "...",
  "offsetX": 0,
  "offsetY": 1332,
  "flavourText": "...",
  "flavourTextColour": "ffa57e",
  "flavourTextSize": 135,
  "flavourTextRect": {...},
  "overridePairs": {...}
}
```

## Nodes

Each node is keyed by its string ID (e.g., "50459", "47175"):

```json
{
  "group": 0,
  "orbit": 0,
  "orbitIndex": 0,
  "out": ["50459", "47175"],
  "in": [],
  "edges": [0, 1, 2, 3]
}
```

- `group`: References the `groups` dict by index
- `orbit`: Position within the group (lower = closer to center)
- `orbitIndex`: Position along the orbit
- `out`: Connected node IDs (outgoing edges)
- `in`: Connected node IDs (incoming edges)
- `edges`: Edge indices within the group

## Groups

Each group defines a cluster of nodes on the tree:

```json
{
  "x": 0, "y": 0,
  "orbits": [100, 150],
  "nodes": ["root", "50459", "47175"],
  "background": "...",
  "isProxy": false
}
```

- `x`, `y`: Position on the tree canvas
- `orbits`: Array of orbit radii
- `nodes`: Node IDs belonging to this group

## Usage in Build Generation

When generating a build, the allocated passive nodes are simply a list of
node IDs. The planner loads `data.json` and interprets which nodes are
allocated based on user selections.
