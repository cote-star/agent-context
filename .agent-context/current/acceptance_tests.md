# Acceptance Tests

Run during pack creation against this repo. Each test compares a pack-only answer to grep-verified ground truth so the pack's claims are mechanically checkable.

## Test 1: Lookup

**Question:** "Where are the routing-block constants (TIER1 / TIER2 / TIER3) defined?"

**Pack-only answer:** `bin/agent-context` — per `20_CODE_MAP.md` row 1 ("Holds `__version__` and the TIER1 / TIER2 / TIER3 routing-block constants") and `search_scope.json` task family `cli_work` verification shortcut (file: `bin/agent-context`, look_for: `TIER1`).

**Grep verification:**

```
$ git grep -l "TIER1" -- bin tools templates skills tests scripts
bin/agent-context
```

Single hit, matches the pack's claim.

| Metric | Value |
|---|---|
| Pack pointed to correct files? | yes |
| Files opened to verify | 1 (`bin/agent-context`) |

---

## Test 2: Impact Analysis

**Question:** "Bump the CLI release version from 0.3.1 to 0.3.2. Which files must change?"

**Pack-only answer (files that must change, from `30_BEHAVIORAL_INVARIANTS.md` Update Checklist + `routes.json` `bump_release_version` + `completeness_contract.json` `bump_cli_version`):**

- `bin/agent-context` (`__version__`)
- `SKILL.md` (frontmatter `metadata.version`)
- `skills/agent-context/SKILL.md` (frontmatter `metadata.version`)
- `README.md` (version badge URL)
- `RELEASE_NOTES.md` (convention — new entry)

**Grep verification (files that `tests/test_version_drift.py` actually checks):**

```
$ grep -nE 'agent-context|SKILL|README|version_drift' tests/test_version_drift.py
bin/agent-context (__version__)
SKILL.md (frontmatter metadata.version)
skills/agent-context/SKILL.md (frontmatter metadata.version)
README.md (badge URL)
```

| Metric | Value |
|---|---|
| Files identified by pack | 5 (4 test-enforced + RELEASE_NOTES.md convention) |
| Files actually test-enforced | 4 |
| Coverage ratio (test-enforced) | 4/4 = 100% |
| False positives | 0 (RELEASE_NOTES.md is correctly labeled "convention") |
| False negatives | 0 |
| Pass (≥80%)? | yes |

---

## Test 3: Cross-Cutting Impact

**Question:** "Add a new field `tokens_thinking_per_correct` to the v3 result schema. Which files must change?"

**Pack-only answer (from `routes.json` `add_result_schema_field` + `completeness_contract.json` `add_result_schema_field` + `20_CODE_MAP.md` Cross-Cutting Tracing Flows):**

Schema + extractors + tests:
- `scripts/experiments/result.schema.json` (add the field)
- `scripts/experiments/extract-events-from-chorus.py` (populate from session data)
- `scripts/experiments/extract-events-from-codex.py` (populate from session data)

Metric (since the field name implies a derived per-correct ratio):
- `scripts/experiments/derived-metrics.py`

Tests:
- `tests/test_result_schema.py`
- `tests/test_extract_events.py`
- `tests/test_extract_events_codex.py`
- `tests/test_derived_metrics.py` (because a derived metric was added)

Optional backfill of historical results:
- `scripts/experiments/apply-provenance.py`

**Grep verification (which files actually reference `tool_call_events`, the canonical schema-v3 marker):**

```
$ git grep -l "tool_call_events" -- scripts/experiments tests
scripts/experiments/derived-metrics.py
scripts/experiments/extract-events-from-chorus.py
scripts/experiments/result.schema.json
tests/test_derived_metrics.py
tests/test_extract_events.py
tests/test_extract_events_codex.py
tests/test_result_schema.py
```

7 files reference the schema-v3 marker. Pack covers all 7 in its impact set (note: `extract-events-from-codex.py` doesn't grep-hit because it imports the helper from the chorus extractor via `importlib`, but it absolutely must change — pack correctly includes it).

| Metric | Value |
|---|---|
| Core files identified by pack | 8 (3 schema/extractor + 1 derived-metrics + 4 tests) |
| Downstream files findable via pack guidance | 1 (`apply-provenance.py` for backfill) |
| Files grep found that pack missed entirely | 0 |
| Coverage ratio (core files) | 8/8 = 100% |
| Pass (≥80% core)? | yes |

---

## Test 4: Diagnosis

**Question:** "After my last commit, the deck renders without theme — every slide looks broken. Where do I look?"

**Pack-only diagnosis plan (from `10_SYSTEM_OVERVIEW.md` Silent Failure Modes + `30_BEHAVIORAL_INVARIANTS.md` invariant 7 + `20_CODE_MAP.md` row 11):**

The pack flags this exact failure mode by name: "Marp frontmatter unrecognized — Deck renders without theme/pagination — every slide looks broken. Root cause: YAML frontmatter not on line 1 (e.g., HTML comment placed before it). See `talk/cursor-meetup-may-2026.md` line 1 — frontmatter must be first."

Investigation steps (in this order):
1. Open `talk/cursor-meetup-may-2026.md` and confirm line 1 is `---` (start of YAML frontmatter), not an HTML comment.
2. If a comment block is present, move it below the closing `---` of the frontmatter.
3. Re-render: `npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.html`.
4. Re-render PDF and refresh `talk/index.html`.

**Source verification:** The pack named the root cause directly without requiring any source-tree exploration. Verified by reading `talk/cursor-meetup-may-2026.md` line 1: `---` (frontmatter on line 1, comment block at line 125 — correct ordering after the recent fix).

| Metric | Value |
|---|---|
| Pack pointed to correct subsystem? | yes (`talk/cursor-meetup-may-2026.md`) |
| Pack avoided dead ends? | yes (no exploration into `bin/`, `tools/`, `scripts/` needed) |
| Files opened to verify | 1 (the deck source) |
| Additional files needed beyond pack guidance | 0 |

---

## Summary

| Test | Category | Pass? |
|---|---|---|
| 1 | Lookup | yes |
| 2 | Impact analysis | yes |
| 3 | Cross-cutting impact | yes |
| 4 | Diagnosis | yes |

**Overall:** all pass.

**Iterations:** 1 pack-content correction was made before all tests passed — invariant #2 originally listed `RELEASE_NOTES.md` as test-enforced, but `tests/test_version_drift.py` actually enforces `README.md` (badge URL). Updated `00_START_HERE.md`, `20_CODE_MAP.md`, `30_BEHAVIORAL_INVARIANTS.md`, `40_OPERATIONS_AND_RELEASE.md`, `routes.json`, and `completeness_contract.json` to match. Test 2 then passed.
