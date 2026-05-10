# Code Map

## High-Impact Paths

| # | Path | What it does | Why it matters | Risk | Authority |
|---|---|---|---|---|---|
| 1 | `bin/agent-context` | CLI dispatch (argparse) for `init`, `verify`, `doctor`, `freshness`, `install-hook`. Holds `__version__` and the TIER1 / TIER2 / TIER3 routing-block constants. | Every operator command flows through here. Version drift starts here. | HIGH | authoritative |
| 2 | `tools/verify_agent_context.py` | Structural validator: required-files-per-tier, JSON schema, glob existence, template-marker scan. | The gate that lets a pack into CI. Rules added here propagate to every consumer. | HIGH | authoritative |
| 3 | `templates/` (11 files) | Canonical pack scaffold: 5 markdown + 5 JSON + `acceptance_tests.md`. | What `init` copies into target repos. The shape of every published pack. | HIGH | authoritative |
| 4 | `skills/agent-context/templates/` (11 files) | Mirror of `templates/` for the installable skill (`~/.claude/skills/agent-context/`). | What skill consumers see. Must stay byte-equivalent to `templates/`. | HIGH | derived (synced from `templates/`) |
| 5 | `SKILL.md` + `skills/agent-context/SKILL.md` | The 10-step fill flow the agent runs after `init`. | How agents actually fill the templates. | HIGH | authoritative (top) / derived (skill copy) |
| 6 | `scripts/experiments/result.schema.json` | v3 result schema: `tool_call_events`, `source_read_events`, `unique_source_paths_read`, ground-truth path arrays, provenance split. | Every Q2 2026 rerun number flows through this contract. Adding/removing a field is a cross-cutting change. | HIGH | authoritative |
| 7 | `scripts/experiments/derived-metrics.py` | Computes 28 metrics per cell. Discovers both 4-level and 5-level result paths; honors `<repo>/.skipped` markers. | Every public metric in the deck and `docs/evidence/` is computed here. | HIGH | authoritative |
| 8 | `scripts/experiments/extract-events-from-chorus.py`, `extract-events-from-codex.py` | Session JSONL → schema-v3 event streams. Per-task segmentation via Write/Edit-to-`<task>.json` boundaries. | Extraction is the bottleneck for telemetry; bugs here silently corrupt all downstream metrics. | HIGH | authoritative |
| 9 | `tools/check_freshness.sh` | `git diff <base>..HEAD` against `CONTEXT_RELEVANT_PATHS`; advisory exit. | Drives the "stale-pack" advisory and the pre-push hook. | MEDIUM | authoritative |
| 10 | `.github/workflows/ci.yml` | Runs unittest suite + verify on `examples/hello-service` and `examples/agent-chorus-reference`. | Merge blocker for every PR. | HIGH | authoritative |
| 11 | `talk/cursor-meetup-may-2026.md` | Marp source for the 21-slide meetup deck. Cream theme. **YAML frontmatter must be on line 1**, otherwise the entire render breaks. | The deck. HTML/PDF/index.html are derived. | MEDIUM | authoritative; HTML/PDF derived |
| 12 | `examples/hello-service/` | Small Python demo service + filled tier-3 pack. | CI verify smoke; acts as the live "what does a filled pack look like" example. | MEDIUM | authoritative |
| 13 | `examples/agent-chorus-reference/` | Reference filled tier-3 pack from a real agent-chorus seal. | Shows what a richer pack looks like; CI verifies it on every PR. | LOW | reference |

## Quick Lookup Shortcuts

