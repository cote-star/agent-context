# agent-context

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.0-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**A navigation contract for AI agents working in large codebases.**

AI coding agents pay a _cold-start tax_ on every new session — re-reading the same repo from zero. `agent-context` gives you a structured, token-efficient briefing that lives in `.agent-context/current/`, plus routing blocks that tell every agent to read the pack first. One pack, multiple agents, zero orchestrator.

![agent-context init demo](docs/demos/init.webp)

## Evidence

Tested across 3 repo types (ML pipeline/501 files, CLI library/155 files, React frontend/1,982 files), 78+ graded experiment runs:

| Metric | Without pack | With pack | Change |
|--------|-------------|-----------|--------|
| Correct answers | 50% | 88% | **+76%** |
| Files opened (Claude) | 6-10 | 1-3 | **-70%** |
| Tokens used (Claude) | 40-53K | 4-22K | **-58 to -74%** |
| Dead ends | 2-3 per repo | 0 | **-100%** |
| Production-risk answers | 7 total | 0 | **eliminated** |

The same pack made one agent (Claude) narrower — 14 files down to 4 — while making another (Codex) broader — 3 files up to 12. Both got more correct answers. Different agents use the same contract differently.

Full evidence: [`docs/evidence/`](docs/evidence/) | Interactive dashboard: [context-pack-viz](https://cote-star.github.io/agent-recall/docs/)

## Quick Start

Three commands, under two minutes:

```bash
git clone https://github.com/cote-star/agent-context.git
cd your-repo
/path/to/agent-context/bin/agent-context init --tier 3 .
# ...fill the REPLACE markers in each template...
/path/to/agent-context/bin/agent-context verify .
```

That's it. Every agent session on that repo can now read the pack first and open source files only when needed.

Or use the skill — open any agent (Claude Code, Cursor, Codex) in your repo and say:

> **"Set up agent context for this repo"**

The agent follows the [`SKILL.md`](SKILL.md) and creates the full pack in ~15 minutes.

## Tiers

Not every repo needs the full pack:

| Tier | Files | Best for | Init command |
|------|-------|----------|-------------|
| **1** (minimal) | `20_CODE_MAP.md` + `search_scope.json` | Quick adoption, 50-100 file repos | `agent-context init --tier 1 .` |
| **2** (standard) | + start, invariants, manifest, acceptance tests | Most repos, 100-500 files | `agent-context init --tier 2 .` |
| **3** (full) | + all 5 docs + authority layer (routes, contracts, reporting) | Complex repos, 500+ files | `agent-context init .` (default) |

## See It Work

Run the worked example:

```bash
cd examples/hello-service
../../bin/agent-context verify .
# OK: agent-context pack passed machine-checkable validation (tier 2)
```

Inside `examples/hello-service/` is a tiny Python service with a fully filled pack. For a real-world example from a 155-file CLI repo, see `examples/agent-chorus-reference/`.

![agent-context verify pass vs fail](docs/demos/verify.webp)

## The 3-Layer Pack

```
.agent-context/current/
├── 00_START_HERE.md             ─┐
├── 10_SYSTEM_OVERVIEW.md         │  Content layer (markdown)
├── 20_CODE_MAP.md                │  Read by humans + all agents
├── 30_BEHAVIORAL_INVARIANTS.md   │
├── 40_OPERATIONS_AND_RELEASE.md ─┘
├── routes.json                   ─┐
├── completeness_contract.json     │  Authority layer (JSON, tier 3)
├── reporting_rules.json          ─┘  Trust-and-follow agents (Claude)
├── search_scope.json             ← Navigation layer
├── manifest.json                 ← Metadata
└── acceptance_tests.md           ← Author-time quality checks
```

- **Content** (5 markdown docs) — architecture, code map, invariants, ops. Deterministic read order `00 → 10 → 20 → 30 → 40`.
- **Authority** (3 JSON files, tier 3) — task routing, completeness contracts ("what MUST be in the answer"), reporting rules. Claude trusts these as authoritative — result: answers from pure context, zero files opened.
- **Navigation** (`search_scope.json`) — bounds WHERE search-and-verify agents (Codex, Cursor) look. Does not prescribe when to stop.

## Cursor Integration

`agent-context init` generates a `.cursorrules` file with the search-and-verify routing block:

```
1. Read .agent-context/current/routes.json → identify task type
2. Load contracts from completeness_contract.json + search_scope.json
3. Search ONLY within scoped directories defined in search_scope.json
4. Do not open repo source files before step 3
```

Cursor reads `.cursorrules` automatically. No extra configuration needed.

## Three-Track Framework

Packs are one part of a broader frame:

- **Navigation** — the pack. Where the agent looks first.
- **Harness** — the agent setup and rails around it (Cursor, Claude Code, Codex).
- **Engineering** — the underlying codebase shape that lets both above work.

Full argument: [explorable-recall research](https://cote-star.github.io/agent-recall/)

## How It Compares

| | agent-context | MemGPT / Letta | CrewAI / AutoGen |
|---|:---:|:---:|:---:|
| Primitive | Static repo-level pack | Long-term LLM memory | Multi-agent orchestration |
| When to use | Cold-start for coding agents in big repos | Persona + history continuity across chats | Coordinating multiple LLM workers on a task |
| Runtime dependency | none (stdlib Python, shell) | Python framework + vector store | Python framework + LLM calls |
| Local-first | yes | optional | optional |
| Scope | Navigation contract | Memory | Orchestration |

Different problem, different primitive. They stack.

## What This Repo Ships vs What's in agent-chorus

| Capability | agent-context (here) | agent-chorus |
|---|:---:|:---:|
| 5-doc content templates | yes | yes |
| Authority layer (`routes.json`, `completeness_contract.json`, `reporting_rules.json`) | yes (tier 3) | yes |
| `search_scope.json` | yes | yes |
| `verify_context_pack.py` | yes | yes |
| `check_freshness.sh` | yes | yes |
| Python CLI (`init / verify / doctor / freshness`) | yes | — |
| Tier support (1/2/3) | yes | yes |
| Routing block generation (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules) | yes | yes |
| SKILL.md (agent-driven pack creation) | yes | yes |
| Cross-agent session reading | **no** | yes |
| Agent-to-agent messaging | **no** | yes |
| Chorus binary dependency | **no** | yes |
| License | MIT | MIT |

If you only want "navigation + verification," stay here. If you want multi-agent visibility, session reads, and the full agent coordination layer, pair with [agent-chorus](https://github.com/cote-star/agent-chorus).

## Recipes

**Create a pack from scratch:**

```bash
cd ~/code/my-service
/path/to/agent-context/bin/agent-context init .
$EDITOR .agent-context/current/00_START_HERE.md   # fill the REPLACE markers
/path/to/agent-context/bin/agent-context verify .
```

**Quick tier 1 for small repos:**

```bash
/path/to/agent-context/bin/agent-context init --tier 1 .
```

**Wire verification into CI** — see `docs/ci-adaptation.md`. Short version:

```yaml
- name: Verify agent-context pack
  run: python3 .agent-context/tools/verify_context_pack.py
```

**Install the advisory pre-push hook:**

```bash
cp tools/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Roadmap

- **v0.3.0** — Hardening (binary/encoding safety, concurrency, schema versioning, trust-boundary checks).
- Broader agent family testing (Gemini, Cursor) on route-trusting / route-verifying taxonomy.
- Pip packaging (`pip install agent-context`).
- Windows support.
- CI templates for CircleCI, Jenkins, GitLab.

See [GitHub issues](https://github.com/cote-star/agent-context/issues) for current scope.

## Go Deeper

| If you need... | Go here |
|---|---|
| The SKILL.md (agent-driven pack creation) | [`SKILL.md`](SKILL.md) |
| Getting started guide | [`docs/getting-started.md`](docs/getting-started.md) |
| The three-layer model in detail | [`docs/architecture.md`](docs/architecture.md) |
| The 16 design principles behind pack structure | [`docs/design-principles.md`](docs/design-principles.md) |
| CI adaptation guidance | [`docs/ci-adaptation.md`](docs/ci-adaptation.md) |
| Evidence and experiment results | [`docs/evidence/`](docs/evidence/) |
| The three-way sync policy | [`docs/SYNC.md`](docs/SYNC.md) |
| Research narrative + interactive dashboard | [explorable-recall](https://cote-star.github.io/agent-recall/) |
| Companion tooling for multi-agent work | [agent-chorus](https://github.com/cote-star/agent-chorus) |
| Research repo (experiments + graded runs) | [agent-recall](https://github.com/cote-star/agent-recall) |

---

Found a bug or have a feature idea? [Open an issue](https://github.com/cote-star/agent-context/issues). Ready to contribute? See [`CONTRIBUTING.md`](CONTRIBUTING.md) — the default path for template and script changes is a PR against the canonical source first; see [`docs/SYNC.md`](docs/SYNC.md).
