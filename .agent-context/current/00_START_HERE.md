# agent-context — Agent Context

**MANDATORY before starting work.** Do NOT open repo source files until steps 1-3 are complete.

## Fast Facts

| Field | Value |
|---|---|
| Product | `agent-context` — installable agent-context skill + stdlib CLI for authoring, verifying, and maintaining checked-in `.agent-context/` packs in a target repo |
| Languages | Python 3 (CLI + verifier — stdlib only, no runtime deps), Bash (freshness gate, hooks, experiments lane runners) |
| Package manager | None (Python stdlib + Bash). The `talk/` deck is hand-authored HTML; the PDF is rendered via headless Chrome from `talk/render-pdf.sh`. |
| Quality gate | `python3 -m unittest discover -s tests -v`; `bin/agent-context verify <repo>` against the bundled examples; `tools/check_freshness.sh` (advisory) |
| Core risk | Drift between canonical `templates/` + `tools/` + `SKILL.md` and their `skills/agent-context/` mirrors — `scripts/sync-from-canonical.sh` keeps them aligned, `tests/test_skill_sync.py` enforces. Version drift across `bin/agent-context` `__version__`, `SKILL.md` frontmatter, `skills/agent-context/SKILL.md` frontmatter, and the `README.md` version badge URL is enforced by `tests/test_version_drift.py`. |
| Version | Pinned in `bin/agent-context` (`__version__`), `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter, and `README.md` (`![Version]...badge/version-X.Y.Z-...`). Currently 0.3.1. `RELEASE_NOTES.md` carries the human-facing release log (convention, not test-enforced). |

## Scope Rule

This pack covers the agent-context toolchain itself: the installable skill, the CLI, the verifier, the freshness gate, the canonical templates, the experiments harness (Q2 2026 multi-agent rerun infrastructure), public docs/evidence, the meetup deck, and the example packs. It does NOT cover gitignored local rerun storage (`.agent-chorus/`, `experiments/`, `docs/experiments/`, `__pycache__/`) or deleted/private talk working artifacts — that content is intentionally not part of the published artifact.

## Read Order

1. This file (fast facts, scope, stop rules)
2. `10_SYSTEM_OVERVIEW.md`
3. `20_CODE_MAP.md` for navigation tasks · `30_BEHAVIORAL_INVARIANTS.md` for impact-analysis tasks
4. Then open source files as needed

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
- `talk/cursor-meetup-may-2026.html` is the deck source-of-truth (hand-authored HTML + CSS, deep-navy theme).
- `talk/index.html` is a byte-identical copy of `talk/cursor-meetup-may-2026.html` for GitHub Pages — refresh with `cp` after edits, never edit directly.
- `talk/cursor-meetup-may-2026.pdf` is rendered from the HTML via `talk/render-pdf.sh` (headless Chrome). Don't edit directly.
- `talk/LinkedIN_QR.JPG` and `talk/amit_passport.jpeg` are public speaker assets used by the deck, not source-of-truth for the toolchain.
