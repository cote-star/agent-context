# agent-context

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.1.0-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)

**A navigation contract for AI agents working in large codebases.**

AI coding agents pay a _cold-start tax_ on every new session — re-reading the same repo from zero. `agent-context` gives you a 5-doc, token-efficient briefing that lives in `.agent-context/current/`, plus a `search_scope.json` that tells search-and-verify agents where to look first. One pack, multiple agents, zero orchestrator.

![agent-context init demo](docs/demos/init.webp)

## Quick Start

Three commands, under two minutes:

```bash
git clone https://github.com/cote-star/agent-context.git
cd agent-context
./bin/agent-context init .                # copies templates into .agent-context/current/
# ...fill the REPLACE markers in each template...
./bin/agent-context verify .              # exits 0 when the pack is valid
```

That's it. Every agent session on that repo can now read the pack first and open source files only when needed.

## See It Work

Run the worked example:

```bash
cd examples/hello-service
../../bin/agent-context verify .
# OK: agent-context pack passed machine-checkable validation
```

Inside `examples/hello-service/` is a tiny Python service with a fully filled pack under `.agent-context/current/`. Open `00_START_HERE.md` there to see what a completed template looks like.

![agent-context verify pass vs fail](docs/demos/verify.webp)

Prefer a live demo? The companion [context-pack-viz](https://context-pack-viz.vercel.app) renders a real pack in the browser.

## The 3-Layer Pack in 60 Seconds

```
.agent-context/current/
├── 00_START_HERE.md             ─┐
├── 10_SYSTEM_OVERVIEW.md         │  Content layer (markdown)
├── 20_CODE_MAP.md                │  Read by humans + all agents
├── 30_BEHAVIORAL_INVARIANTS.md   │
├── 40_OPERATIONS_AND_RELEASE.md ─┘
├── search_scope.json             ← Navigation layer
├── manifest.json                 ← Informational metadata
└── acceptance_tests.md           ← Author-time checks
```

- **Content** (5 markdown docs) — architecture, code map, invariants, ops. Deterministic read order `00 → 10 → 20 → 30 → 40`.
- **Navigation** (`search_scope.json`) — bounds WHERE search-and-verify agents look; does not prescribe when to stop.
- **Manifest** — informational metadata (freshness, version, git revision).

> **Note on the authority layer.** A third layer — `routes.json`, `completeness_contract.json`, `reporting_rules.json` — exists for trust-and-follow agents coupled to chorus tooling. That layer is **not** shipped here by design. It lives in [agent-chorus](https://github.com/cote-star/agent-chorus) where the runtime makes it useful.

## Three-Track Framework

Packs are one part of a broader frame:

- **Navigation** — the pack. Where the agent looks first.
- **Harness** — the agent setup and rails around it (chorus, custom agents, plugins).
- **Engineering** — the underlying codebase shape that lets both above work.

Full argument in the Substack post: [explorable-recall](https://yourname.substack.com/p/explorable-recall). The research paper backs it with graded-run evidence: [arXiv:TBD](https://arxiv.org/abs/TBD).

## What This Repo Ships vs What's in agent-chorus

| Capability | agent-context (here) | agent-chorus |
|---|:---:|:---:|
| 5-doc content templates | yes | yes |
| `search_scope.json` | yes | yes |
| `verify_context_pack.py` | yes | yes |
| `check_freshness.sh` | yes | yes |
| Python CLI (`init / verify / doctor / freshness`) | yes | — |
| Authority layer (`routes.json`, `completeness_contract.json`, `reporting_rules.json`) | **no** | yes |
| Cross-agent session reading | **no** | yes |
| Agent-to-agent messaging | **no** | yes |
| Chorus binary dependency | **no** | yes |
| License | MIT | MIT |

If you only want "shared navigation plus verification," stay here. If you want multi-agent visibility, session reads, and the trust-and-follow authority layer, pair with agent-chorus.

## Recipes

**Create a pack from scratch in a repo you maintain:**

```bash
cd ~/code/my-service
~/path/to/agent-context/bin/agent-context init .
$EDITOR .agent-context/current/00_START_HERE.md   # fill the REPLACE markers
~/path/to/agent-context/bin/agent-context verify .
```

**Wire verification into CI** — reference workflow in `docs/ci-adaptation.md`. Short version:

```yaml
- name: Verify agent-context pack
  run: python3 .agent-context/tools/verify_context_pack.py
```

**Install the advisory pre-push hook:**

```bash
cp tools/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## How It Compares

| | agent-context | MemGPT / Letta | CrewAI / AutoGen |
|---|:---:|:---:|:---:|
| Primitive | Static repo-level pack | Long-term LLM memory | Multi-agent orchestration |
| When to use | Cold-start for coding agents in big repos | Persona + history continuity across chats | Coordinating multiple LLM workers on a task |
| Runtime dependency | none (stdlib Python, shell) | Python framework + vector store | Python framework + LLM calls |
| Local-first | yes | optional | optional |
| Scope | Navigation contract | Memory | Orchestration |

Different problem, different primitive. `agent-context` starts where the agent opens the repo for the first time; MemGPT/Letta handle the agent's _own_ memory across chats; CrewAI/AutoGen coordinate multiple agents. They stack.

## Roadmap

- **v0.2.0** — Hardening (binary/encoding safety, concurrency, schema versioning, trust-boundary checks). Tracks internal `agent-context-hardening` work once real-world validated.
- Broader agent family testing (Gemini, Cursor) on route-trusting / route-verifying taxonomy.
- Pip packaging (`pip install agent-context`).
- Windows support.
- CI templates for CircleCI, Jenkins, GitLab.
- Ablation data isolating navigation contribution from harness and engineering.

See [GitHub issues](https://github.com/cote-star/agent-context/issues) for current scope.

## Go Deeper

| If you need... | Go here |
|---|---|
| The three-layer model in detail | [`docs/architecture.md`](docs/architecture.md) |
| The 16 design principles behind pack structure | [`docs/design-principles.md`](docs/design-principles.md) |
| CI adaptation guidance | [`docs/ci-adaptation.md`](docs/ci-adaptation.md) |
| The three-way sync policy | [`docs/SYNC.md`](docs/SYNC.md) |
| Research narrative + blog post | [explorable-recall on Substack](https://yourname.substack.com/p/explorable-recall) |
| Research paper | [arXiv:TBD](https://arxiv.org/abs/TBD) |
| Companion tooling for multi-agent work | [agent-chorus](https://github.com/cote-star/agent-chorus) |
| Research repo (experiments + graded runs) | [agent-recall](https://github.com/cote-star/agent-recall) |

---

Found a bug or have a feature idea? [Open an issue](https://github.com/cote-star/agent-context/issues). Ready to contribute? See [`CONTRIBUTING.md`](CONTRIBUTING.md) — the default path for template and script changes is a PR against the canonical source first; see [`docs/SYNC.md`](docs/SYNC.md).
