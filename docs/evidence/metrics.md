# Agent-Context — Key Metrics

A standalone summary of the experiment results. For the full 78+ graded result
breakdown, see [results.md](./results.md). For the interactive visualization,
visit the [agent-context dashboard](https://cote-star.github.io/agent-recall/docs/).

---

## Headline Numbers

Historical March/April 2026 aggregate:

| Metric | Bare | Structured |
|---|---|---|
| Correctness (3 repos avg) | 50% | **88%** |
| Token reduction (Claude, 3-repo avg: 38.6K → 13.1K) | -- | **~66%** |
| Dead ends (route-trusting family, 3 repos) | 2-3/repo | **0** |
| Production risk flags | 7 total | **0** |

Current Codex/Cursor meetup evidence:

| Agent | Metric | Bare | Structured |
|---|---|---:|---:|
| Codex | Tokens / 6-task cell | 163K | **130K** |
| Codex | Risk flags | 12 | **6** |
| Codex | Files opened / task | 7.7 | **7.1** |
| Cursor | Dead ends / task | 0.24 | **0.07** |
| Cursor | Files opened / task | 3.6 | **2.7** |
| Cursor | Risk flags | 14 | **10** |

Current focused Codex check from May 2, 2026:

| Metric | Bare | Structured |
|---|---:|---:|
| Reviewer grade, CLI/library rerun | 5 yes / 1 partial | 5 yes / 1 partial |
| Self-reported task-local files opened | 58 | **30** |
| Self-reported dead ends | **0** | 3 |
| Production-risk answers | **0** | **0** |

Current focused Cursor Agent check from May 2, 2026:

| Metric | Bare | Structured |
|---|---:|---:|
| Reviewer grade, CLI/library rerun | 3 yes / 3 partial | 3 yes / 3 partial |
| Self-reported task-local files opened | 35 | **18** |
| Self-reported dead ends | 1 | 1 |
| Production-risk answers | **0** | **0** |

Readout: the current Codex and Cursor reruns support the navigation-efficiency
claim, not a fresh correctness-lift claim. Cursor was run through authenticated
Cursor Agent CLI with `composer-2-fast`; Chorus did not expose Cursor CLI session
telemetry for these temp workspaces, so Cursor metrics are from the CLI final
answers.

## Repos Tested

| Repo Type | Files | Description |
|---|---|---|
| ML pipeline (`ml-pipeline-reference`) | 501 | Python ML training/inference pipeline |
| CLI library (`agent-chorus`) | 155 | Dual Rust/Node CLI with conformance-tested parity |
| React frontend (`react-frontend-reference`) | 1,982 | TypeScript React app with Zustand + React Query |

The same general-purpose template was used across all three repos with zero
modifications.

The May 2026 Codex check reused the CLI/library protocol only. It was a focused
freshness check, not a full replication of the 78+ result matrix.

For fresh Codex/Cursor reruns, use the private isolated bare vs
`structured_fresh` protocol. Runs where the structured pack fails `verify` or
the strict `.agent-context/tools/check_freshness.sh` gate should be discarded
from success metrics and treated as maintenance failures.

## Key Stories

### "Zero files, 12 seconds"
The route-trusting family answered a complex impact-analysis question (new client
parameter through the call chain) in 12 seconds with zero files opened. It
trusted the completeness contract completely and produced a correct,
comprehensive answer from context alone.

**Source**: ml-pipeline-reference, structured condition, M2 task.

### "Both miss setup.tsx"
Both agents in the bare condition missed `src/__tests__/setup.tsx` store reset
when adding a new Zustand store. This causes tests to pass individually but fail
in suite -- a silent, hard-to-debug failure. Both agents found it in the
structured condition because the behavioral invariants checklist explicitly
names it.

**Source**: react-frontend-reference, M1 task.

### "Deprecated pattern prevented"
The route-trusting family in the bare condition proposed using Apollo Client
(being deprecated) in its implementation plan. In the structured condition it
correctly used React Query because the behavioral invariants say "Do not assume
Apollo GraphQL queries are the current data path -- React Query is the primary
pattern."

**Source**: react-frontend-reference, H1 task.

---

## Interactive Dashboard

The full experiment visualization with per-repo breakdowns is available at:

**https://cote-star.github.io/agent-recall/docs/**

---

## Full Evidence Sources

- **Full result breakdown**: [results.md](./results.md) in this repo
- **Experiment data and figures**: [cote-star/agent-recall](https://github.com/cote-star/agent-recall) -- SVG/PNG figures, evidence map, interactive dashboard
- **Reference implementation and experiment protocol**: [cote-star/agent-chorus](https://github.com/cote-star/agent-chorus) -- `docs/agent-context-results.md`, research artifacts, and the `chorus agent-context` CLI that creates and maintains packs
