# System Overview

## Product Shape

`agent-context` is an authoring + verification toolchain for *checked-in* system evidence that any coding agent (Cursor, Claude Code, Codex CLI, Gemini, OpenCode) can consume before acting. The developer venue emphasizes repo navigation, but the product framing is broader: portable context packs for systems whose operators need reliable recall, routes, contracts, and verification. It ships six surfaces from one source-of-truth:

1. An **installable agent-context skill** (`SKILL.md` + `skills/agent-context/`) — the preferred authoring workflow: ask an agent to build or refresh the pack, then review the diff.
2. A **CLI** (`agent_context/cli.py`, with `bin/agent-context` as a clone-use shim and `pyproject.toml` console-script entry point) — Python 3 stdlib, no runtime deps. Subcommands: `init`, `routing`, `verify`, `freshness`, `doctor`, `install-hook`, `install-skill`. The CLI scaffolds, verifies, checks freshness, installs hooks, and installs the bundled skill; it is not the primary authoring interface for filled content.
3. **Canonical templates** (`templates/`, 11 files for tier 3) that `init` copies into the target repo's `.agent-context/current/`.
4. An **experiments harness** (`scripts/experiments/`) for the Q2 2026 multi-agent rerun: bare vs `structured_fresh` clones × 4 agent/model lanes × 6 repos × 6 tasks = 288 graded tasks, with extractors, derived-metrics, ground-truth parser, and an LLM-judge dispatcher.
5. **Public docs/evidence** (`README.md`, `docs/getting-started.md`, `docs/evidence/`) that carry the skill-first onboarding path and Q2 2026 results.
6. **Completed meetup talk pages** (`talk/index.html`, `talk/claude-dev-day-jun-2026.html`, `talk/cursor-meetup-may-2026.html`) served by GitHub Pages; non-page support artifacts live only in ignored `talk/_archive-local/`.

## Runtime Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  1. operator: install/use the agent-context skill in an agent session          │
│     └── agent inspects the system, fills .agent-context/current/, and          │
│         explains the diff for review                                           │
│                                                                                │
│  2. optional scaffold: bin/agent-context init --tier 3 <repo>                  │
│     └── copies templates/ → <repo>/.agent-context/current/                    │
│     └── writes canonical AGENTS.md and a CLAUDE.md import; optional adapters│
│                                                                                │
│  3. agent: reads SKILL.md → enumerates subsystems via git ls-files →           │
│            fills 11 templates → verifies globs against real files              │
│                                                                                │
│  4. operator: bin/agent-context verify <repo>                                  │
│     └── tools/verify_agent_context.py: structural + JSON schema + glob checks │
│                                                                                │
│  5. operator: bin/agent-context freshness <repo>                               │
│     └── tools/check_freshness.sh: git diff base..HEAD vs CONTEXT_RELEVANT_PATHS│
│                                                                                │
│  6. CI: .github/workflows/ci.yml runs unittest + verify on bundled examples    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Subsystems

| Subsystem | Entry point | Main implementation | Data / external dep |
|---|---|---|---|
| CLI | `agent_context/cli.py`; `bin/agent-context` shim | argparse subcommands; copies templates; invokes verifier and freshness; installs bundled skill | Python stdlib |
| Verifier | `tools/verify_agent_context.py` | structural checks · JSON schema · glob existence · template-marker scan | json / glob (stdlib) |
| Freshness gate | `tools/check_freshness.sh` | `git diff <base>..HEAD` vs `CONTEXT_RELEVANT_PATHS`; advisory exit | bash, git |
| Pre-push hook | `tools/pre-push-hook.sh` | advisory wrapper around freshness for pre-push | bash |
| Skill (top-level) | `SKILL.md` | 10-step instructions for the agent fill flow | n/a |
| Skill (installable) | `skills/agent-context/SKILL.md` + `skills/agent-context/{templates,tools,agents}/` | mirror of top-level for `~/.claude/skills/` install | byte-copied from the public root files (`cp`); equality enforced by `tests/test_skill_sync.py` |
| Templates (canonical) | `templates/*.md`, `templates/*.json` | 11-file full-pack scaffold (tier 3, the only generation target; tiers 1-2 deprecated for `init`) | source-of-truth for both copies |
| Experiments harness | `scripts/experiments/{*.py,*.sh}` + `result.schema.json` | bare vs `structured_fresh` runs, schema-v3 extractors, derived-metrics, judge dispatcher | bash + python stdlib |
| Tests | `tests/test_*.py` (13 files) + `_helpers.py` | unittest, no third-party deps | unittest (stdlib) |
| Public docs/story | `README.md`, `docs/getting-started.md`, `docs/evidence/{metrics,results}.md`, `talk/README.md` | skill-first onboarding, experiment methodology/results, talk support notes | markdown |
| Talk | `talk/index.html`, `talk/claude-dev-day-jun-2026.html`, `talk/cursor-meetup-may-2026.html`, `talk/README.md`, speaker image assets | Completed live HTML pages + public speaker assets; support files archived locally under ignored `talk/_archive-local/` | GitHub Pages |
| CI | `.github/workflows/{ci,release,deploy-pages}.yml` | unit suite + verify on examples + GitHub Pages deploy | github actions |

