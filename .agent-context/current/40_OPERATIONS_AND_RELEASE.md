# Operations and Release

## Validation Commands

| Command | What it checks | When to run |
|---|---|---|
| `python3 -m unittest discover -s tests -v` | Full unittest suite — CLI smoke, tier init, verifier (positive + negative), freshness, extractors, derived metrics, schema, ground-truth parser, run-agent-lane, skill sync, version drift | Every change to `bin/`, `tools/`, `templates/`, `skills/`, `scripts/experiments/` |
| `bin/agent-context verify examples/hello-service` | Tier-3 verify on the bundled demo pack | After template or verifier edits |
| `bin/agent-context doctor` | Python version, CLI version, bundled package-data status, verifier result, freshness summary, routing blocks, hook status | When debugging an operator issue |
| `tools/check_freshness.sh --base-ref origin/main` | Advisory freshness on the live working tree; prints changed context-relevant files and changed pack files | Before committing changes that touch CONTEXT_RELEVANT_PATHS |
| `scripts/sync-from-canonical.sh` | Mirrors `templates/`, `tools/`, `SKILL.md` into `skills/agent-context/` | After any edit to a canonical file |
| `cp talk/claude-dev-day-jun-2026.html talk/index.html` | Refresh the GitHub Pages target after editing the current live HTML page | After any current-page typo/link fix in `talk/claude-dev-day-jun-2026.html` |

## CI / Workflow Integration

- **Workflow file:** `.github/workflows/ci.yml` runs the unittest suite + verifies both example packs on every PR. `.github/workflows/release.yml` packages on tag push. `.github/workflows/deploy-pages.yml` rebuilds the `talk/` deck for GitHub Pages on every push to `main`.
- **Chosen `CONTEXT_RELEVANT_PATHS` (for this repo's own freshness checks):** `bin/`, `agent_context/`, `tools/`, `templates/`, `skills/`, `scripts/experiments/`, `tests/`, `SKILL.md`, `README.md`, `RELEASE_NOTES.md`, `docs/architecture.md`, `docs/ci-adaptation.md`, `docs/design-principles.md`, `docs/getting-started.md`, `docs/evidence/metrics.md`, `docs/evidence/results.md`, `docs/references/`, `talk/`. The README, evidence docs, CI guidance, and deck are product-facing surfaces for this repo, so story/methodology changes should trigger pack review even when runtime code is unchanged. Private benchmark plans, harness drafts, raw runs, and reviewer-only ground truth stay outside the tracked public surface.
- **Verifier command:** `bin/agent-context verify .` (operates on `<repo>/.agent-context/current/`).
- **Freshness mode:** advisory. Running `tools/check_freshness.sh` warns; the pre-push hook surfaces the warning; CI does not hard-block on freshness for this repo because the pack documents the toolchain itself — staleness manifests as docs drift, not runtime failure.
- **Rationale:** the verifier is the hard gate (it checks structure, schema, glob existence). Freshness is a soft gate that nudges authors to update the pack when changing CONTEXT_RELEVANT_PATHS.

## Release Flow

1. Bump `agent_context/cli.py` (`__version__`), `pyproject.toml` (`[project] version`), `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter (`metadata.version`), `README.md` (badge URL `badge/version-X.Y.Z-...`). Also add a `RELEASE_NOTES.md` entry under the new version heading (convention).
2. Run `python3 -m unittest discover -s tests -v` — must be green.
3. Run `bin/agent-context verify examples/hello-service` — must pass.
4. Commit with a clear release message (e.g., `vX.Y.Z: <one-line summary>`).
5. Tag: `git tag vX.Y.Z`. Push commit + tag: `git push origin main && git push origin vX.Y.Z`.
6. The `release.yml` workflow runs on the tag push and produces release artifacts.
7. The `deploy-pages.yml` workflow runs on the commit push and rebuilds the GitHub Pages deck (talk/).

## Environment / Operational Notes

- **Python:** stdlib-only. No `requirements.txt`, no virtualenv needed. CI uses the GitHub-Actions-default Python 3 (currently 3.12 family).
- **Bash:** `set -euo pipefail` patterns; tested on macOS and Ubuntu. The shell scripts in `scripts/experiments/` rely on `git`, `jq` (most), and standard POSIX tooling.
- **Talk pages:** the live public talk surface is hand-authored HTML (`talk/index.html`, `talk/claude-dev-day-jun-2026.html`, `talk/cursor-meetup-may-2026.html`) served by GitHub Pages. PDFs, render scripts, speaker guides, demo runbooks, recordings, and audio work are local-only archive material under ignored `talk/_archive-local/`.
- **Tests run:** locally on macOS dev workstations and on Ubuntu CI. They do not require network access. They do not require any agent CLI to be installed (no `claude`, `codex`, or `cursor-agent` invocations).
- **Experiments tooling:** the `scripts/experiments/` tooling is public reusable machinery for *operator-driven* multi-agent reruns. It does NOT run in CI — running an experiment requires private local plans, harness setup, reviewer-only ground truth, isolated clones of target repos, and raw run artifacts that are not part of the public docs surface.

## Agent-Context Maintenance

- **Update the pack when** adding a CLI subcommand, changing tier defaults, changing the skill-first authoring flow, adding a new agent extractor, shipping a new schema version, restructuring the experiments pipeline, or changing public README/deck/evidence claims.
- **Most-patched section:** `20_CODE_MAP.md` "High-Impact Paths" and "Quick Lookup Shortcuts" — refreshed whenever a new core file is added or an existing one's role shifts.
- **Less-patched but watch:** `30_BEHAVIORAL_INVARIANTS.md` "File Families" counts. Any new file under one of the listed globs invalidates the count. Re-verify with `git ls-files <glob> | wc -l` after structural changes.
- **`.agent-context/` lives in this repo's `main` branch** — same review path as code changes. PRs that change the pack should call out the rationale in the PR body.
- **Sync target:** if you update canonical templates, also bring `examples/hello-service/.agent-context/current/` up to date. Keep `examples/agent-chorus-reference/` useful as a flat reference snapshot, but do not treat it as a direct CLI verify target.
