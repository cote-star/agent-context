# System Overview

## Product Shape

`agent-context` is an authoring + verification toolchain for *checked-in* repo evidence that any coding agent (Cursor, Claude Code, Codex CLI, Gemini, OpenCode) can consume before editing source. It ships five surfaces from one source-of-truth:

1. A **CLI** (`bin/agent-context`) — Python 3 stdlib, no runtime deps. Subcommands: `init`, `verify`, `freshness`, `doctor`, `install-hook`.
2. An **installable Claude skill** (`SKILL.md` + `skills/agent-context/`) — the fill flow the agent runs after `init`.
3. **Canonical templates** (`templates/`, 11 files for tier 3) that `init` copies into the target repo's `.agent-context/current/`.
4. An **experiments harness** (`scripts/experiments/`) for the Q2 2026 multi-agent rerun: bare vs `structured_fresh` clones × 4 model variants × 6 repos × 6 tasks, with extractors, derived-metrics, ground-truth parser, and an LLM-judge dispatcher.
5. A **meetup deck** (`talk/cursor-meetup-may-2026.md`) plus rendering pipeline.

## Runtime Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  1. operator: bin/agent-context init --tier 3 <repo>                          │
│     └── copies templates/ → <repo>/.agent-context/current/                    │
│     └── writes routing block in CLAUDE.md / AGENTS.md / GEMINI.md / .cursorrules│
│                                                                                │
│  2. agent: reads SKILL.md → enumerates subsystems via git ls-files →           │
│            fills 11 templates → verifies globs against real files              │
│                                                                                │
│  3. operator: bin/agent-context verify <repo>                                  │
│     └── tools/verify_agent_context.py: structural + JSON schema + glob checks │
│                                                                                │
│  4. operator: bin/agent-context freshness <repo>                               │
│     └── tools/check_freshness.sh: git diff base..HEAD vs CONTEXT_RELEVANT_PATHS│
│                                                                                │
│  5. CI: .github/workflows/ci.yml runs unittest + verify on bundled examples    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Subsystems

| Subsystem | Entry point | Main implementation | Data / external dep |
|---|---|---|---|
| CLI | `bin/agent-context` | argparse subcommands; copies templates; invokes verifier and freshness | Python stdlib |
| Verifier | `tools/verify_agent_context.py` | structural checks · JSON schema · glob existence · template-marker scan | json / glob (stdlib) |
| Freshness gate | `tools/check_freshness.sh` | `git diff <base>..HEAD` vs `CONTEXT_RELEVANT_PATHS`; advisory exit | bash, git |
| Pre-push hook | `tools/pre-push-hook.sh` | advisory wrapper around freshness for pre-push | bash |
| Skill (top-level) | `SKILL.md` | 10-step instructions for the agent fill flow | n/a |
| Skill (installable) | `skills/agent-context/SKILL.md` + `skills/agent-context/{templates,tools,agents}/` | mirror of top-level for `~/.claude/skills/` install | synced from canonical via `scripts/sync-from-canonical.sh` |
| Templates (canonical) | `templates/*.md`, `templates/*.json` | 11-file tier-3 scaffold | source-of-truth for both copies |
| Experiments harness | `scripts/experiments/{*.py,*.sh}` + `result.schema.json` | bare vs `structured_fresh` runs, schema-v3 extractors, derived-metrics, judge dispatcher | bash + python stdlib |
| Tests | `tests/test_*.py` (13 files) + `_helpers.py` | unittest, no third-party deps | unittest (stdlib) |
| Talk | `talk/cursor-meetup-may-2026.md` (Marp source) → `.html` / `.pdf` / `index.html` | 21-slide cream-theme deck + supporting docs | npx marp-cli (render-only) |
| CI | `.github/workflows/{ci,release,deploy-pages}.yml` | unit suite + verify on examples + GitHub Pages deploy | github actions |

## Silent Failure Modes

| Failure | Symptom | Root cause |
|---|---|---|
| Template drift | `tests/test_skill_sync.py` fails; `init` copies a stale template | Edit to `templates/` not mirrored to `skills/agent-context/templates/` (forgot `scripts/sync-from-canonical.sh`) |
| Version drift | `tests/test_version_drift.py` fails | Bumped one of `bin/agent-context`, `SKILL.md`, `skills/agent-context/SKILL.md`, `RELEASE_NOTES.md` without the others |
| Verifier passes but pack is wrong | CI green; agents still fail tasks | `acceptance_tests.md` not iterated — verifier checks structure, not semantic correctness |
| Freshness false-positive | Every commit triggers a stale-pack warning | `CONTEXT_RELEVANT_PATHS` declared too broad in operator's freshness invocation |
| Schema/extractor drift | `derived-metrics.py` returns `null` for a metric across all cells | New field added to `result.schema.json` but not populated by the relevant extractor |
| Marp frontmatter unrecognized | Deck renders without theme/pagination — every slide looks broken | YAML frontmatter not on line 1 (e.g., HTML comment placed before it). See `talk/cursor-meetup-may-2026.md` line 1 — frontmatter must be first. |

## Command / API Surface

| Command | Purpose |
|---|---|
| `agent-context init [--tier {1,2,3}] [--force] [--install-hook] <path>` | Copy templates into `<path>/.agent-context/current/`; write routing blocks in CLAUDE/AGENTS/GEMINI/.cursorrules |
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
| `talk/` | 11 | meetup deck source + renders + supporting docs (excludes `talk/archive/` items) |
| `examples/hello-service/.agent-context/current/` | 8 | demo pack used by the CI verify smoke |
| `docs/` (top-level *.md) | 6 | architecture · ci-adaptation · design-principles · getting-started · roadmap · SYNC |
| `docs/evidence/figures/` | 6 | rendered evidence figures (3 svg + 3 png) |
| `docs/visuals/` | 5 | deck/diagram visuals (svg) |
| `examples/hello-service/src/` | 4 | demo Python service (config, server, main, init) |
| `docs/demos/` | 4 | demo svgs (init/verify/cold-start/two-panel) |
| `tools/` | 3 | canonical verifier + freshness + pre-push hook |
| `skills/agent-context/tools/` | 3 | mirror of `tools/` |
| `.github/workflows/` | 3 | ci.yml · release.yml · deploy-pages.yml |
| `bin/` | 1 | the CLI |
| `SKILL.md` | 1 | top-level skill instructions (also installed under `skills/agent-context/SKILL.md`) |
