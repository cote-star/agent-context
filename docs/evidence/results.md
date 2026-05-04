# Agent-Context — Experiment Results

## TL;DR

Agent-context makes AI agents **dramatically better** at navigating large codebases. Across 3 repo types and 6 experiment runs:

- **Answer quality**: 50% to 88% correct (bare to structured)
- **Efficiency**: 58-74% fewer tokens, zero dead ends
- **Risk elimination**: agent-context prevented every "would break production" answer
- **Template is general-purpose**: ML pipeline, CLI library, React frontend -- zero modifications

These headline numbers are historical March/April 2026 results. The current
path for any new Codex or Cursor claim is a private fresh-pack rerun protocol:
every structured condition must pass `agent-context verify` and the strict
`.agent-context/tools/check_freshness.sh` gate before the agent runs. The May 2
2026 one-shot below predates that protocol and is recategorized as a stale-pack
maintenance failure, not a current product result.

---

## The Problem

Large codebases (500-2,000+ files) cause AI agents to:
- **Explore inefficiently** -- opening irrelevant files, burning tokens
- **Miss critical files** -- incomplete impact analysis, silent production failures
- **Use deprecated patterns** -- proposing Apollo when React Query is the standard
- **Fail silently** -- missing test setup resets that cause flaky suites

## The Solution

A three-layer `.agent-context` directory committed to the repo:

| Layer | Files | Serves |
|---|---|---|
| **Content** | 5 markdown files (architecture, code map, invariants, operations) | Humans + all agents |
| **Authority** | 3 JSON files (routes, completeness contracts, reporting rules) | Trust-and-follow agents (Claude) |
| **Navigation** | 1 JSON file (search scopes, verification shortcuts) | Search-and-verify agents (Codex) |

Plus minimal routing blocks in `CLAUDE.md` / `AGENTS.md` (~100-200 tokens each).

---

## Results Across 3 Repo Types

### Correctness (yes rate)

| Repo | Files | Claude bare | Claude structured | Codex bare | Codex structured |
|------|-------|------------|-------------------|------------|------------------|
| ml-pipeline-reference (ML pipeline) | 501 | 3/6 (50%) | 5/6 (83%) | 3/6 (50%) | 5/6 (83%) |
| agent-chorus (CLI/library) | 155 | 5/6 (83%) | 5/6 (83%) | -- | 6/6 (100%) |
| react-frontend-reference (React/TS) | 1,982 | 2/4 (50%) | 4/4 (100%) | 2/4 (50%) | 3/4 (75%) |

### Efficiency (Claude only -- most dramatic improvement)

| Repo | Bare avg files | Structured avg files | Reduction | Bare avg tokens | Structured avg tokens | Token reduction |
|------|---------------|---------------------|-----------|----------------|----------------------|----------------|
| ml-pipeline-reference | 7.5 | 2.2 | **71%** | 49K | 12.5K | **74%** |
| agent-chorus | 1.5 | 0.83 | **45%** | 13.5K | 4.25K | **69%** |
| react-frontend-reference | 10.0 | 2.75 | **73%** | 53K | 22.5K | **58%** |

### Dead Ends (wasted file reads)

| Repo | Claude bare | Claude structured | Codex bare | Codex structured |
|------|------------|-------------------|------------|------------------|
| ml-pipeline-reference | 2 | **0** | 7 | 11 |
| agent-chorus | 0 | **0** | 1 | 1 |
| react-frontend-reference | 3 | **0** | 6 | 2 |

Claude structured: **zero dead ends across all 3 repos.**

### Risk Flags (answers that would break production)

| Repo | Bare total | Structured total |
|------|-----------|-----------------|
| ml-pipeline-reference | 3 | 0 |
| agent-chorus | 0 | 0 |
| react-frontend-reference | 4 | 0* |

\* Structured risk flags were protocol breaches (grep matched ground truth), not production risks.

**Agent-context eliminated every production-risk answer.**

---

## May 2026 Stale-Pack Rerun (preliminary; superseded)

> **Recategorized as a maintenance failure, not a product result.** The
> structured condition in this rerun used a pack that had drifted from the
> repo since the original experiments. `agent-context freshness` was not
> required to pass before the agent started, and the structured run hit
> stale-pack dead ends. The protocol fix is a private isolated fresh-pack rerun:
> every structured run begins with `verify` and strict freshness passing on a
> freshly filled pack, on an isolated repo copy. Numbers below are kept for
> research-history continuity; do not cite them as current Codex or Cursor
> claims.

Why this rerun exists: the Codex-specific claims above were based on experiments
from roughly four weeks earlier, which is old enough to matter in agent behavior.
We reran the canonical CLI/library behavior protocol with current local tools:

| Tool | Version / status |
|---|---|
| Codex CLI | `codex-cli 0.128.0` |
| Cursor Agent | `cursor 3.2.11`, `composer-2-fast`, authenticated and run headlessly after setup |

Scope: one play-side CLI/library repo, bare vs structured condition, six tasks
(`L1`, `L2`, `M1`, `M2`, `H1`, `H2`). Work repos were not used. Raw transcripts
were kept temporary; only scrubbed aggregate results are reported here.

### Codex Result

