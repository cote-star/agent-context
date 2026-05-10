# Agent-Context — Experiment Results

## TL;DR

Agent-context makes AI agents **dramatically better** at navigating large
codebases. Q2 2026 multi-agent rerun (current evidence): 252 graded tasks
across 48 cells (6 repos × 4 model variants × 2 conditions × 6 tasks).

- **Claude Opus 4.7 + structured = 6/6 perfect** across all 6 repos.
  Bare scored 80%; structured tied 100%. Largest correctness lift in the
  rerun.
- **Cursor `composer-2-fast` (the default) gains the most**: 61% → 81%
  yes-rate moving bare → structured. Structured matters most for
  trust-and-follow weaker-model lanes.
- **Cursor Opus medium with structured context cuts duration 65%**
  (median 219s → 78s per task). The search-and-verify pattern collapses
  to direct reads when the pack guides navigation.
- **Production-risk drops to zero** for codex and cursor opus medium with
  structured context. Composer-2-fast remains the riskiest lane in both
  conditions.
- Same general-purpose template, **zero modifications** across 6 real
  repos: CLI library, ML pipeline, React frontend, FastAPI service,
  polyglot monorepo, Swift macOS daemon.

Grading is LLM-provisional via independent Claude Code subagents (one per
cell, fresh context, no human spot-audit). See
[Methodology](metrics.md#methodology-and-disclosure) in metrics.md for the
full disclosure on grading, anomalies, and telemetry caveats.

The historical March/April 2026 3-repo run set (78 reviewer-confirmed
graded answers) is preserved in [§Historical](#historical-marchapril-2026-3-repo-run-set)
below.

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

## Q2 2026 Multi-Agent Rerun (current evidence)

**Scope.** 6 repos × 4 model variants × bare/structured × 6 tasks =
**252 graded answers across 48 cells.** Run May 9–10, 2026 under the
fresh-pack isolated protocol: every `structured_fresh` clone passed
`agent-context verify` + strict `check_freshness.sh` before the agent
started. All 252 task verdicts carry `grading_method: llm-provisional`
— LLM-judged via independent Claude Code subagents (one subagent per
cell, fresh context). No human spot-audit.

### Correctness (yes-rate, mean across 6 repos)

| Agent / Model | Bare | Structured | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

Claude Opus structured: **perfect 6/6 across all 6 repos.** Cursor
composer shows the largest absolute lift; Cursor Opus medium and Codex
are already strong on bare and tighten further.

### Production-risk reduction (risk flags / 6 tasks)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Codex CLI | 0.33 | **0.00** |
| Cursor `claude-opus-4-7-medium` | 0.50 | **0.00** |
| Claude Opus 4.7 | 0.20 | 0.17 |
| Cursor `composer-2-fast` | 0.67 | 0.50 |

Structured context **eliminates risk flags entirely** for codex and
cursor opus medium. Composer remains risky in both conditions —
trust-and-follow weaker-model behavior under bare and partial under
structured.

### Median duration per task (sec, mean across 6 repos)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Cursor `claude-opus-4-7-medium` | 219 | **78** (−65%) |
| Cursor `composer-2-fast` | 111 | 112 |
| Claude Opus 4.7 | 65 | 56 |
| Codex CLI | 55 | 126 |

Cursor Opus medium with structured context cuts duration 65% — the
search-and-verify pattern collapses to direct reads when the pack
guides navigation. Codex's structured runs are *slower* than bare in
this rerun: structured codex spends more wall-clock per task on
careful verification, even when the correctness lift is small.

### Tool-call efficiency (calls per correct answer)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Claude Opus 4.7 | 14.2 | **8.8** |
| Codex CLI | 11.4 | **9.2** |
| Cursor `claude-opus-4-7-medium` | 8.3 | **7.9** |
| Cursor `composer-2-fast` | 5.6 | **4.6** |

Every lane gets cheaper per correct answer with the pack. Claude Opus
shows the strongest reduction (38%).

### Anomalies preserved

Per the disclosure principle, anomalies are surfaced rather than
masked or retried-to-100%:

1. *Cursor composer / structured / polyglot-monorepo-reference*:
   transient provider error; recovered on first retry.
2. *Cursor opus medium / bare / daemon-reference*: first attempt
   emitted a final summary claiming result JSONs were written but no
   files actually landed (tool-call hallucination); recovered on
   first retry.
3. *Claude / bare / agent-chorus*: ran on
   `claude-haiku-4-5-20251001` rather than `claude-opus-4-7` due to
   Claude Code's 5h-session automatic fallback. Reported separately
   under the haiku model_id (5/6 yes on that cell).
4. *`org-second-brain` repo skipped*: interactive claude session
   looped without writing results — pack/EXPERIMENT setup needs
   review. Codex and Cursor cells did complete (6/6 each) but are
   considered untrustworthy until the underlying issue is fixed.
   Working slate is **6 repos**.

See [metrics.md §Methodology and Disclosure](./metrics.md#methodology-and-disclosure)
for the full grading + telemetry disclosure.

---

## Historical (March/April 2026, 3-repo run set)

Pre-Q2-2026 evidence kept for comparison. The 78-graded run set is the
basis for several earlier public claims; the Q2 2026 rerun above
supersedes those claims with a 4-agent, 6-repo, fresh-pack matrix and
LLM-provisional grading. Numbers below were reviewer-confirmed.

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

### Risk Flags (historical)

| Repo | Bare total | Structured total |
|------|-----------|-----------------|
| ml-pipeline-reference | 3 | 0 |
| agent-chorus | 0 | 0 |
| react-frontend-reference | 4 | 0* |

\* Structured risk flags were protocol breaches (grep matched ground truth), not production risks.

The May 2 2026 one-shot Codex/Cursor stale-pack check that previously
appeared here is **superseded by the Q2 2026 rerun above** and removed
from the headline. The earlier numbers are preserved in the rerun infra
for research-history continuity.

---

## Best Stories

### "Zero files, 12 seconds" (ml-pipeline-reference, Claude structured, M2)
Claude answered a complex impact analysis question (new client parameter through the call chain) in 12 seconds with zero files opened. It trusted the completeness contract completely and produced a correct, comprehensive answer from context alone.

### "Both agents miss the same silent failure" (react-frontend-reference, M1)
Both Claude and Codex in bare condition missed `src/__tests__/setup.tsx` store reset when adding a new Zustand store. This causes tests to pass individually but fail in suite -- a silent, hard-to-debug failure. Both agents found it in structured because the behavioral invariants checklist explicitly names it.

### "Negative guidance prevents deprecated pattern" (react-frontend-reference, H1)
Claude bare proposed using Apollo Client (being deprecated) in its implementation plan. Claude structured correctly used React Query because the behavioral invariants say "Do not assume Apollo GraphQL queries are the current data path -- React Query is the primary pattern."

### "Claude Opus structured: perfect 6/6 across 6 repos" (Q2 2026 rerun)
Claude Opus 4.7 with the structured pack scored **yes on every one of 36
graded tasks across all 6 repos** in the Q2 2026 rerun. Bare Claude Opus
on the same matrix scored 80% (24/30 across 5 repos; the agent-chorus bare
cell ran on Haiku). The +20pp lift is the strongest correctness improvement
of any agent in the rerun.

### "Cursor Opus medium 219s → 78s" (Q2 2026 rerun)
Cursor Agent with `claude-opus-4-7-medium` takes 219 seconds median per
task in bare condition (heavy `glob` + `grep` + verify pattern) versus
78 seconds with structured context — a 65% duration cut. The search-and-
verify pattern collapses to direct reads when the pack provides the
navigation target. Search-vs-read ratio drops from 0.89 → 0.57 across
the same lane.

### "Composer biggest correctness lift: 61% → 81%" (Q2 2026 rerun)
Cursor's default `composer-2-fast` model gains 20 percentage points of
yes-rate moving bare → structured (3.67/6 → 4.83/6). Structured context
matters most for the trust-and-follow weaker-model lane.

### "Codex achieves 6/6" (agent-chorus, Run 5, historical)
Codex structured scored 6/6 yes on agent-chorus in the March/April 2026
historical run — the highest correctness in that earlier matrix. The
Q2 2026 rerun confirms the broad shape: codex structured outperforms
bare on every repo, though the cross-repo average tightens to 78%
because structured codex on harder repos (large polyglot monorepo,
TypeScript frontend) trades correctness for thoroughness rather than
hitting 100%.

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
