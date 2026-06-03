# OpenClaw Adapter

Agent of Exile works with OpenClaw as a project context. Load the SKILL.md
as your agent's system instructions, reference files are plain markdown.

## Installation

```bash
git clone https://github.com/YOU/agent-of-exile.git ~/workspace/agent-of-exile
cd ~/workspace/agent-of-exile/scripts
python fetch_tree.py --force
```

## OpenClaw-Specific Setup

### Option 1: Load as project context

In your OpenClaw workspace config, add:

```yaml
project_context:
  - path: ~/workspace/agent-of-exile/SKILL.md
    type: system_instruction
  - path: ~/workspace/agent-of-exile/references/sources.md
    type: reference
    load_on_demand: true
  - path: ~/workspace/agent-of-exile/references/verified-mechanics.md
    type: reference
    load_on_demand: true
```

SKILL.md always loads as system context. Reference files load on demand
when the agent accesses them.

### Option 2: Use via AGENTS.md

Copy the SKILL.md content into your project's `AGENTS.md` if you want
the theory-crafting instructions available alongside project-specific context:

```bash
cat ~/workspace/agent-of-exile/SKILL.md >> ~/your-project/AGENTS.md
```

### Option 3: Load via workspace memory

Save the skill path to OpenClaw workspace memory. OpenClaw agents can
read the SKILL.md with their native file tool when triggered:

```
# In a session, tell OpenClaw:
"Remember: Agent of Exile is at ~/workspace/agent-of-exile/.
 When I ask for PoE2 builds, read SKILL.md and follow the workflows."
```

## Loading References in OpenClaw

OpenClaw agents read files with their native tools:

```bash
# Read the source directory
cat ~/workspace/agent-of-exile/references/sources.md

# Read verified mechanics (only when you need formulas)
cat ~/workspace/agent-of-exile/references/verified-mechanics.md

# Read build format schema
cat ~/workspace/agent-of-exile/references/build-format.md
```

Don't load all references into context. Load `sources.md` once per session
to know where to look. Load `verified-mechanics.md` only when you need
specific formulas. Load `build-format.md` when generating output.

## Running Scripts

All scripts use Python 3.9+ stdlib only:

```bash
python ~/workspace/agent-of-exile/scripts/fetch_tree.py --force
python ~/workspace/agent-of-exile/scripts/generate_build.py spec.json -o build.txt
python ~/workspace/agent-of-exile/scripts/calc_stats.py spec.json --detail
```

## Character Audit in OpenClaw

Set the POESESSID environment variable or pass it directly:

```bash
export POESESSID=your_session_id
python ~/workspace/agent-of-exile/scripts/fetch_character.py --account Lorne --char MyWitch
```

## Workspace Memory Pattern

OpenClaw workspace memory is the equivalent of Hermes `memory()`. Store:

- Tree data cache status: "PoE2 tree data cached at ~/.cache/poe2-theory-crafter/"
- User account name for character audits
- Preferred risk profile defaults
- Build session history (for reference across sessions)

## Differences from Hermes

| Feature | Hermes | OpenClaw |
|---------|--------|----------|
| Skill loading | `skill_view()` auto-loads SKILL.md | Load SKILL.md via project context or AGENTS.md |
| Reference files | `skill_view(file_path=...)` | Native file read tools |
| Persistent memory | `memory(add=...)` | Workspace memory or notes |
| Delegation | `delegate_task()` | OpenClaw sub-processes or manual delegation |
| Cron jobs | `cronjob(create=...)` | External scheduler or cron |
