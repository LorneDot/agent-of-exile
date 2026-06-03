# PoE2 Verified Source Directory

When the agent needs information about PoE2 mechanics, gear, skills, or
crafting, it MUST consult these sources rather than relying on memory.
PoE1 knowledge is NOT valid for PoE2 without explicit GGG confirmation.

## Primary Verified Sources

### 1. GGG Skill Tree Data (Verified)
| What | URL | Format | How to access |
|------|-----|--------|---------------|
| PoE2 passive tree | `grindinggear/poe2-skilltree-export` | `data.json` | `fetch_tree.py` or raw GitHub |
| PoE2 atlas tree | `grindinggear/atlastree-export` | `data.json` | Raw GitHub |
| PoE1 tree (legacy) | `grindinggear/skilltree-export` | `data.json` | Raw GitHub |

These are the ONLY sources of truth for:
- Class base attributes
- Ascendancy names, IDs, and override pairs
- Node positions, connections, and group assignments
- Jewel socket positions
- Skill tree bounds and layout

### 2. GGG Official Documentation (Verified)
| What | URL | Notes |
|------|-----|-------|
| PoE2 official site | `https://pathofexile2.com` | News, league pages, announcements |
| PoE2 patch notes | Path of Exile 2 forum → Patch Notes | Mechanics changes, balance updates |
| PoE2 game guide | PoE2 website → Game Guide | Basic mechanics explanations |
| Developer manifestos | PoE forum → Development Manifestos | Design intent, formula explanations |
| GGG tracker | Community aggregators of GGG posts | Developer comments on Reddit/forum |

Use these for: current patch version, confirmed mechanics, league content,
developer statements about how systems work.

### 3. Game Data Mining (High Confidence)
| What | URL | Format | Notes |
|------|-----|--------|-------|
| PoE2DB | `https://poe2db.tw` | Web | Datamined items, mods, gems, uniques, passive tree stats |
| PoE2 item data | PoE2DB → Items | Web | Item bases, requirements, implicits |
| PoE2 gem data | PoE2DB → Gems | Web | Skill gems, support gems, spirit gems — tags, levels, requirements |
| PoE2 unique items | PoE2DB → Uniques | Web | All unique items with stats and sources |
| PoE2 mods | PoE2DB → Mods | Web | All modifiers, tiers, weights, slot restrictions |
| PoE2 crafting | PoE2DB → Crafting | Web | Bench crafts, essence mods, harvest options |
| PoE2 currencies | PoE2DB → Currencies | Web | All currency items, their effects, and mechanics |
| PoE2 essences | PoE2DB → Essences | Web | Essence tiers, guaranteed mod types |
| PoE2 omens | PoE2DB → Omens | Web | Meta-crafting items and their effects |
| PoE2 runes & soul cores | PoE2DB → Runes | Web | Socketable runes, soul cores, and their stats |

**poe2db.tw is the primary source for gear/crafting/mod data.** When designing
builds, use poe2db to look up what mods are available on each slot, what tier
ranges exist, and what unique items enable specific mechanics.

Note: poe2db is datamined from game files — not officially endorsed by GGG but
highly reliable as it reads actual game data.

### 4. Community Resources (Use with Caution)
| What | URL | Confidence | Notes |
|------|-----|------------|-------|
| Maxroll PoE2 Planner | `maxroll.gg/poe2/planner` | High (for format) | GGG build format reverse-engineered from JS |
| Maxroll Build Guides | `maxroll.gg/poe2/build-guides` | Medium | Community builds, may be outdated |
| PoE2 Wiki | `poe2wiki.net` | Medium | Community-maintained, variable quality |
| PoB2 (Community Fork) | GitHub | High (data) | Import/export format compatible with GGG planner |
| Reddit r/PathOfExile2 | `reddit.com/r/PathOfExile2` | Low-Medium | Player discussion, unverified claims |
| PoE2 Discord | Community servers | Low | Real-time discussion, unverified |

### 5. Build Planner Format (Verified — Reverse-Engineered)
| What | Source | Details |
|------|--------|---------|
| GGG build format | Maxroll planner JS | `deflate + base64` encoded XML |
| Build XML schema | `references/build-format.md` | Full element/attribute reference |
| Encode/decode | `scripts/build_codec.py` | Working implementation |

## How to Use Sources During Build Design

### When designing passives:
1. Run `fetch_tree.py` to get current `data.json`
2. Read the class entry for base attributes and ascendancy list
3. Navigate the `nodes` dict for potential path nodes
4. Use `groups` for cluster positions and orbit sizes

### When selecting gear mods:
1. Go to `poe2db.tw` → Mods
2. Filter by item slot (e.g., "Body Armour" prefix mods)
3. Identify the top mods by tier for your build's budget
4. Note which mods are prefixes vs suffixes for each slot
5. Cite poe2db as source: `[POE2DB]`

### When evaluating unique items:
1. Go to `poe2db.tw` → Uniques
2. Search for relevant keywords or item types
3. Verify unique stats and drop sources
4. Cite poe2db: `[POE2DB]`

### When looking up skill/support gems:
1. Go to `poe2db.tw` → Gems
2. Search by skill name or tag
3. Check: damage effectiveness, tags, attribute requirements, level scaling
4. Check support gem compatibility by tags
5. Cite poe2db: `[POE2DB]`

### When understanding crafting:
1. Go to `poe2db.tw` → Crafting
2. Check available bench crafts per slot
3. Check essence mod pools
4. Verify what omens exist and their effects
5. Cite poe2db: `[POE2DB]`

### When evaluating league mechanics:
1. Check PoE2 official patch notes for current league
2. Check poe2db for league-specific items/mods
3. Check PoE2 wiki for mechanic details
4. Mark league-specific claims with `[CURRENT-LEAGUE]` — they may change

## Source Citation Tags

| Tag        | Source                                          | Confidence |
|-----------|-------------------------------------------------|------------|
| `[TREE]`    | grindinggear/poe2-skilltree-export data.json   | Confirmed  |
| `[ATLAS]`   | grindinggear/atlastree-export data.json        | Confirmed  |
| `[GGG-PN]`  | Official patch notes from pathofexile2.com     | Confirmed  |
| `[GGG-DEV]` | Developer post, manifesto, or interview         | Confirmed  |
| `[POE2DB]`  | poe2db.tw — datamined from game files           | High       |
| `[COMM]`    | Community wiki, maxroll guides, PoB2 data       | Medium     |
| `[ESTIMATED]` | Agent's estimate, not source-verified         | Speculative |

**Golden rule:** Every mechanical claim must carry a citation tag. If you
can't find a source, mark it `[ESTIMATED]`. Never pass off PoE1 knowledge
or LLM training data as PoE2 fact.
