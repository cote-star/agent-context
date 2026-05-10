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

**Question:** "`tests/test_skill_sync.py` is failing on CI — what diverged and how do I fix it?"

**Pack-only diagnosis plan (from `30_BEHAVIORAL_INVARIANTS.md` invariant 1 + `20_CODE_MAP.md` Quick Lookup Shortcuts + `40_OPERATIONS_AND_RELEASE.md` Validation Commands):**

The pack flags this failure mode by name: "Template drift — `tests/test_skill_sync.py` fails; `init` copies a stale template — Edit to `templates/` not mirrored to `skills/agent-context/templates/` (forgot `scripts/sync-from-canonical.sh`)."

Investigation steps (in this order):
1. Read what `tests/test_skill_sync.py` compares: byte-equality between `templates/` ↔ `skills/agent-context/templates/`, `tools/` ↔ `skills/agent-context/tools/`, and `SKILL.md` ↔ `skills/agent-context/SKILL.md`.
2. Run `git diff --stat templates/ skills/agent-context/templates/` to see which file diverged.
3. Run `scripts/sync-from-canonical.sh` to mirror the canonical onto the skill copy.
4. Re-run: `python3 -m unittest tests.test_skill_sync` — must pass.
5. Commit the mirror update together with the canonical edit.

**Source verification:** The pack named the root cause and the fix directly without requiring source-tree exploration. Verified by reading `tests/test_skill_sync.py:35` (the assertion: "Update one to match the other so the installable skill stays in sync") and `tests/test_skill_sync.py:54` ("templates/ file lists differ between repo root and the installable skill").

| Metric | Value |
|---|---|
| Pack pointed to correct subsystem? | yes (`scripts/sync-from-canonical.sh` + `tests/test_skill_sync.py`) |
| Pack avoided dead ends? | yes (no exploration into `bin/`, `scripts/experiments/`, or the runtime needed) |
| Files opened to verify | 1 (`tests/test_skill_sync.py`) |
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

**Iterations:** 2 pack-content corrections before all tests passed.

1. Invariant #2 originally listed `RELEASE_NOTES.md` as test-enforced, but `tests/test_version_drift.py` actually enforces `README.md` (badge URL). Updated `00_START_HERE.md`, `20_CODE_MAP.md`, `30_BEHAVIORAL_INVARIANTS.md`, `40_OPERATIONS_AND_RELEASE.md`, `routes.json`, and `completeness_contract.json`. Test 2 then passed.

2. After publishing the v2 hand-authored HTML deck, every Marp reference in the pack (high-impact path #11, `Edit deck` route, "Marp frontmatter on line 1" invariant, `npx marp-cli` validation command) became stale. Updated `00_START_HERE.md`, `10_SYSTEM_OVERVIEW.md`, `20_CODE_MAP.md`, `30_BEHAVIORAL_INVARIANTS.md`, `40_OPERATIONS_AND_RELEASE.md`, and replaced Test 4's diagnosis question (Marp frontmatter → skill-sync drift). Test 4 then passed against the new diagnosis path.
