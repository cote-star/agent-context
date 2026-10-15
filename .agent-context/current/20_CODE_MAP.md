# Code Map

## High-Impact Paths

| # | Path | What it does | Why it matters | Risk | Authority |
|---|---|---|---|---|---|
| 1 | `agent_context/cli.py` | CLI dispatch (argparse) for `init`, `routing`, `verify`, `doctor`, `freshness`, `install-hook`, `install-skill`. Holds `__version__`, tier template lists, routing block templates, and package-data lookup. | Every packaged operator command flows through here. Version drift starts here. | HIGH | authoritative |
| 1a | `bin/agent-context` | Thin clone-use shim that prepends the repo root to `sys.path` and delegates to `agent_context.cli:main_cli`. | Keeps clone-based usage working without `pip install .`; not where CLI behavior lives. | LOW | shim |
| 2 | `tools/verify_agent_context.py` | Structural validator: required-files-per-tier, JSON schema, glob existence, template-marker scan. | The gate that lets a pack into CI. Rules added here propagate to every consumer. | HIGH | authoritative |
| 3 | `templates/` (11 files) | Canonical pack scaffold: 5 markdown + 5 JSON + `acceptance_tests.md`. | What `init` copies into target repos. The shape of every published pack. | HIGH | authoritative |
| 4 | `skills/agent-context/templates/` (11 files) | Mirror of `templates/` for the installable skill (`~/.claude/skills/agent-context/`). | What skill consumers see. Must stay byte-equivalent to `templates/`. | HIGH | derived (synced from `templates/`) |
| 5 | `SKILL.md` + `skills/agent-context/SKILL.md` | The 10-step fill flow the agent runs after `init`. | How agents actually fill the templates. | HIGH | authoritative (top) / derived (skill copy) |
| 6 | `scripts/experiments/result.schema.json` | v3 result schema: `tool_call_events`, `source_read_events`, `unique_source_paths_read`, ground-truth path arrays, provenance split. | Every Q2 2026 rerun number flows through this contract. Adding/removing a field is a cross-cutting change. | HIGH | authoritative |
| 7 | `scripts/experiments/derived-metrics.py` | Computes 28 metrics per cell. Discovers both 4-level and 5-level result paths; honors `<repo>/.skipped` markers. | Every public metric in the deck and `docs/evidence/` is computed here. | HIGH | authoritative |
| 8 | `scripts/experiments/extract-events-from-chorus.py`, `extract-events-from-codex.py` | Session JSONL → schema-v3 event streams. Per-task segmentation via Write/Edit-to-`<task>.json` boundaries. | Extraction is the bottleneck for telemetry; bugs here silently corrupt all downstream metrics. | HIGH | authoritative |
| 9 | `tools/check_freshness.sh` | `git diff <base>..HEAD` against `CONTEXT_RELEVANT_PATHS`; reports changed context paths and pack paths; advisory exit when invoked through the CLI. | Drives the "stale-pack" advisory and the pre-push hook. Diagnostics here are what adopters see in CI. | MEDIUM | authoritative |
| 10 | `.github/workflows/ci.yml` | Runs unittest suite + `bin/agent-context verify examples/hello-service`. | Merge blocker for every PR. | HIGH | authoritative |
| 11 | `README.md`, `docs/getting-started.md`, `docs/ci-adaptation.md` | Public onboarding story, practical setup, and CI adaptation. Current framing is skill-first: install/invoke the skill to author the pack; use the CLI to scaffold, verify, freshness-check, and install hooks. Private benchmark plans, harness drafts, raw runs, and reviewer-only ground truth stay local. | Primary user conversion and adoption path. Drift here directly changes how people create and gate packs. | HIGH | authoritative |
| 12 | `docs/evidence/metrics.md`, `docs/evidence/results.md` | Public methodology/results summary for the Q2 2026 rerun. Current headline set is 288 graded tasks across 48 cells, excluding one skipped repo that needs setup review. | Source for evidence claims in the README and deck. | HIGH | authoritative summary |
| 13 | `talk/index.html`, `talk/claude-dev-day-jun-2026.html`, `talk/cursor-meetup-may-2026.html` | Completed live HTML talk pages. `index.html` is the GitHub Pages target; the Claude and Cursor editions remain directly addressable. | Public talk surface. Support artifacts (PDFs, speaker guides, render scripts, demo runbooks, recordings) are local-only under ignored `talk/_archive-local/`. | MEDIUM | authoritative public pages |
| 14 | `examples/hello-service/` | Small Python demo service + filled tier-3 pack. | CI verify smoke; acts as the live "what does a filled pack look like" example. | MEDIUM | authoritative |
| 15 | `examples/agent-chorus-reference/` | Reference filled tier-3 pack from a real agent-chorus seal, stored flat rather than under `.agent-context/current/`. | Shows what a richer pack looks like; not a direct `bin/agent-context verify <path>` target. | LOW | reference |

