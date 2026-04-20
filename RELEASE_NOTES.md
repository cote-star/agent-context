# Release Notes

## v0.1.0 — 2026-04-17

Initial public release.

**Canonical source**: this repo is a distilled public view of the internal `team_skills/skills/agent-context/` skill. Updates flow from canonical to this repo via `scripts/sync-from-canonical.sh`. See `docs/SYNC.md`.

### What's included
- Content layer: 5 markdown templates (`00_START_HERE`, `10_SYSTEM_OVERVIEW`, `20_CODE_MAP`, `30_BEHAVIORAL_INVARIANTS`, `40_OPERATIONS_AND_RELEASE`) + `acceptance_tests.md`.
- Navigation layer: `search_scope.json` template.
- Validation: `verify_context_pack.py` + `check_freshness.sh` (stdlib-only Python + POSIX shell).
- Python CLI: `bin/agent-context init | verify | doctor | freshness`.
- Worked example: `examples/hello-service/` — small service with a filled pack; verify passes out of the box.
- Three-way sync policy + tooling: `scripts/sync-from-canonical.sh` + `docs/SYNC.md`.

### Coming in v0.2.0
- Hardening: binary/encoding safety, concurrency + atomic writes, schema versioning, trust-boundary checks, authoring ergonomics. Tracks the internal `agent-context-hardening` work once real-world validated.
- Broader agent family testing (Gemini, Cursor) on route-trusting / route-verifying taxonomy.
- Ablation data showing navigation contribution isolated from harness.

### Known not included (intentional)
- The **authority layer** (`routes.json`, `completeness_contract.json`, `reporting_rules.json`) is only shipped inside `agent-chorus` for Claude-style trust-and-follow agents coupled to chorus binary tooling.
- Pip packaging (`pip install agent-context`) — clone + run for now.
