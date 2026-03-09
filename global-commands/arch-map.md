# /arch-map — Generate Architecture & Dependency Map

Generate a living architecture map for the current project. Produces `.claude/ARCHITECTURE.md` with:

- **"If X changes, update Y"** blast-radius table — instant lookup for any change's downstream impact
- **Mermaid dependency diagram** — full network graph of data files, modules, scripts, and UI layers
- **Critical workflow paths** — step-by-step sequences for the most common operations
- **Data file lineage** — who produces and consumes each file, when to rebuild
- **Duplication warnings** — config or logic defined in multiple places that must stay in sync

## Usage

```
/arch-map              # Generate full map for current project
/arch-map --update     # Regenerate only changed sections
```

## Implementation

Invoke the `arch-map` skill. Follow its full workflow:

1. Check for existing `.claude/ARCHITECTURE.md` and its freshness
2. Discover project structure (layers, entry points, data files)
3. Spawn Explore subagent to map all file I/O and imports
4. Identify critical nodes, output nodes, and duplications
5. Write `.claude/ARCHITECTURE.md` with all sections
6. Update MEMORY.md / CLAUDE.md to reference the map
7. Deliver summary of findings

## Output Location

Always writes to: `.claude/ARCHITECTURE.md` in the current project root.

## When Future Sessions Use This

At the start of any session, reading `.claude/ARCHITECTURE.md` gives instant topology understanding:
- No need to explore the codebase from scratch
- Immediately know what to update when making changes
- Understand data flow and layer boundaries
- Spot tech debt (duplication warnings)

## Regeneration

Run `/arch-map` again after:
- Adding new scripts or modules
- Changing data file schemas
- Major refactors
- New integrations or dependencies

The map is always regenerated from scratch (not manually edited) to prevent drift.