## Quick Lookup Shortcuts

| Question | Answer |
|---|---|
| Where are CLI subcommands wired? | `agent_context/cli.py` — single argparse block; subparsers for init / verify / doctor / freshness / install-hook / install-skill |
| Where are tier defaults defined? | `agent_context/cli.py` — `TIER_1_TEMPLATES` / `TIER_2_TEMPLATES` / `TIER_3_TEMPLATES` and `TIER_MAP`; tier-3 = 11 files |
| Where is the result schema? | `scripts/experiments/result.schema.json` (current: v3) |
| Which tests cover the verifier? | `tests/test_verify.py` (happy path + tier matrix), `tests/test_verifier_failures.py` (negative cases) |
| Where is the version pinned? | Five test-enforced surfaces: `agent_context/cli.py` (`__version__`), `pyproject.toml`, `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter, `README.md` (badge URL `badge/version-X.Y.Z-...`). Drift is enforced by `tests/test_version_drift.py`. `RELEASE_NOTES.md` is convention, not test-enforced. |
| Where do template edits go first? | `templates/<file>`. Then copy the changed public canonical files into `skills/agent-context/templates/<file>`. |
| Where does the agent fill flow live? | `SKILL.md` (10 steps); the skill copy is at `skills/agent-context/SKILL.md`. |
| Where are CI workflows? | `.github/workflows/ci.yml`, `release.yml`, `deploy-pages.yml` |
| What's the ground-truth file format? | Markdown with `### TASK_ID — Title` headers and a `Required citations:` bullet list. Parser: `scripts/experiments/parse-ground-truth.py`. |
| Where are derived metrics computed? | `scripts/experiments/derived-metrics.py` — 28 metrics, glob-discovers result JSONs, filters archive subdirs by name pattern. |
| How is per-task segmentation done in extractors? | `extract-events-from-chorus.py` and `extract-events-from-codex.py` use `Write`/`Edit`-to-`<task>.json` boundaries to split one cell-level event stream across the 6 tasks. |
| Where do tests live? | `tests/test_*.py` — 13 test files, plus `tests/_helpers.py` and `tests/__init__.py`. unittest, no third-party deps. |
| Where is the skill-first onboarding story? | `README.md` and `docs/getting-started.md`; deck reinforcement lives in `talk/cursor-meetup-may-2026.html` around the setup/demo/CTA slides. |
| Where are the public Q2 2026 evidence claims? | `docs/evidence/metrics.md` and `docs/evidence/results.md`; deck/README claims should stay consistent with these summaries. |
| Where is the live talk page? | `talk/index.html` is the GitHub Pages target and currently mirrors `talk/claude-dev-day-jun-2026.html`. The completed Cursor edition remains at `talk/cursor-meetup-may-2026.html`. |
| Where is the canonical-vs-skill mirror contract? | Public root files (`SKILL.md`, `templates/`, `tools/`) are byte-copied into `skills/agent-context/`; `tests/test_skill_sync.py` enforces equality; `docs/SYNC.md` documents the policy. `scripts/sync-from-canonical.sh` imports an *external* private tree and is not the mirror step. |
| What does each top-level doc cover? | `docs/architecture.md` (toolchain shape), `docs/getting-started.md` (operator quickstart), `docs/ci-adaptation.md` (how to wire this into existing CI, including monorepos/generated paths/advisory mode), `docs/design-principles.md` (the why), `docs/roadmap.md` (next), `docs/SYNC.md` (canonical/skill sync). |
| Where does the freshness `CONTEXT_RELEVANT_PATHS` get tuned? | Operator-supplied at invocation time. For *this* repo, see `40_OPERATIONS_AND_RELEASE.md`. |

