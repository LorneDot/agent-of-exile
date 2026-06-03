# Hermes Agent Adapter

Agent of Exile integrates with Hermes Agent as a skill.

## Installation

```bash
git clone https://github.com/YOU/agent-of-exile.git \
  ~/.hermes/skills/gaming/agent-of-exile
cd ~/.hermes/skills/gaming/agent-of-exile/scripts
python fetch_tree.py --force
```

The skill auto-loads when the user triggers any of the When to Use patterns.

## Hermes-Specific Tools

### Loading references

Use `skill_view()` to load references on demand without cluttering context:

```
skill_view(name='agent-of-exile', file_path='references/verified-mechanics.md')
skill_view(name='agent-of-exile', file_path='references/sources.md')
skill_view(name='agent-of-exile', file_path='references/build-format.md')
```

### Persistent project memory

Use `memory()` to store session-crossing facts:

```
memory(action='add', target='memory',
       content='Agent of Exile: tree data cached. User account: Lorne.')
```

### Delegating heavy work

For tasks like scanning the full 5,102-node tree for path optimization,
use `delegate_task()` to offload to a subagent.

### Cron jobs

For periodic checks (e.g., "alert me if new PoE2 patch changes my build"):

```
cronjob(action='create', schedule='every 6h', name='poe2-patch-watch',
        prompt='Check pathofexile2.com for new patch notes. If found, summarize changes affecting Witch Infernalist builds.')
```

## Quick Start (Hermes)

After install, just ask:

- "theory craft a Fireball Infernalist build"
- "audit my level 78 Witch" (needs POESESSID env var)
- "make a melee Sorceress work somehow"

The skill loads, the agent looks up everything from poe2db.tw and data.json,
and outputs a build.txt file you can import into the PoE2 planner.
