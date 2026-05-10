# Agent-Context — Key Metrics

A standalone summary of the experiment results. For the full per-cell
breakdown, see [results.md](./results.md). For the interactive visualization,
visit the [agent-context dashboard](https://cote-star.github.io/agent-recall/docs/).

---

## Headline — Q2 2026 multi-agent rerun (current evidence)

**252 graded tasks** across **48 cells**: 6 repos × 4 model variants ×
2 conditions × 6 tasks. Grading is LLM-provisional via independent
Claude Code subagents (one subagent per cell, fresh context, no human
spot-audit). See [methodology disclosure](#methodology-and-disclosure)
below.

### Correctness (yes-rate, mean across 6 repos)

| Agent / Model | Bare | Structured | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

Claude Opus structured is perfect 6/6 across all 6 repos. Cursor
composer-2-fast shows the largest absolute lift (61% → 81%). Both
Codex and Cursor Opus medium are already strong on bare; structured
context narrows the remaining gap.

### Production-risk reduction (risk flags / 6 tasks, mean across 6 repos)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Codex CLI | 0.33 | **0.00** |
| Cursor `claude-opus-4-7-medium` | 0.50 | **0.00** |
| Claude Opus 4.7 | 0.20 | 0.17 |
| Cursor `composer-2-fast` | 0.67 | 0.50 |

Structured context eliminates risk flags entirely for Codex and Cursor
Opus medium. Composer-2-fast remains the riskiest lane in both
conditions, consistent with its trust-and-follow profile relying on
the bare context.

### Median duration per task (seconds, mean across 6 repos)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Cursor `claude-opus-4-7-medium` | 219 | **78** (−65%) |
| Cursor `composer-2-fast` | 111 | 112 |
| Claude Opus 4.7 | 65 | 56 |
| Codex CLI | 55 | 126 |

Cursor Opus medium under structured context cuts duration 65% — the
search-and-verify pattern (many `glob` / `grep` calls before reads)
collapses to direct reads when the pack tells the agent where to
look. Codex's structured runs are slower than bare in this rerun;
structured codex spends more wall-clock per task on careful
verification, even when correctness lift is small.

### Tool-call efficiency (calls per correct answer)

| Agent / Model | Bare | Structured |
|---|---:|---:|
| Claude Opus 4.7 | 14.2 | **8.8** |
| Codex CLI | 11.4 | **9.2** |
| Cursor `claude-opus-4-7-medium` | 8.3 | **7.9** |
| Cursor `composer-2-fast` | 5.6 | **4.6** |

Every lane gets cheaper per correct answer with the pack — strongest
for Claude Opus (38% reduction).

---

## Historical reference (March/April 2026, 3-repo run set)

Pre-Q2-2026 evidence kept for comparison. The 78-graded run set is the
basis for several earlier public claims; the Q2 2026 rerun above
supersedes those claims with a 4-agent, 6-repo, fresh-pack matrix.

| Metric | Bare | Structured |
|---|---:|---:|
| Correctness (3 repos avg) | 50% | **88%** |
| Token reduction (Claude, 3-repo avg: 38.6K → 13.1K) | -- | **~66%** |
| Dead ends (route-trusting family, 3 repos) | 2-3/repo | **0** |
| Production risk flags | 7 total | **0** |

The May 2 2026 stale-pack one-shot Codex/Cursor check that previously
appeared here is superseded by the Q2 2026 rerun and removed from the
headline numbers. The run is preserved in the rerun infra and
[results.md §Historical](./results.md) for research-history continuity.

---

## Methodology and disclosure

**Grading method.** All 252 task verdicts in the Q2 2026 rerun carry
`grading_method: llm-provisional`. Each cell (6 tasks) was graded by an
independent Claude Code subagent with fresh context — the subagent
read the cell's results, the per-task ground truth, and a fixed judge
system prompt, then emitted `correct ∈ {yes, partial, no}` plus a
`risk_flag` boolean and a 2-3 sentence rationale per task. There was
**no human spot-audit on top of the LLM-provisional grades.** The
historical 3-repo run set used reviewer-confirmed grading; numbers are
not directly comparable on grading rigor.

**Per-cell results were captured fresh** (not derived from prior
sessions). Each cell is one fresh agent-CLI process per condition per
repo, six tasks in one session, started after `agent-context verify` +
strict freshness on the `structured_fresh` clone. The pack content
itself was authored at v0.2.0 and validated by v0.3.1 for this rerun
(see `pack_content_origin_version` and `validator_cli_version` on each
result row).

**Anomalies.** Three operational anomalies were preserved (not
masked):

1. *Cursor `composer-2-fast` / structured / `polyglot-monorepo-reference`*:
   transient provider error; recovered on first retry.
2. *Cursor `claude-opus-4-7-medium` / bare / `daemon-reference`*: first
   attempt emitted a final summary claiming result JSONs were written,
   but no files actually landed (tool-call hallucination); recovered
   on first retry.
3. *Claude / `bare` / `agent-chorus`*: ran on `claude-haiku-4-5-20251001`
   rather than `claude-opus-4-7` due to Claude Code's 5h-session
   automatic fallback. The cell is reported separately under the
   haiku model_id in per-cell tables.
4. *`org-second-brain` repo*: skipped from the matrix (interactive
   claude session looped without writing results — pack/EXPERIMENT
   setup needs review). Codex and Cursor cells did complete but are
   considered untrustworthy until the underlying issue is fixed.
   Working slate is 6 repos.

**Telemetry caveats.**

- Cursor lanes do not expose ordered tool-call event streams via
  `cursor-agent --print` (they exist in a SQLite store under
  `~/.cursor/chats/` but require reverse-engineering). Cursor cells
  use the agent's self-reported aggregate `tool_calls`, citations,
  duration, files-opened, dead-ends, and post-hit dead-ends —
  sufficient for the headline metrics, but token / cost figures are
  null for cursor in this rerun.
- Codex's `model` field is null in `session_meta` (codex CLI doesn't
  always populate it). All codex cells are normalized to
  `model_id: codex-cli-0.130.0`. The underlying OpenAI model the
  codex CLI routed to is recorded in the codex banner output but not
  in this aggregated table.
- Search-vs-read ratios are only directly comparable within an agent.
  Claude / Codex use distinct tool taxonomies (Claude has `Grep` /
  `Glob` as top-level tools; Codex routes searches through
  `exec_command` shell calls).

---

## Repos Tested

| Repo Type | Files | Description |
|---|---|---|
| CLI library (`agent-chorus`) | 155 | Dual Rust/Node CLI with conformance-tested parity |
| ML pipeline (`ml-pipeline-reference`) | 501 | Python ML training/inference pipeline |
| React frontend (`react-frontend-reference`) | 1,982 | TypeScript React app with Zustand + React Query |
| Backend service (`backend-service-reference`) | varies | FastAPI Python service |
| Polyglot monorepo (`polyglot-monorepo-reference`) | varies | Mixed-language monorepo |
| macOS daemon (`daemon-reference`) | varies | Swift daemon process broker |

The same general-purpose template was used across all 6 repos with zero
modifications. Pack content was authored at v0.2.0; runs validated under
v0.3.1.

The seventh repo (`org-second-brain`, a markdown knowledge-base corpus)
is skipped pending pack/EXPERIMENT setup review.

---

## Key Stories

### "Claude Opus structured: perfect 6/6 across 6 repos"
Claude Opus 4.7 with structured pack scored yes on every one of 36 graded
tasks across all 6 repos in the Q2 2026 rerun. Bare Claude Opus scored
80% on the same matrix (24/30, excluding the haiku-fallback agent-chorus
cell). The +20pp lift is the strongest correctness improvement of any
agent in the rerun.

**Source**: Q2 2026 rerun, claude/`claude-opus-4-7`/structured_fresh.

### "Cursor Opus medium: 219s → 78s"
Cursor Agent with `claude-opus-4-7-medium` model takes 219 seconds median
per task in bare condition (heavy `glob` / `grep` / verify pattern)
versus 78 seconds with structured context — a 65% duration cut. The
search-and-verify pattern collapses to direct reads when the pack
provides the navigation target.

**Source**: Q2 2026 rerun, cursor/`claude-opus-4-7-medium`,
search_vs_read_ratio bare=0.89 → structured=0.57.

### "Composer biggest correctness lift: 61% → 81%"
Cursor's default `composer-2-fast` model gains 20 percentage points of
yes-rate moving bare → structured (3.67/6 → 4.83/6). Structured context
matters most for the trust-and-follow weaker-model lane.

**Source**: Q2 2026 rerun, cursor/`composer-2-fast`.

### "Zero files, 12 seconds" (historical)
The route-trusting family answered a complex impact-analysis question
(new client parameter through the call chain) in 12 seconds with zero
files opened. It trusted the completeness contract completely and
produced a correct, comprehensive answer from context alone.

**Source**: ml-pipeline-reference, structured condition, M2 task,
March/April 2026 historical run.

### "Both miss setup.tsx" (historical)
Both Claude and Codex in the bare condition missed `src/__tests__/setup.tsx`
store reset when adding a new Zustand store. This causes tests to pass
individually but fail in suite — a silent, hard-to-debug failure. Both
agents found it in the structured condition because the behavioral
invariants checklist explicitly names it.

**Source**: react-frontend-reference, M1 task, March/April 2026 historical run.

---

## Interactive Dashboard

The full experiment visualization with per-repo breakdowns is available at:

**https://cote-star.github.io/agent-recall/docs/**

---

## Full Evidence Sources

- **Full result breakdown**: [results.md](./results.md) in this repo
- **Experiment data and figures**: [cote-star/agent-recall](https://github.com/cote-star/agent-recall) -- SVG/PNG figures, evidence map, interactive dashboard
- **Experiment protocol and reference data**: [cote-star/agent-chorus](https://github.com/cote-star/agent-chorus) -- `docs/agent-context-results.md` and research artifacts. Pack creation and maintenance use this repo's `bin/agent-context` CLI.
