# Reference Pack: agent-chorus

> **Historical snapshot.** This is a faithful capture of an `agent-chorus` v0.14.1
> pack, preserved as-is to show what a complex filled tier-3 pack looks like in a
> real Rust + Node.js monorepo. The inner files reference that source repo's
> bundled `chorus agent-context` CLI (including the older `seal` verb); the
> current public `agent-context` CLI replaces that step with `verify` + `freshness`.
> Do not copy commands out of this directory — see [`docs/getting-started.md`](../../docs/getting-started.md)
> for current setup.

This directory contains a complete, real-world agent-context artifact set from the
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

## Using this as a structural reference

This pack is for reading, not copying. The shape — five markdown files, three
authority JSON files, one navigation JSON, one manifest — is what a richer
tier-3 pack looks like. The content is specific to agent-chorus and will not
fit another repo verbatim.

For setup on your own repo, follow [`docs/getting-started.md`](../../docs/getting-started.md).
That is the canonical install and authoring flow; this directory does not
duplicate it.
