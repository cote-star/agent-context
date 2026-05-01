# agent-context

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.0-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**Checked-in repo evidence for coding agents.**

Commit one `.agent-context/` directory to your repo. Claude, Codex, Cursor, Gemini, and human reviewers get the same content map, authority contracts, search boundaries, and verification hooks before anyone edits code.

![agent-context cold start flow](docs/demos/cold-start-agent-context-hero.svg)

```bash
# Install once
git clone https://github.com/cote-star/agent-context.git ~/agent-context

# Add the full agent-context artifact set to any repo
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 .
```

## Why This Exists

Coding agents still start cold. On a large repo they spend the first part of every session re-reading directory trees, guessing ownership boundaries, and missing the one setup file or invariant that should have shaped the answer.

`agent-context` turns that repeated exploration into a local, reviewable evidence layer:

- **Content**: system overview, code map, behavioral invariants, and operations notes.
- **Authority**: task routes, completeness contracts, and reporting rules for agents that follow explicit instructions.
- **Navigation**: scoped directories and verification shortcuts for agents that search before trusting.
- **Quality**: manifests, acceptance tests, copied helper tools, and CI-friendly checks.

It is not a memory database, orchestrator, crawler, or hosted service. It is a small artifact set that lives beside the code it describes.

![agent-context loop](docs/visuals/agent-context-loop.svg)

## Proof

Across 78+ reviewer-graded experiment runs on three repo types, agent-context artifacts improved answer correctness and reduced wasted exploration.

| Metric | Bare session | With agent-context | Change |
|---|---:|---:|---:|
| Correct answers | 50% | 88% | **+76%** |
| Files opened by Claude | 6-10 | 1-3 | **~70% fewer** |
| Tokens used by Claude | 40-53K | 4-22K | **58-74% fewer** |
| Dead ends | 2-3 per repo | 0 | **eliminated** |
| Production-risk answers | 7 total | 0 | **eliminated** |

