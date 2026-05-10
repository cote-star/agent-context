# agent-context

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.3.1-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**Checked-in repo evidence for coding agents.**

Commit one `.agent-context/` directory to your repo. Cursor, Claude, Codex, Gemini, OpenCode, and human reviewers get the same content map, authority contracts, search boundaries, and verification hooks before anyone edits code.

![agent-context impact at a glance](docs/visuals/hero-stat-ribbon.svg)

## Install the skill, then ask your agent

Install the bundled skill into your agent of choice (one-time):

| Agent       | Install |
|-------------|---------|
| Claude Code | `git clone https://github.com/cote-star/agent-context.git && cp -r agent-context/skills/agent-context ~/.claude/skills/` |
| Codex       | register `skills/agent-context/agents/openai.yaml` with your Codex skill registry |
| Cursor      | reads `.cursorrules` from the target repo natively — open the repo, no extra install step |

Then in any repo, ask your agent:

> **Set up agent context for this repo.**

The skill drives scaffold → fill from the subsystem inventory → acceptance tests with grep verification → `verify` → advisory pre-push freshness hook. Output is a reviewable diff in one PR.

**Other agents are supported.** Gemini, OpenCode, and any agent that reads `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.cursorrules` consume the same pack under the same dual-routing architecture; measured runs only exist for Claude, Codex, and Cursor today.

<details>
<summary>If you want the CLI directly (advanced)</summary>

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 --install-hook .
```

The skill invokes the same `agent-context` CLI under the hood. Running it yourself is useful for scripted setup or CI where an agent isn't in the loop.
</details>

## Features

| | Feature | Why it matters | Where in this README |
|---:|---|---|---|
| 1 | **Works across agents** | Cursor, Claude, Codex, Gemini, and OpenCode all read the same `.agent-context/`. `init` writes the routing block to `.cursorrules`, `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` — modern agents read several of these together as project rules (Cursor, for example, picks up `.cursorrules` + `CLAUDE.md` + `AGENTS.md`), so any one of the four is enough to route any agent. | [§Architecture](#architecture) |
| 2 | **Quantified evidence** | 78+ reviewer-graded answers across three real repos, with grep-backed verification of every claim | [§Results](#results) |
| 3 | **Tiered adoption** | Start with 2 files, scale to 11 — every tier is a valid stopping point | [§Tiers](#tiers) |
| 4 | **Agent-creatable** | One prompt — `Set up agent context for this repo.` — fills the pack, acceptance tests, routing blocks, and hook/CI guidance via the included root skill and installable `skills/agent-context/` package | [SKILL.md](SKILL.md) |
| 5 | **Machine-checkable** | `verify`, `freshness`, `doctor`, and `install-hook` make every artifact auditable locally and in CI | [§How it works](#how-it-works) |
| 6 | **Zero infra** | Markdown + JSON committed to your repo — no server, vector store, or API key | [§The cold-start tax](#the-cold-start-tax) |

## The cold-start tax

Every coding agent session starts cold. On a real repo it spends the first chunk of every task re-reading the directory tree, guessing ownership boundaries, and missing the one setup file or invariant that should have shaped the answer. That cost compounds over every question, every reviewer, every agent.

`agent-context` turns that repeated exploration into a small, reviewable evidence layer that lives beside the code:

- **Content** — system overview, code map, behavioral invariants, operations notes.
- **Authority** — task routes, completeness contracts, and reporting rules for agents that follow explicit instructions.
- **Navigation** — scoped directories and verification shortcuts for agents that search before trusting.
- **Quality** — manifests, acceptance tests, copied helper tools, and CI-friendly checks.

It is **not** a memory database, orchestrator, crawler, or hosted service. No server, vector store, or API key. Markdown and JSON, committed to your repo.

![agent-context loop](docs/visuals/agent-context-loop.svg)

## Results

### Q2 2026 multi-agent rerun — current evidence

**252 graded answers across 48 cells**: 6 repos × 4 model variants × bare/structured × 6 tasks. Fresh-pack isolated protocol — every `structured_fresh` clone passed `agent-context verify` + strict `check_freshness.sh` before the agent started.

| Agent / Model | Bare yes-rate | Structured yes-rate | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

**Claude Opus + structured pack: 6/6 perfect across all 6 repos.** Cursor `composer-2-fast` (the default) gains the most absolute lift; Cursor Opus medium and Codex are already strong on bare.

**Production-risk drops to zero** with structured for codex and cursor opus medium (`risk_flag` per 6 tasks, mean): codex 0.33 → **0.00**; cursor opus 0.50 → **0.00**.

**Cursor Opus medium duration cut 65%** under structured (median 219s → 78s per task) — the search-and-verify pattern collapses to direct reads when the pack guides navigation.

Grading is **LLM-provisional** via independent Claude Code subagents (one subagent per cell, fresh context, no human spot-audit). Anomalies preserved in the writeup rather than masked. Full disclosure: [methodology](docs/evidence/metrics.md#methodology-and-disclosure).

→ [Full Q2 2026 results](docs/evidence/results.md#q2-2026-multi-agent-rerun-current-evidence) · [headline metrics](docs/evidence/metrics.md) · [evidence dashboard](https://cote-star.github.io/agent-recall/docs/)

### Historical reference (78-graded run set, March/April 2026)

The pre-Q2-2026 evidence: 78+ reviewer-confirmed grades across three repos (ml-pipeline-reference, agent-chorus, react-frontend-reference). Headline numbers preserved for comparison; superseded as the lead claim by the Q2 rerun above.

| Metric | Bare | With agent-context | Change |
|---|---:|---:|---:|
| Correct answers | 50% | 88% | **+76%** |
| Files opened by Claude (3-repo avg) | 6.3 | 1.9 | **~70% fewer** |
| Tokens used by Claude (3-repo avg) | 38.6K | 13.1K | **~66% fewer** |
| Dead ends | 2–3 per repo | 0 | **eliminated** |
| Production-risk answers | 7 total | 0 | **eliminated** |

![agent-context proof summary — per-agent + historical](docs/visuals/proof-results.svg)

(The visual summarises the historical 3-repo run set; an updated 6-repo Q2 figure is on the v0.5 roadmap.)

**Other agents read the same pack.** Gemini, OpenCode (with local OSS or Anthropic backend), and any agent that consumes `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / `.cursorrules` route through the same dual architecture (trust-and-follow vs search-and-verify). Measured runs exist for Claude, Codex, and Cursor (composer-2-fast and claude-opus-4-7-medium); the artifact set is the same for every agent.

