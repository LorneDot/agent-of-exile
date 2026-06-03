# PoE2 Theory Crafter

A Hermes Agent skill that theory-crafts Path of Exile 2 builds and outputs
them as GGG-compatible build planner files.

## What it does

- Designs complete PoE2 builds: passive trees, skill gems, gear, ascendancy
- Outputs build files in the official GGG build planner format
- Uses real skill tree data from GGG's published JSON export
- Works as a skill inside Hermes Agent (or any OpenClaw-compatible agent)

## Quick Install

```bash
# Clone into your Hermes skills directory
git clone https://github.com/YOU/poe2-theory-crafter.git \
  ~/.hermes/skills/poe2-theory-crafter

# Fetch the latest PoE2 skill tree data
cd ~/.hermes/skills/poe2-theory-crafter/scripts
python fetch_tree.py --force
```

## Usage

Once installed as a Hermes skill, just ask:

> "Theory craft a PoE2 Lightning Arrow Deadeye build for mapping"

The agent will:
1. Load the skill tree data
2. Design passives, skills, and gear
3. Generate a `build.txt` file you can import into the PoE2 planner

### Standalone Scripts

You can also use the scripts directly:

```bash
# Generate a build from a JSON spec
python scripts/generate_build.py examples/example_build.json -o build.txt

# See the raw XML before encoding
python scripts/generate_build.py examples/example_build.json --xml

# Decode an existing build string
python scripts/build_codec.py decode build.txt
```

## Project Structure

```
poe2-theory-crafter/
├── SKILL.md              # Hermes Agent skill definition
├── README.md             # This file
├── scripts/
│   ├── build_codec.py    # Encode/decode GGG build format
│   ├── fetch_tree.py     # Fetch & cache skill tree data
│   └── generate_build.py # Generate build files from specs
├── references/
│   ├── build-format.md   # GGG build format documentation
│   └── skill-tree-format.md  # Skill tree JSON schema docs
└── examples/
    └── example_build.json    # Sample build spec
```

## Build Format

GGG's build planner uses a compressed XML format:

```
XML → Deflate (zlib) → Base64 (URL-safe) → Build String
```

See `references/build-format.md` for the full schema.

## Skill Tree Data

GGG publishes the PoE2 passive tree as JSON at:
[grindinggear/poe2-skilltree-export](https://github.com/grindinggear/poe2-skilltree-export)

The `fetch_tree.py` script downloads and caches this data.

## Requirements

- Python 3.9+
- No external dependencies (stdlib only)

## License

MIT