| Metric | Bare | Structured | Readout |
|---|---:|---:|---|
| Reviewer grade | 5 yes / 1 partial | 5 yes / 1 partial | No correctness lift in this focused rerun |
| Self-reported task-local files opened | 58 | 30 | 48% fewer files with structured context |
| Self-reported dead ends | 0 | 3 | Structured run hit stale/scope mismatches |
| Session duration | ~4 min | ~4 min | Roughly tied |
| Production-risk answers | 0 | 0 | No production-risk answer in either condition |

### Cursor Agent Result

| Metric | Bare | Structured | Readout |
|---|---:|---:|---|
| Reviewer grade | 3 yes / 3 partial | 3 yes / 3 partial | No correctness lift in this focused rerun |
| Self-reported task-local files opened | 35 | 18 | 49% fewer files with structured context |
| Self-reported dead ends | 1 | 1 | Tied |
| Production-risk answers | 0 | 0 | No production-risk answer in either condition |

Cursor evidence caveat: Cursor Agent CLI completed the headless runs, but its
sessions were not visible to `chorus read/list` for these temporary workspaces.
The table uses the CLI final answers and self-reported task-local metrics, not
Chorus-extracted tool telemetry.

Interpretation:

- The current Codex claim should be narrowed: agent-context still acts as useful
  scaffolding for Codex and reduced the number of task-local files it opened.
- The current rerun does not support saying Codex correctness improves
  automatically from the pack. In this run both conditions graded the same.
- Cursor showed the same broad shape: structured context reduced file opens, but
  did not improve grade in this focused rerun.
- The structured runs followed the pack first, then verified against source.
  That still supports the "search-and-verify" characterization for Codex and is
  consistent with Cursor in this run.
- Freshness matters. The structured run found a stale pack mismatch around the
  current modular adapter architecture; that mismatch caused extra dead ends and
  should be treated as evidence for stricter freshness checks, not as a reason to
  trust stale packs.
- Do not present Cursor as fully proven equivalent to Codex from this evidence:
  the run is one repo, one model, and lacks Chorus-extracted Cursor telemetry.

---

## Best Stories

### "Zero files, 12 seconds" (ml-pipeline-reference, Claude structured, M2)
Claude answered a complex impact analysis question (new client parameter through the call chain) in 12 seconds with zero files opened. It trusted the completeness contract completely and produced a correct, comprehensive answer from context alone.

### "Both agents miss the same silent failure" (react-frontend-reference, M1)
Both Claude and Codex in bare condition missed `src/__tests__/setup.tsx` store reset when adding a new Zustand store. This causes tests to pass individually but fail in suite -- a silent, hard-to-debug failure. Both agents found it in structured because the behavioral invariants checklist explicitly names it.

### "Negative guidance prevents deprecated pattern" (react-frontend-reference, H1)
Claude bare proposed using Apollo Client (being deprecated) in its implementation plan. Claude structured correctly used React Query because the behavioral invariants say "Do not assume Apollo GraphQL queries are the current data path -- React Query is the primary pattern."

### "Codex achieves 6/6" (agent-chorus, Run 5)
Codex structured scored 6/6 yes on agent-chorus — the highest correctness of any
agent in any condition across these experiments. The completeness contracts gave
Codex the information it needed to be thorough without over-exploring. Any
current Codex/Cursor claim should come from a fresh-pack rerun under the
private isolated protocol, not from this historical anecdote alone.

---

## Two Agent Architectures

The experiments revealed that agents fall into two categories:

### Trust-and-follow (Claude, likely Gemini)
- Reads the agent-context as authoritative
- Opens minimal repo files (2.75 avg in frontend)
- Zero dead ends consistently
- Benefits from: completeness contracts, stop rules, grouped reporting

### Search-and-verify (Codex, Cursor)
- Uses the agent-context as scaffolding, then verifies against code
- Still opens many files (10.25 avg in frontend)
- Benefits from: search scope boundaries and completeness cues
- Does NOT benefit from: stop rules (ignores them)

**The three-layer architecture serves both**: authority layer for Claude, navigation layer for Codex, content layer for both.

---

## Experiment Program Summary

| Phase | What | Status |
|---|---|---|
| 1-3 | Foundation + learning runs | Done |
| 4 | Template improvements (v0.8.3) | Done |
| 5 | Apply to ml-pipeline-reference | Done |
| 6 | Validation run -- all 5 SC passed | Done |
| 6b | Structured JSON layer experiment | Done |
| 7 | Integration + release (v0.9.0) | Done |
| 8 | Generalization -- CLI/library (Run 5) | Done |
| 8b | agent-context creation skill | Done |
| 8c | Frontend validation (Run 6) | Done |
| 9 | Showcase | Done (this document) |
| 10 | Documentation + guide | Done |

6 experiment runs, 78+ graded results, 15 design principles, 3 repo types, 1 general-purpose template.

---

## Full Evidence

- **Key metrics summary**: [metrics.md](./metrics.md)
- **Figures**: [figures/](./figures/) -- SVG+PNG pairs for asymmetry contrast, three-track importance, and experiment results
- **Interactive dashboard**: https://cote-star.github.io/agent-recall/docs/
- **Source repos**: [cote-star/agent-recall](https://github.com/cote-star/agent-recall) (figures, evidence map), [cote-star/agent-chorus](https://github.com/cote-star/agent-chorus) (experiment protocol, reference implementation)