Evidence: [full results](docs/evidence/results.md), [metrics summary](docs/evidence/metrics.md), [evidence dashboard](https://cote-star.github.io/agent-recall/docs/).

![Agent-context proof summary](docs/visuals/proof-results.svg)

## See It Work

### 1. Initialize

```bash
~/agent-context/bin/agent-context init --tier 3 .
```

![agent-context init demo](docs/demos/init.svg)

The command creates `.agent-context/current/`, copies helper tools into `.agent-context/tools/`, and writes managed routing blocks to `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, and `.cursorrules`.

### 2. Fill the Artifacts

Fill the `REPLACE` markers manually or ask an agent:

> Set up agent context for this repo.

The included [SKILL.md](SKILL.md) gives agents a concrete creation workflow: inventory subsystems, fill all templates, add acceptance tests, verify answers against grep, and run the machine checks.

![agent-context workflow](docs/demos/demo-agent-context.svg)

### 3. Verify

```bash
~/agent-context/bin/agent-context verify .
# OK: agent-context passed machine-checkable validation (tier 3)
```

You can also inspect local setup and freshness:

```bash
~/agent-context/bin/agent-context doctor
~/agent-context/bin/agent-context freshness . --base-ref origin/main
```

![agent-context verify pass](docs/demos/verify.svg)

## What Gets Created

Tier 3, the default, creates the full 11-file artifact set:

```text
.agent-context/current/
|-- 00_START_HERE.md
|-- 10_SYSTEM_OVERVIEW.md
|-- 20_CODE_MAP.md
|-- 30_BEHAVIORAL_INVARIANTS.md
|-- 40_OPERATIONS_AND_RELEASE.md
|-- routes.json
|-- completeness_contract.json
|-- reporting_rules.json
|-- search_scope.json
|-- manifest.json
`-- acceptance_tests.md

.agent-context/tools/
|-- verify_agent_context.py
`-- check_freshness.sh
```

| Layer | Files | Main job |
|---|---|---|
| Content | `00_*` through `40_*` markdown | Human-readable map, risks, invariants, validation |
| Authority | `routes.json`, `completeness_contract.json`, `reporting_rules.json` | State what must be considered before an answer is complete |
| Navigation | `search_scope.json` | Bound search-and-verify agents to relevant directories |
| Quality | `manifest.json`, `acceptance_tests.md`, copied tools | Make the artifacts auditable and CI-friendly |

## Tiers

| Tier | Files | Best for | Command |
|---|---:|---|---|
| **1** minimal | 2 | Quick adoption, smaller repos | `init --tier 1 .` |
| **2** standard | 6 | Most teams starting out | `init --tier 2 .` |
| **3** full | 11 | Complex repos and production workflows | `init --tier 3 .` |

## Architecture

The core design is a three-track architecture. Navigation tells an agent what to load and when to stop. The operating loop accounts for different agent behavior. Engineering makes the work inspectable, durable, and CI-checkable.

![Explorable recall as a three-track system](docs/evidence/figures/three-tracks-importance-minimal.png)

Claude and Gemini tend to trust explicit instructions. Codex and Cursor tend to search and verify. `agent-context` is designed for both modes:

| Agent family | Uses agent-context as | Best layer |
|---|---|---|
| Trust-and-follow | an authority contract | `routes.json` + completeness contracts |
| Search-and-verify | a scoped investigation map | `search_scope.json` + code map |
| Humans | operational documentation | markdown content layer |

![Same navigation design, opposite behavior](docs/evidence/figures/asymmetry-contrast-minimal.png)

The goal is not to make agents stop thinking. The goal is to give them better starting evidence, clearer boundaries, and a machine-checkable way to catch stale repo guidance.

## What This Is Not

`agent-context` is intentionally narrow:

- It does **not** store chat history or personal memory.
- It does **not** coordinate multiple agents.
- It does **not** require a server, vector database, or API key.
- It does **not** replace tests, CI, or human review.

If you want multi-agent session visibility and messaging, pair it with [agent-chorus](https://github.com/cote-star/agent-chorus).

## Compared With Nearby Tools

| | agent-context | MemGPT / Letta | CrewAI / AutoGen | agent-chorus |
|---|---|---|---|---|
| Primitive | Checked-in repo evidence | Long-term memory | Multi-agent orchestration | Cross-agent session visibility |
| Best for | Cold-start coding work and PR-scoped repo guidance | Persona/history recall | Worker coordination | Reading and messaging agents |
| Runtime dependency | none | service/vector store optional | Python + LLM calls | chorus CLI |
| Lives in repo | yes | no | no | no |

## Roadmap

The next work is about making artifacts easier to author, keep fresh, and measure across repos:

- **v0.3 authoring UX**: better `doctor` output, clearer template diagnostics, and guided fixes for common verifier failures.
- **v0.4 freshness gates**: stronger CI examples for monorepos, generated files, and multiple source roots.
- **v0.5 evidence loop**: lightweight before/after measurement scripts so teams can prove whether agent-context is helping.
- **Reference artifact sets**: more real examples for backend services, frontend apps, CLIs, data pipelines, and monorepos.

Details: [docs/roadmap.md](docs/roadmap.md).

## Docs

| Need | Start here |
|---|---|
| First install | [Getting started](docs/getting-started.md) |
| Architecture | [Architecture guide](docs/architecture.md) |
| Design rationale | [Design principles](docs/design-principles.md) |
| CI setup | [CI adaptation](docs/ci-adaptation.md) |
| Evidence | [Experiment results](docs/evidence/results.md) |
| Agent-driven creation | [SKILL.md](SKILL.md) |
| Release history | [Release notes](RELEASE_NOTES.md) |

## Repository Boundary

This repo ships the public `agent-context` CLI, templates, verifier, examples, and evidence docs. It does not ship `chorus` session-reading commands; that belongs to [agent-chorus](https://github.com/cote-star/agent-chorus).

Found a bug or a missing repo pattern? [Open an issue](https://github.com/cote-star/agent-context/issues).
