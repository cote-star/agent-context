# Reference Pack: agent-chorus

This directory contains a complete, real-world agent context pack from the
[agent-chorus](https://github.com/cote-star/agent-chorus) repository -- a
155-file CLI project with dual Rust and Node.js implementations.

## What this pack covers

agent-chorus is a local-first CLI (`chorus`) for cross-agent session reading,
comparison, and handoff across Codex, Claude, Gemini, and Cursor. The codebase
has Rust source in `cli/src/`, Node scripts in `scripts/`, JSON schemas in
`schemas/`, golden test fixtures in `fixtures/golden/`, and conformance tests
that enforce byte-identical output between the two implementations.

## Pack tier

This is a **Tier 3** (full) pack containing the complete authority layer:

### Content layer (5 markdown files)
| File | Purpose |
|---|---|
| `00_START_HERE.md` | Entrypoint with mandatory read order, task-type routing, fast facts, stop rules |
| `10_SYSTEM_OVERVIEW.md` | Runtime architecture, command surface, silent failure modes |
| `20_CODE_MAP.md` | Navigation index, quick lookup shortcuts, cross-cutting tracing flows |
| `30_BEHAVIORAL_INVARIANTS.md` | 19 invariants, update checklists, file families, negative guidance |
| `40_OPERATIONS_AND_RELEASE.md` | Validation commands, CI checks, release flow, rollback |

### Authority layer (3 JSON files)
| File | Purpose |
|---|---|
| `routes.json` | Task-type router mapping intents to pack read order and completeness refs |
| `completeness_contract.json` | Per-task minimum sufficient evidence, contractually required files |
| `reporting_rules.json` | Stop rules, groupable families, verify budgets |

### Navigation layer (1 JSON file)
| File | Purpose |
|---|---|
| `search_scope.json` | Per-task search directories, exclusions, verification shortcuts |

### Manifest (1 JSON file)
| File | Purpose |
|---|---|
| `manifest.json` | Pack metadata: checksums, file list, schema version, provenance, family counts |

## Experiment results

When tested in the structured condition with this pack, Codex scored 6/6
correctness on agent-chorus -- the highest of any agent in any condition across
all experiments. Claude achieved zero dead ends and 69% token reduction compared
to bare condition.

See the full results at [docs/evidence/results.md](../../docs/evidence/results.md).

## Using this as a template

To create a similar pack for your own repo:

```bash
# Install the CLI
npm install -g agent-context

# Initialize a pack (choose tier 1, 2, or 3)
agent-context init --tier 3

# Have an agent fill in the template sections, then seal
agent-context seal
```

The markdown files in this reference pack are specific to agent-chorus. When
creating your own pack, replace the content with your repo's architecture, code
map, invariants, and operations. The JSON files follow the same schema regardless
of repo -- adapt the file paths, search directories, and contractually required
files to match your codebase.