### Definitions

Every claim above maps to an operational definition and a citation in the evidence docs.

| Term | What we count | Source |
|---|---|---|
| **Correct answer** | Reviewer judges all required claims true and complete; reported as the "yes rate" across 78 graded answers | [`docs/evidence/results.md`](docs/evidence/results.md) §Correctness |
| **Files opened** | Source files the agent reads via the `Read` tool during one task — `grep` and `find` listings excluded | [`docs/evidence/results.md`](docs/evidence/results.md) §Efficiency |
| **Tokens** | Per-session total of prompt + response tokens, reported in K | [`docs/evidence/results.md`](docs/evidence/results.md) §Efficiency |
| **Dead end** | A file the agent opens that turns out to be irrelevant to the task — P8: *"track files opened that turned out irrelevant as the primary metric, not just file count"* | [`docs/design-principles.md`](docs/design-principles.md) P8 |
| **Production-risk answer** | An answer that, if acted on, would break production: wrong API, wrong file, missing invariant | [`docs/evidence/results.md`](docs/evidence/results.md) §Risk Flags |
| **Time-to-answer** | One observed task hit zero files and **12 seconds** end-to-end with the pack — vs. multi-minute baselines. Aggregate time measurement is on the v0.5 roadmap. | [`docs/evidence/results.md`](docs/evidence/results.md) §Best Stories · [v0.5 roadmap](docs/roadmap.md) |

## How it works

The skill drives the workflow end-to-end. Each step is a CLI subcommand the skill invokes — and that you can run directly if you skip the agent path.

