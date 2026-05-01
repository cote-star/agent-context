# Release Notes

## v0.2.0 — 2026-05-01

Meetup-ready release. The pack is now fully self-contained with all three layers, a skill definition for agent-driven pack creation, and evidence materials from 78+ graded experiments.

### What's new

- **SKILL.md** — 10-step skill definition adapted from the production team-skills version. Agents can now autonomously create, update, and maintain packs by following the skill. Includes the subsystem inventory step (enumerate before narrate), acceptance test framework (4 tests with grep verification), and CI adaptation guidance.
- **Authority layer templates** — `routes.json`, `completeness_contract.json`, `reporting_rules.json` are now shipped as tier 3 templates. These give trust-and-follow agents (Claude, Gemini) authoritative guidance without needing the chorus CLI.
- **Tier support** — `agent-context init --tier 1|2|3 .` lets you choose adoption level:
  - Tier 1 (minimal): `20_CODE_MAP.md` + `search_scope.json` (2 files)
  - Tier 2 (standard): + start, invariants, manifest, acceptance tests (6 files)
  - Tier 3 (full, default): all 11 files including authority layer
- **Routing block generation** — `init` now creates managed routing blocks in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.cursorrules`. Blocks are tier-aware and use HTML comment sentinels for idempotent upsert.
- **Cursor integration** — `.cursorrules` is generated automatically with the search-and-verify routing pattern. Cursor reads this file natively.
- **Tool copying** — `init` copies `verify_context_pack.py` and `check_freshness.sh` into the target repo's `.agent-context/tools/` so packs are self-verifiable without agent-context installed.
- **Upgraded verifier** — tier-aware validation, authority layer contract checking (glob patterns match real files, no template variables), routing file validation, coverage heuristics.
- **Evidence materials** — figures from agent-recall research (asymmetry contrast, three-track framework, experiment results), metrics summary, full results breakdown, demo assets.
- **Real-world reference pack** — `examples/agent-chorus-reference/` shows a mature tier 3 pack from a 155-file dual-implementation CLI repo.
- **Getting started guide** — step-by-step quickstart for new users.
- **CI example workflow** — reference GitHub Actions job for PR gating.

### Breaking changes

- None. Tier 2 behavior matches v0.1.0 default. Existing packs validate without changes.

---

## v0.1.0 — 2026-04-20

Initial public release.

**Canonical source**: this repo is a distilled public view of the internal `team_skills/skills/agent-context/` skill. Updates flow from canonical to this repo via `scripts/sync-from-canonical.sh`. See `docs/SYNC.md`.

### What's included
- Content layer: 5 markdown templates (`00_START_HERE`, `10_SYSTEM_OVERVIEW`, `20_CODE_MAP`, `30_BEHAVIORAL_INVARIANTS`, `40_OPERATIONS_AND_RELEASE`) + `acceptance_tests.md`.
- Navigation layer: `search_scope.json` template.
- Validation: `verify_context_pack.py` + `check_freshness.sh` (stdlib-only Python + POSIX shell).
- Python CLI: `bin/agent-context init | verify | doctor | freshness`.
- Worked example: `examples/hello-service/` — small service with a filled pack; verify passes out of the box.
- Three-way sync policy + tooling: `scripts/sync-from-canonical.sh` + `docs/SYNC.md`.
