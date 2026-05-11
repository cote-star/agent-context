# agent-context

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.3.1-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**Portable system context for agents, checked into the repo.**

Agents start cold. They re-read the same tree, rediscover the same ownership boundaries, and miss the same hidden invariants. `agent-context` turns that repeated exploration into a small, reviewable context pack that lives beside the code.

The **skill authors** the pack. The **CLI verifies** it, checks freshness, and makes it safe to commit.

![agent-context impact at a glance](docs/visuals/hero-stat-ribbon.svg)

## Quickstart

Install the bundled skill once, then ask your coding agent to build the context pack.

| Agent | Setup |
|---|---|
| Claude Code | `git clone https://github.com/cote-star/agent-context.git && cp -r agent-context/skills/agent-context ~/.claude/skills/` |
| Codex | register `skills/agent-context/agents/openai.yaml` with your Codex skill registry |
| Cursor | open the target repo; Cursor reads `.cursorrules` after the pack exists |

In the repo you want to improve, ask:

> **Use the agent-context skill to build context for this repo.**

Then make the generated diff reviewable:

```bash
agent-context verify .
agent-context freshness . --base-ref origin/main
```

Open a PR with `.agent-context/`, the managed routing blocks, and any CI/hook follow-up the skill recommends.

<details>
<summary>Advanced/manual/scripted setup</summary>

Use the CLI directly when no agent is in the loop, or when bootstrapping repos in scripts:

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 --install-hook .
```

`init` scaffolds the files and routing blocks. It does not replace the authoring workflow; the pack still needs repo-specific content before `verify` will pass.
</details>

## Why This Exists

| Capability | What it gives you |
|---|---|
| **Agent-authored context** | One prompt produces a reviewable `.agent-context/` PR instead of a private model memory. |
| **Cross-agent routing** | Cursor, Claude, Codex, Gemini, OpenCode, and human reviewers consume the same checked-in pack. |
| **Machine checks** | `verify`, `freshness`, `doctor`, and `install-hook` make the artifact auditable locally and in CI. |
| **Evidence-backed workflow** | Q2 2026 rerun: 288 graded tasks across 48 cells, plus a historical reviewer-confirmed run set. |
| **Portable pattern** | Code repos are the validated venue today; the same context pattern applies to any system with state, rules, risk, and work to do. |
| **Zero infrastructure** | Markdown and JSON committed to your repo. No server, vector store, crawler, or API key. |

## What Gets Created

The skill and CLI scaffold a tiered pack under `.agent-context/current/`:

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

It also writes short managed routing blocks to `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.cursorrules` so agents read the pack before opening source files.

| Layer | Files | Job |
|---|---|---|
| **Content** | `00_*` through `40_*` markdown | Human-readable map, risks, invariants, operations |
| **Authority** | `routes.json`, `completeness_contract.json`, `reporting_rules.json` | Completeness rules for trust-and-follow agents |
| **Navigation** | `search_scope.json` | Scoped search and verification shortcuts for search-and-verify agents |
| **Quality** | `manifest.json`, `acceptance_tests.md`, helper tools | Validation, freshness, and PR review support |

## How It Works

The product experience is skill-first:

1. **Ask the agent** to use the `agent-context` skill.
2. **The skill inventories the repo**, chooses the right tier, scaffolds files when needed, fills templates, and writes grep-backed acceptance tests.
3. **The CLI verifies** structure, JSON schema, real glob matches, template cleanup, and freshness.
4. **You review the diff** like code and merge it through PR.

The CLI remains intentionally boring:

```bash
agent-context init --tier 3 --install-hook .   # scaffold
agent-context verify .                         # validate pack integrity
agent-context freshness . --base-ref origin/main
agent-context doctor                           # local setup audit
```

`init` is a bootstrap command. `verify` and `freshness` are what make agent-written context safe to commit.

## Results

### Q2 2026 multi-agent rerun

Current evidence: **288 graded tasks across 48 cells**: 6 repos × 4 model variants × bare/structured × 6 tasks. Every `structured_fresh` clone passed `agent-context verify` and strict freshness checks before the agent started.

| Agent / Model | Bare yes-rate | Structured yes-rate | Δ |
|---|---:|---:|---:|
| **Claude Opus 4.7** | 80% (4.80/6) | **100% (6.00/6)** | +20pp |
| **Cursor `claude-opus-4-7-medium`** | 89% (5.33/6) | **97% (5.83/6)** | +8pp |
| **Cursor `composer-2-fast`** | 61% (3.67/6) | **81% (4.83/6)** | +20pp |
| **Codex CLI 0.130.0** | 72% (4.33/6) | **78% (4.67/6)** | +6pp |

Headline stories:

- **Claude Opus + structured: 6/6 across all 6 repos.**
- **Cursor `composer-2-fast`: largest correctness lift** at +20 percentage points.
- **Cursor Opus medium: 219s → 78s median duration** under structured context.
- **Production-risk flags drop to zero** for Codex and Cursor Opus medium with structured context.

Grading is **LLM-provisional** via independent Claude Code subagents, one fresh-context grader per cell. Treat the Q2 numbers as directional until reviewer spot-audit is complete. Anomalies are disclosed rather than hidden; see [metrics methodology](docs/evidence/metrics.md#methodology-and-disclosure).

→ [Full Q2 results](docs/evidence/results.md#q2-2026-multi-agent-rerun-current-evidence) · [headline metrics](docs/evidence/metrics.md) · [evidence dashboard](https://cote-star.github.io/agent-recall/docs/)

### Historical reference

The March/April 2026 run set used **78+ reviewer-confirmed grades** across three repos. It is preserved as a historical reference and is not directly comparable to the Q2 LLM-provisional rerun.

| Metric | Bare | With agent-context | Change |
|---|---:|---:|---:|
| Correct answers | 50% | 88% | **+76%** |
| Files opened by Claude | 6.3 | 1.9 | **~70% fewer** |
| Tokens used by Claude | 38.6K | 13.1K | **~66% fewer** |
| Dead ends | 2-3 per repo | 0 | **eliminated** |
| Production-risk answers | 7 total | 0 | **eliminated** |

![agent-context proof summary — per-agent + historical](docs/visuals/proof-results.svg)

## Agent Architectures

The same `.agent-context/` pack serves two opposite loops:

```text
Trust-and-follow: Claude, Gemini, OpenCode with Anthropic backend
  routing block → required files → completeness contract → answer