## Cross-Cutting Tracing Flows

### Bump release version

1. Edit `agent_context/cli.py` — update the `__version__` string.
2. Edit `pyproject.toml` — update `[project] version`.
3. Edit `SKILL.md` — update the frontmatter `metadata.version` field.
4. Edit `skills/agent-context/SKILL.md` — same `metadata.version` (mirror).
5. Edit `README.md` — bump the version badge URL `badge/version-X.Y.Z-...`.
6. Update `RELEASE_NOTES.md` — add a top entry under the new version heading (convention).
7. Run `python3 -m unittest tests.test_version_drift` — must pass.
8. Run the full suite: `python3 -m unittest discover -s tests -v`.
9. Commit, tag `vX.Y.Z`, push.

### Add a new field to `result.schema.json`

1. Edit `scripts/experiments/result.schema.json` — add the field under the appropriate object.
2. Edit `scripts/experiments/extract-events-from-chorus.py` — populate the field from session data.
3. Edit `scripts/experiments/extract-events-from-codex.py` — populate the field from session data.
4. If the field feeds a metric: add the computation in `scripts/experiments/derived-metrics.py`.
5. Update `tests/test_result_schema.py` — assert the new field is required/optional as designed.
6. Update `tests/test_extract_events.py` and `tests/test_extract_events_codex.py` — add an assertion that the extractor populates it.
7. (Optional) backfill old result JSONs via `scripts/experiments/apply-provenance.py`.

### Edit a canonical template

1. Edit `templates/<file>` (markdown or JSON).
2. Copy it over the mirror: `cp templates/<file> skills/agent-context/templates/<file>`.
3. Run `python3 -m unittest tests.test_skill_sync` — must pass.
4. Run `python3 -m unittest tests.test_init_tiers` — exercises the tier-3 default plus the deprecated tier-1/2 compatibility flows against the new templates.
5. If the change affects what the verifier accepts, add coverage in `tests/test_verify.py` and `tests/test_verifier_failures.py`.

### Add a new agent extractor

1. Create `scripts/experiments/extract-events-from-<agent>.py` — mirror the chorus/codex shape (events → schema-v3).
2. Add `tests/test_extract_events_<agent>.py` — copy the structure of `tests/test_extract_events_codex.py`.
3. Run `python3 -m unittest tests.test_extract_events_<agent>`.
4. Update `scripts/experiments/derived-metrics.py` only if the new agent introduces a metric variant.

### Edit live talk pages

1. Prefer typo/link fixes only; both talks are complete.
2. If the current public page changes, edit `talk/claude-dev-day-jun-2026.html`.
3. Refresh `talk/index.html`: `cp talk/claude-dev-day-jun-2026.html talk/index.html`.
4. Edit `talk/cursor-meetup-may-2026.html` only when fixing the archived public Cursor page directly.
5. Keep PDFs, speaker guides, render helpers, demo runbooks, recordings, and audio work in ignored `talk/_archive-local/`.

### Edit public onboarding or evidence claims

1. Edit `README.md` first for the product promise and setup path.
2. Edit `docs/getting-started.md` if the practical user flow changes.
3. Edit `docs/evidence/metrics.md` and/or `docs/evidence/results.md` if counts, methodology, exclusions, or headline numbers change.
4. If the talk repeats the claim, edit `talk/cursor-meetup-may-2026.html`, refresh `talk/index.html`, and re-render the PDF in the same commit.

## Extension Recipe

**Add a new derived metric.**

1. Define the metric in `scripts/experiments/derived-metrics.py` — write a helper function that takes a cell's events list and returns the metric value, then register it in the cell-level dict produced by `compute_derived_metrics()`.
2. Document which schema-v3 fields the metric consumes (e.g., `tool_call_events[*].name`, `source_read_events[*].path`).
3. Add a unit test in `tests/test_derived_metrics.py` — synthesize a minimal cell input and assert the metric value.
4. Run `python3 -m unittest tests.test_derived_metrics -v`.
5. Re-run derived-metrics across any existing rerun output if the metric should backfill.
