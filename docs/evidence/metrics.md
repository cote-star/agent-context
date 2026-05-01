# Agent Context Pack — Key Metrics

A standalone summary of the experiment results. For the full 78+ graded result
breakdown, see [results.md](./results.md). For the interactive visualization,
visit the [context-pack dashboard](https://cote-star.github.io/agent-recall/docs/).

---

## Headline Numbers

| Metric | Bare | Structured |
|---|---|---|
| Correctness (3 repos avg) | 50% | **88%** |
| Token reduction (route-trusting family) | -- | **58-74%** |
| Dead ends (route-trusting family, 3 repos) | 2-3/repo | **0** |
| Production risk flags | 7 total | **0** |

## Repos Tested

| Repo Type | Files | Description |
|---|---|---|
| ML pipeline (`stream-models`) | 501 | Python ML training/inference pipeline |
| CLI library (`agent-chorus`) | 155 | Dual Rust/Node CLI with conformance-tested parity |
| React frontend (`trust-stream-frontend`) | 1,982 | TypeScript React app with Zustand + React Query |

The same general-purpose template was used across all three repos with zero
modifications.

## Key Stories

### "Zero files, 12 seconds"
The route-trusting family answered a complex impact-analysis question (new client
parameter through the call chain) in 12 seconds with zero files opened. It
trusted the completeness contract completely and produced a correct,
comprehensive answer from context alone.

**Source**: stream-models, structured condition, M2 task.

### "Both miss setup.tsx"
Both agents in the bare condition missed `src/__tests__/setup.tsx` store reset
when adding a new Zustand store. This causes tests to pass individually but fail
in suite -- a silent, hard-to-debug failure. Both agents found it in the
structured condition because the behavioral invariants checklist explicitly
names it.

**Source**: trust-stream-frontend, M1 task.

### "Deprecated pattern prevented"
The route-trusting family in the bare condition proposed using Apollo Client
(being deprecated) in its implementation plan. In the structured condition it
correctly used React Query because the behavioral invariants say "Do not assume
Apollo GraphQL queries are the current data path -- React Query is the primary
pattern."

**Source**: trust-stream-frontend, H1 task.

---

## Interactive Dashboard

The full experiment visualization with per-repo breakdowns is available at:

**https://cote-star.github.io/agent-recall/docs/**

---

## Full Evidence Sources

- **Full result breakdown**: [results.md](./results.md) in this repo
- **Experiment data and figures**: [cote-star/agent-recall](https://github.com/cote-star/agent-recall) -- SVG/PNG figures, evidence map, interactive dashboard
- **Reference implementation and experiment protocol**: [cote-star/agent-chorus](https://github.com/cote-star/agent-chorus) -- `docs/agent-context-results.md`, research artifacts, and the `chorus agent-context` CLI that creates and maintains packs