## Silent Failure Modes

| Failure | Symptom | Root cause |
|---|---|---|
| Template drift | `tests/test_skill_sync.py` fails; `init` copies a stale template | Edit to `templates/` not copied over `skills/agent-context/templates/` (forgot the mirror `cp`) |
| Version drift | `tests/test_version_drift.py` fails | Bumped one of the 5 test-enforced surfaces (`agent_context/cli.py` `__version__`, `pyproject.toml`, `SKILL.md` frontmatter, `skills/agent-context/SKILL.md` frontmatter, `README.md` badge URL) without the others |
| Verifier passes but pack is wrong | CI green; agents still fail tasks | `acceptance_tests.md` not iterated — verifier checks structure, not semantic correctness |
| Freshness false-positive | Every commit triggers a stale-pack warning | `CONTEXT_RELEVANT_PATHS` declared too broad in operator's freshness invocation |
| Schema/extractor drift | `derived-metrics.py` returns `null` for a metric across all cells | New field added to `result.schema.json` but not populated by the relevant extractor |
| Deck/index drift | `talk/index.html` and `talk/claude-dev-day-jun-2026.html` show different content unintentionally | After editing the current live HTML, forgot to `cp talk/claude-dev-day-jun-2026.html talk/index.html`. Always refresh both together for live-page fixes. |
| Archived artifact drift | Local PDFs, speaker guides, demo notes, or recordings no longer match the live HTML | Completed-talk support artifacts are local archive material under ignored `talk/_archive-local/`; do not treat them as public source-of-truth. |

## Command / API Surface

| Command | Purpose |
|---|---|
| `agent-context init [--tier {1,2,3}] [--force] [--install-hook] <path>` | Copy templates into `<path>/.agent-context/current/` (tier 3 default; `--tier 1\|2` warn as deprecated, removed in 0.6.0); write canonical AGENTS.md plus a CLAUDE.md import (legacy layout is explicit) |
| `agent-context verify <path>` | Run `tools/verify_agent_context.py`: structure + JSON schema + glob existence + template-marker scan |
| `agent-context freshness <path> [--base-ref REF]` | Advisory `git diff` of `CONTEXT_RELEVANT_PATHS` vs the pack's commit anchor |
| `agent-context doctor` | Print Python version, CLI version, artifact status, environment notes |
| `agent-context install-hook [<path>]` | Copy `tools/pre-push-hook.sh` to `.git/hooks/pre-push` if no unmanaged hook exists |

## Tracked Path Density

| Directory | File count | Description |
|---|---|---|
| `scripts/experiments/` | 16 | Q2 2026 rerun harness (extractors, derived-metrics, judge, lane runners, schema) |
| `tests/` | 15 | unittest suite + `_helpers.py` + `__init__.py` |
| `templates/` | 11 | canonical tier-3 scaffold |
| `skills/agent-context/templates/` | 11 | mirror of `templates/` for the installable skill |
| `examples/agent-chorus-reference/` | 11 | reference filled tier-3 pack |
| `talk/` | 6 | live HTML pages + public talk README + speaker assets; support artifacts are local-only under ignored `talk/_archive-local/` |
| `examples/hello-service/.agent-context/current/` | 8 | demo pack used by the CI verify smoke |
| `docs/` (top-level *.md) | 6 | architecture · ci-adaptation · design-principles · getting-started · roadmap · SYNC |
| `docs/evidence/` | 2 | public methodology/results summary for the 288-task Q2 2026 rerun |
| `docs/evidence/figures/` | 6 | rendered evidence figures (3 svg + 3 png) |
| `docs/visuals/` | 5 | deck/diagram visuals (svg) |
| `examples/hello-service/src/` | 4 | demo Python service (config, server, main, init) |
| `docs/demos/` | 4 | demo svgs (init/verify/cold-start/two-panel) |
| `tools/` | 3 | canonical verifier + freshness + pre-push hook |
| `skills/agent-context/tools/` | 3 | mirror of `tools/` |
| `.github/workflows/` | 3 | ci.yml · release.yml · deploy-pages.yml |
| `bin/` | 1 | clone-use shim for the CLI |
| `agent_context/` | 5 | installable Python package module + bundled package-data links |
| `SKILL.md` | 1 | top-level skill instructions (also installed under `skills/agent-context/SKILL.md`) |