Search-and-verify: Cursor, Codex, OpenCode with local model
  search scope → scoped grep → verification shortcut → answer
```

Claude-like agents can stop when the completeness contract is satisfied. Cursor/Codex-like agents still verify against source, but the pack tells them where to search and what evidence matters.

![Explorable recall as a three-track system](docs/evidence/figures/three-tracks-importance-minimal.svg)

## Tested Repositories

The Q2 rerun used the same general-purpose template across six code repos with zero template modifications.

| Repo type | Stack | Notes |
|---|---|---|
| CLI/library | Rust + Node.js | `agent-chorus` |
| ML pipeline | Python | training/inference workflow |
| React frontend | TypeScript | React Query + Zustand |
| Backend service | Python | FastAPI service |
| Polyglot monorepo | mixed | multi-language workspace |
| macOS daemon | Swift | process broker / daemon |

The seventh candidate, `org-second-brain`, was skipped because its experiment setup caused an interactive Claude session loop. It remains a follow-up, not part of the headline slate.

**Non-code corpora are not yet validated.** The design is intentionally broader than repos, but public evidence currently covers code repositories only.

## Tiers

Start small. Promote only when the repo needs more structure.

| Tier | Files | Best for | Direct CLI scaffold |
|---|---:|---|---|
| **1** minimal | 2 | Quick adoption, smaller repos | `init --tier 1 .` |
| **2** standard | 6 | Most teams starting out | `init --tier 2 .` |
| **3** full | 11 | Complex repos, production workflows | `init --tier 3 --install-hook .` |

## Examples

| Example | Size | Why look at it |
|---|---:|---|
| [`examples/hello-service/`](examples/hello-service/) | 6 files | Read the whole pack in five minutes |
| [`examples/agent-chorus-reference/`](examples/agent-chorus-reference/) | 155 files | Real dual Rust/Node CLI pack |

## Comparison

| | agent-context | Long-term memory | Multi-agent orchestration | agent-chorus |
|---|---|---|---|---|
| **Primitive** | Checked-in system context | Stored memory | Worker coordination | Cross-agent session visibility |
| **Best for** | Cold-start agent work and PR-scoped guidance | Persona/history recall | Delegated task execution | Reading and comparing agent sessions |
| **Runtime dependency** | none | service/vector store optional | framework runtime | chorus CLI |
| **Lives in repo** | yes | no | no | no |

For multi-agent session visibility and messaging, pair with [agent-chorus](https://github.com/cote-star/agent-chorus).

## Documentation

| Need | Document |
|---|---|
| First install | [Getting started](docs/getting-started.md) |
| Architecture deep-dive | [Architecture guide](docs/architecture.md) |
| Evidence | [Experiment results](docs/evidence/results.md) · [metrics summary](docs/evidence/metrics.md) |
| Agent-driven creation | [SKILL.md](SKILL.md) |
| CI setup | [CI adaptation](docs/ci-adaptation.md) |
| Design rationale | [16 design principles](docs/design-principles.md) |
| Roadmap | [Roadmap](docs/roadmap.md) |

## Project Scope

The public `agent-context` CLI, templates, verifier, examples, and evidence docs live here. `chorus` session-reading commands live in [agent-chorus](https://github.com/cote-star/agent-chorus).

Found a bug or a missing system pattern? [Open an issue](https://github.com/cote-star/agent-context/issues).
