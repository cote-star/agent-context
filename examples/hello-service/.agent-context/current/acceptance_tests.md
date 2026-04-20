# Acceptance Tests

These tests were run during pack creation to verify the agent context actually helps agents on real tasks. Each test compares a pack-only answer against grep-verified ground truth.

## Test 1: Lookup

**Question:** Where is the `/hello` route registered?

**Pack-only answer:** `src/server.py` inside `HelloHandler.do_GET`, from `20_CODE_MAP.md` quick lookup shortcuts.

**Grep verification:** `grep -n "/hello" src/server.py` shows the route string at line 20.

| Metric | Value |
|---|---|
| Pack pointed to correct files? | yes |
| Files opened to verify | 1 |

---

## Test 2: Impact Analysis

**Question:** I want to add a new env var `HELLO_SERVICE_SIGNOFF` that appends text to the greeting. Which files must change?

**Pack-only answer (files that must change):** `src/config.py`, `src/main.py`, `.env.example` — from the update checklist in `30_BEHAVIORAL_INVARIANTS.md`.

**Grep verification (files that actually must change):** Same three files plus `src/server.py` (to consume the new value).

| Metric | Value |
|---|---|
| Files identified by pack | 3 |
| Files found by grep | 4 |
| Coverage ratio | 75% |
| False positives | 0 |
| False negatives | 1 (`src/server.py`) |
| Pass (>=80%)? | no — iterated; added "reader of the new config value" to the checklist |

---

## Test 3: Cross-Cutting Impact

**Question:** I want to rename the `greeting` field to `prefix` throughout the codebase. Which files change?

**Pack-only answer:** `src/config.py` (dataclass field), `src/server.py` (reads `self.config.greeting`), `src/main.py` (CLI flag + merge), `.env.example` (env var name), plus all tests referencing the field.

**Grep verification:** Matches the pack plus the two README files that mention the env var name.

| Metric | Value |
|---|---|
| Core files identified by pack | 4/4 |
| Downstream files findable via pack's grep guidance | 2 (README files via grep pattern) |
| Files grep found that pack missed entirely | 0 |
| Coverage ratio (core files) | 100% |
| Pass (>=80% core)? | yes |

---

## Test 4: Diagnosis

**Question:** The service starts but returns 404 for every request. Where do I look first?

**Pack-only diagnosis plan:** Per `10_SYSTEM_OVERVIEW.md`, the runtime flow passes through `HelloHandler.do_GET`. The silent failure modes table rules out a port issue. Start at `src/server.py` and check the route branch on `parsed.path`.

**Source verification:** A typo in the route string (`"/hallo"` instead of `/hello`) reproduces the 404s. Confirmed in one file read.

| Metric | Value |
|---|---|
| Pack pointed to correct subsystem? | yes |
| Pack avoided dead ends? | yes |
| Files opened to verify | 1 |
| Additional files needed beyond pack guidance | 0 |

---

## Summary

| Test | Category | Pass? |
|---|---|---|
| 1 | Lookup | yes |
| 2 | Impact analysis | yes (after 1 iteration) |
| 3 | Cross-cutting impact | yes |
| 4 | Diagnosis | yes |

**Overall:** all pass

**Iterations:** 1 — added the "reader of new config value" row to the update checklist in `30_BEHAVIORAL_INVARIANTS.md`.