### 1. Initialize

The skill starts by scaffolding the pack:

```bash
agent-context init --tier 3 --install-hook .
```

![agent-context init demo](docs/demos/init.svg)

Creates `.agent-context/current/`, copies helper tools into `.agent-context/tools/`, writes managed routing blocks to `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, and `.cursorrules`, and installs an advisory pre-push freshness hook when no unmanaged hook blocks safe install.

### 2. Fill the artifacts

Once scaffolded, the agent enumerates every subsystem (so nothing silently gets skipped), fills all templates, writes acceptance tests with grep verification, and leaves a reviewable diff. [SKILL.md](SKILL.md) is the workflow it follows.

> Set up agent context for this repo.

If you skipped the skill path, you can edit the `REPLACE` markers manually instead.

![agent-context workflow](docs/demos/demo-agent-context.svg)

### 3. Verify

```bash
agent-context verify .
# OK: agent-context passed machine-checkable validation (tier 3)

agent-context freshness . --base-ref origin/main
agent-context doctor
```

![agent-context verify pass](docs/demos/verify.svg)

`verify` checks structure, JSON schema, real glob matches, and template-variable elimination. `freshness` flags drift between code and pack. `doctor` audits local setup. `install-hook` adds or refreshes the advisory local pre-push freshness hook. All checks are CI-friendly.

## Architecture

The core design is dual routing — **same artifacts, opposite agent loops**. One pack, two reading patterns:

```text
Search-and-verify (Cursor, Codex, OpenCode w/ local model)
  search_scope   →  scoped grep     →  verification shortcut  →  answer

Trust-and-follow (Claude, Gemini, OpenCode w/ Anthropic backend)
  routing block  →  required files  →  completeness contract  →  answer
```

The same `.agent-context/` content is consumed differently by each agent family. Cursor, Codex, and OpenCode (with a local model backend) bound their grep to scoped directories and cross-check verification shortcuts. Claude, Gemini, and OpenCode (with an Anthropic backend) stop when the completeness contract says done. agent-context provides scaffolding for both — completeness contracts for trust-and-follow agents, bounded search for search-and-verify agents.

**Model-agnostic by construction.** The pack is markdown and JSON; routing blocks are plain text. Operator-verified with OpenCode running locally on a Mac and pointing at an OSS model (Devstral Small 2 or Qwen 4B) via SSH tunnel to a separate inference host — the pack reads identically regardless of where the model runs or which vendor ships it.

![agent-context artifact system](docs/demos/cold-start-agent-context-hero.svg)

| Layer | Files | Job |
|---|---|---|
| **Content** | `00_*` through `40_*` markdown | Human-readable map, risks, invariants |
| **Authority** | `routes.json`, `completeness_contract.json`, `reporting_rules.json` | What MUST be in a complete answer |
| **Navigation** | `search_scope.json` | Bound search-and-verify agents to relevant dirs |
| **Quality** | `manifest.json`, `acceptance_tests.md`, helper tools | Make the pack auditable and CI-checkable |

![Explorable recall as a three-track system](docs/evidence/figures/three-tracks-importance-minimal.svg)

```text
.agent-context/current/
├── 00_START_HERE.md
├── 10_SYSTEM_OVERVIEW.md
├── 20_CODE_MAP.md
├── 30_BEHAVIORAL_INVARIANTS.md
├── 40_OPERATIONS_AND_RELEASE.md
├── routes.json
├── completeness_contract.json
├── reporting_rules.json
├── search_scope.json
├── manifest.json
└── acceptance_tests.md

