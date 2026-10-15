# agent-context — Agent Context

**MANDATORY before starting work.** Complete the applicable read order before opening repo source files.

## Fast Facts

| Field | Value |
|---|---|
| Product | `agent-context` — installable agent-context skill + stdlib CLI for authoring, verifying, and maintaining checked-in `.agent-context/` packs in a target repo |
| Languages | Python 3 (CLI + verifier — stdlib only, no runtime deps), Bash (freshness gate, hooks, experiments lane runners) |
| Package manager | None (Python stdlib + Bash). The public `talk/` surface is hand-authored HTML served by GitHub Pages; completed-talk PDFs, render scripts, runbooks, and recordings live only in ignored `talk/_archive-local/`. |
| Quality gate | `python3 -m unittest discover -s tests -v`; `bin/agent-context verify <repo>` against the bundled examples; `tools/check_freshness.sh` (advisory) |
| Core risk | Drift between canonical `templates/` + `tools` + `SKILL.md` and their bundled/package copies — copying public root files into `skills/agent-context/` keeps mirrors aligned, `tests/test_skill_sync.py` enforces. Version drift across `agent_context/cli.py` `__version__`, `pyproject.toml`, `SKILL.md` frontmatter, `skills/agent-context/SKILL.md` frontmatter, and the `README.md` version badge URL is enforced by `tests/test_version_drift.py`. |
| Version | Pinned in `agent_context/cli.py` (`__version__`), `pyproject.toml`, `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter, and `README.md` (`![Version]...badge/version-X.Y.Z-...`). Currently 0.5.1. `RELEASE_NOTES.md` carries the human-facing release log (convention, not test-enforced). |

## Scope Rule

This pack covers the agent-context toolchain itself: the installable skill, the CLI, the verifier, the freshness gate, the canonical templates, the public experiment scripts, public docs/evidence, the meetup deck, and the example packs. It does NOT cover gitignored local benchmark plans, harness setup, reviewer-only ground truth, raw rerun storage, or deleted/private talk working artifacts — that content is intentionally not part of the published artifact.

## Read Order

1. This file and `30_BEHAVIORAL_INVARIANTS.md`.
2. Select the task in `routes.json`, follow its read order and relevant named patterns.
3. Load `completeness_contract.json`, `search_scope.json` and `reporting_rules.json`.
4. Consult `20_CODE_MAP.md` before source inspection and search only inside the scoped directories.

## Stop Rules

Before opening any source file, check whether your answer is already in the pack:

- "Where is X configured?" → `20_CODE_MAP.md` Quick Lookup Shortcuts
- "What files change for Y?" → `30_BEHAVIORAL_INVARIANTS.md` Update Checklist
- "How do I validate Z?" → `40_OPERATIONS_AND_RELEASE.md`
- "What is the runtime shape?" → `10_SYSTEM_OVERVIEW.md`
- "Which task type am I doing?" → `routes.json`
- "Where am I allowed to grep?" → `search_scope.json`
- "What must my answer include?" → `completeness_contract.json`

If the pack answers your question, do not open additional files. If it does not, use `search_scope.json` to bound your search.

## Not Covered in Detail

- `examples/hello-service/` and `examples/agent-chorus-reference/` — listed in `20_CODE_MAP.md` but not deeply unpacked here. They are reference packs, not toolchain code. Open them only when you need to see what a filled pack looks like.
- `docs/evidence/figures/` and `docs/visuals/` images (PNG/SVG) — rendered artifacts, not source-of-truth.
- `talk/index.html` is the live GitHub Pages target and currently mirrors `talk/claude-dev-day-jun-2026.html`.
- `talk/claude-dev-day-jun-2026.html` is the completed Claude Community Meetup edition.
- `talk/cursor-meetup-may-2026.html` is the completed Cursor Meetup edition.
- PDFs, speaker guides, render helpers, demo runbooks, recordings, and audio work are archived locally under ignored `talk/_archive-local/`.
- `talk/LinkedIN_QR.JPG` and `talk/amit_passport.jpeg` are public speaker assets used by the deck, not source-of-truth for the toolchain.