| Question | Answer |
|---|---|
| Where are CLI subcommands wired? | `bin/agent-context` — single argparse block; subparsers for init / verify / doctor / freshness / install-hook |
| Where are tier defaults defined? | `bin/agent-context` — the `TIER1`/`TIER2`/`TIER3` constants and `tier_files()` mapping; tier-3 = 11 files |
| Where is the result schema? | `scripts/experiments/result.schema.json` (current: v3) |
| Which tests cover the verifier? | `tests/test_verify.py` (happy path + tier matrix), `tests/test_verifier_failures.py` (negative cases) |
| Where is the version pinned? | Four test-enforced surfaces: `bin/agent-context` (`__version__`), `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter, `README.md` (badge URL `badge/version-X.Y.Z-...`). Drift is enforced by `tests/test_version_drift.py`. `RELEASE_NOTES.md` is convention, not test-enforced. |
| Where do template edits go first? | `templates/<file>`. Then run `scripts/sync-from-canonical.sh` to mirror to `skills/agent-context/templates/<file>`. |
| Where does the agent fill flow live? | `SKILL.md` (10 steps); the skill copy is at `skills/agent-context/SKILL.md`. |
| Where are CI workflows? | `.github/workflows/ci.yml`, `release.yml`, `deploy-pages.yml` |
| What's the ground-truth file format? | Markdown with `### TASK_ID — Title` headers and a `Required citations:` bullet list. Parser: `scripts/experiments/parse-ground-truth.py`. |
| Where are derived metrics computed? | `scripts/experiments/derived-metrics.py` — 28 metrics, glob-discovers result JSONs, filters archive subdirs by name pattern. |
| How is per-task segmentation done in extractors? | `extract-events-from-chorus.py` and `extract-events-from-codex.py` use `Write`/`Edit`-to-`<task>.json` boundaries to split one cell-level event stream across the 6 tasks. |
| Where do tests live? | `tests/test_*.py` — 13 test files, plus `tests/_helpers.py` and `tests/__init__.py`. unittest, no third-party deps. |
| Where is the deck source? | `talk/cursor-meetup-may-2026.md` (Marp). Re-render: `npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.html` (and `.pdf` with `--allow-local-files`); then `cp talk/cursor-meetup-may-2026.html talk/index.html`. |
| Where is the canonical-vs-skill sync contract? | `scripts/sync-from-canonical.sh` (the script) + `docs/SYNC.md` (the contract) + `tests/test_skill_sync.py` (enforcement). |
| What does each top-level doc cover? | `docs/architecture.md` (toolchain shape), `docs/getting-started.md` (operator quickstart), `docs/ci-adaptation.md` (how to wire this into existing CI), `docs/design-principles.md` (the why), `docs/roadmap.md` (next), `docs/SYNC.md` (canonical/skill sync). |
| Where does the freshness `CONTEXT_RELEVANT_PATHS` get tuned? | Operator-supplied at invocation time. For *this* repo, see `40_OPERATIONS_AND_RELEASE.md`. |

## Cross-Cutting Tracing Flows

### Bump release version

1. Edit `bin/agent-context` — update the `__version__` string.
2. Edit `SKILL.md` — update the frontmatter `metadata.version` field.
3. Edit `skills/agent-context/SKILL.md` — same `metadata.version` (mirror).
4. Edit `README.md` — bump the version badge URL `badge/version-X.Y.Z-...`.
5. Update `RELEASE_NOTES.md` — add a top entry under the new version heading (convention).
6. Run `python3 -m unittest tests.test_version_drift` — must pass.
7. Run the full suite: `python3 -m unittest discover -s tests -v`.
8. Commit, tag `vX.Y.Z`, push.

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
2. Run `scripts/sync-from-canonical.sh` — mirrors the change to `skills/agent-context/templates/<file>`.
3. Run `python3 -m unittest tests.test_skill_sync` — must pass.
4. Run `python3 -m unittest tests.test_init_tiers` — exercises tier-1/2/3 init flows against the new templates.
5. If the change affects what the verifier accepts, add coverage in `tests/test_verify.py` and `tests/test_verifier_failures.py`.

### Add a new agent extractor

1. Create `scripts/experiments/extract-events-from-<agent>.py` — mirror the chorus/codex shape (events → schema-v3).
2. Add `tests/test_extract_events_<agent>.py` — copy the structure of `tests/test_extract_events_codex.py`.
3. Run `python3 -m unittest tests.test_extract_events_<agent>`.
4. Update `scripts/experiments/derived-metrics.py` only if the new agent introduces a metric variant.

### Edit the deck

1. Edit `talk/cursor-meetup-may-2026.md`. **Keep the YAML frontmatter on line 1.**
2. Re-render: `npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.html`.
3. Re-render PDF: `npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.pdf --allow-local-files`.
4. Refresh `talk/index.html`: `cp talk/cursor-meetup-may-2026.html talk/index.html`.
5. Commit all four artifacts together.

## Extension Recipe

**Add a new derived metric.**

1. Define the metric in `scripts/experiments/derived-metrics.py` — write a helper function that takes a cell's events list and returns the metric value, then register it in the cell-level dict produced by `compute_derived_metrics()`.
2. Document which schema-v3 fields the metric consumes (e.g., `tool_call_events[*].name`, `source_read_events[*].path`).
3. Add a unit test in `tests/test_derived_metrics.py` — synthesize a minimal cell input and assert the metric value.
4. Run `python3 -m unittest tests.test_derived_metrics -v`.
5. Re-run derived-metrics across any existing rerun output if the metric should backfill.