.agent-context/tools/
├── verify_agent_context.py
├── check_freshness.sh
└── pre-push-hook.sh
```

→ [Architecture deep-dive](docs/architecture.md) · [16 design principles](docs/design-principles.md)

## Tested repositories

The same `.agent-context/` template has been validated across stacks and across two orders of magnitude in repo size — with **zero modifications**.

| Repo | Files | Stack | Result |
|---|---:|---|---|
| ML pipeline (`ml-pipeline-reference`) | 501 | Python | 50% → 83% correct · 74% fewer tokens · 0 dead ends |
| Dual CLI (`agent-chorus`) | 155 | Rust + Node.js | Codex hit **6/6** (highest of any condition across all experiments) · 69% fewer tokens with Claude |
| React frontend (`react-frontend-reference`) | 1,982 | TypeScript | 50% → 100% correct · 58% fewer tokens · 0 dead ends |

**Repo-agnostic by design.** Principle P1 ([`docs/design-principles.md`](docs/design-principles.md)) is tagged `[all repos]` — the artifact set is built to "apply regardless of repo type, size, or stack."

**Non-code corpora — not yet tested.** The same content + authority + navigation pattern is designed to generalize to datasets, design systems, runbooks, and other stable corpora that an agent must read before acting. Currently validated only on code repos. The first non-code corpus test is on the [v0.5 roadmap](docs/roadmap.md).

## Tiers

Start small. Scale when the team is ready. Each tier is a valid stopping point — no hidden dependency on the full pack.

| Tier | Files | Best for | Command |
|---|---:|---|---|
| **1** minimal | 2 | Quick adoption, smaller repos | `init --tier 1 .` |
| **2** standard | 6 | Most teams starting out | `init --tier 2 .` |
| **3** full | 11 | Complex repos, production workflows | `init --tier 3 --install-hook .` |

## Examples

Two worked examples ship in this repo. Both pass `verify` as-is — clone, read, adapt.

| Example | Size | Why look at it |
|---|---|---|
| [`examples/hello-service/`](examples/hello-service/) | 6 files, ~300 LOC HTTP service | Read the whole pack in five minutes |
| [`examples/agent-chorus-reference/`](examples/agent-chorus-reference/) | 155 files, dual Rust/Node.js CLI | Real repo, full tier 3 pack — scored 6/6 with Codex, 69% token savings with Claude |

## Comparison

| | agent-context | MemGPT / Letta | CrewAI / AutoGen | agent-chorus |
|---|---|---|---|---|
| **Primitive** | Checked-in repo evidence | Long-term memory | Multi-agent orchestration | Cross-agent session visibility |
| **Best for** | Cold-start coding work, PR-scoped guidance | Persona/history recall | Worker coordination | Reading and messaging agents |
| **Runtime dependency** | none | service / vector store optional | Python + LLM calls | chorus CLI |
| **Lives in repo** | yes | no | no | no |

For multi-agent session visibility and messaging, pair with [agent-chorus](https://github.com/cote-star/agent-chorus).

## Roadmap

- **v0.3 authoring UX** — better `doctor` output, clearer template diagnostics, guided fixes for common verifier failures.
- **v0.4 freshness gates** — stronger CI examples for monorepos, generated files, and multiple source roots.
- **v0.5 evidence loop** — lightweight before/after measurement scripts so teams can prove agent-context is helping.
- **Reference packs** — backend services, frontend apps, CLIs, data pipelines, monorepos.

→ [Full roadmap](docs/roadmap.md)

## Documentation

Each doc maps to one of the features above (or to general onboarding).

| Need | Document | Feature |
|---|---|---|
| First install | [Getting started](docs/getting-started.md) | — |
| Architecture deep-dive | [Architecture guide](docs/architecture.md) | Dual-mode routing |
| Evidence | [Experiment results](docs/evidence/results.md) · [metrics summary](docs/evidence/metrics.md) | Quantified evidence |
| Agent-driven creation | [SKILL.md](SKILL.md) | Agent-creatable |
| CI setup | [CI adaptation](docs/ci-adaptation.md) | Machine-checkable |
| Design rationale | [16 design principles](docs/design-principles.md) | — |
| Release history | [Release notes](RELEASE_NOTES.md) | — |

## Project scope

The public `agent-context` CLI, templates, verifier, examples, and evidence docs live here. `chorus` session-reading commands live in [agent-chorus](https://github.com/cote-star/agent-chorus).

Found a bug or a missing repo pattern? [Open an issue](https://github.com/cote-star/agent-context/issues).
