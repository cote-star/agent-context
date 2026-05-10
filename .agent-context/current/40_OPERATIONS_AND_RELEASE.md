# Operations and Release

## Validation Commands

| Command | What it checks | When to run |
|---|---|---|
| `python3 -m unittest discover -s tests -v` | Full unittest suite — CLI smoke, tier init, verifier (positive + negative), freshness, extractors, derived metrics, schema, ground-truth parser, run-agent-lane, skill sync, version drift | Every change to `bin/`, `tools/`, `templates/`, `skills/`, `scripts/experiments/` |
| `bin/agent-context verify examples/hello-service` | Tier-3 verify on the bundled demo pack | After template or verifier edits |
| `bin/agent-context verify examples/agent-chorus-reference` | Tier-3 verify on the reference pack | After template or verifier edits |
| `bin/agent-context doctor` | Python version, CLI version, working-dir status | When debugging an operator issue |
| `tools/check_freshness.sh --base-ref origin/main` | Advisory freshness on the live working tree | Before committing changes that touch CONTEXT_RELEVANT_PATHS |
| `scripts/sync-from-canonical.sh` | Mirrors `templates/`, `tools/`, `SKILL.md` into `skills/agent-context/` | After any edit to a canonical file |
| `npx --yes @marp-team/marp-cli@latest talk/cursor-meetup-may-2026.md -o talk/cursor-meetup-may-2026.html` | Re-render the deck HTML | After deck edits (also re-render PDF; refresh `talk/index.html`) |

## CI / Workflow Integration

- **Workflow file:** `.github/workflows/ci.yml` runs the unittest suite + verifies both example packs on every PR. `.github/workflows/release.yml` packages on tag push. `.github/workflows/deploy-pages.yml` rebuilds the `talk/` deck for GitHub Pages on every push to `main`.
- **Chosen `CONTEXT_RELEVANT_PATHS` (for this repo's own freshness checks):** `bin/`, `tools/`, `templates/`, `skills/`, `scripts/experiments/`, `tests/`, `SKILL.md`, `RELEASE_NOTES.md`, `docs/architecture.md`, `docs/design-principles.md`. Anything outside these paths (e.g., `docs/evidence/`, `talk/`) is excluded — those are derived/published artifacts, not behavior-defining source.
- **Verifier command:** `bin/agent-context verify .` (operates on `<repo>/.agent-context/current/`).
- **Freshness mode:** advisory. Running `tools/check_freshness.sh` warns; the pre-push hook surfaces the warning; CI does not hard-block on freshness for this repo because the pack documents the toolchain itself — staleness manifests as docs drift, not runtime failure.
- **Rationale:** the verifier is the hard gate (it checks structure, schema, glob existence). Freshness is a soft gate that nudges authors to update the pack when changing CONTEXT_RELEVANT_PATHS.

## Release Flow

1. Bump `bin/agent-context` (`__version__`), `SKILL.md` frontmatter (`metadata.version`), `skills/agent-context/SKILL.md` frontmatter (`metadata.version`), `README.md` (badge URL `badge/version-X.Y.Z-...`). Also add a `RELEASE_NOTES.md` entry under the new version heading (convention).
2. Run `python3 -m unittest discover -s tests -v` — must be green.
3. Run `bin/agent-context verify examples/hello-service` and `bin/agent-context verify examples/agent-chorus-reference` — both must pass.
4. Commit with a clear release message (e.g., `vX.Y.Z: <one-line summary>`).
5. Tag: `git tag vX.Y.Z`. Push commit + tag: `git push origin main && git push origin vX.Y.Z`.
6. The `release.yml` workflow runs on the tag push and produces release artifacts.
7. The `deploy-pages.yml` workflow runs on the commit push and rebuilds the GitHub Pages deck (talk/).

## Environment / Operational Notes

- **Python:** stdlib-only. No `requirements.txt`, no virtualenv needed. CI uses the GitHub-Actions-default Python 3 (currently 3.12 family).
- **Bash:** `set -euo pipefail` patterns; tested on macOS and Ubuntu. The shell scripts in `scripts/experiments/` rely on `git`, `jq` (most), and standard POSIX tooling.
- **Marp render:** `npx --yes @marp-team/marp-cli@latest …` — required only for the `talk/` deck. PDF render needs `--allow-local-files`.
- **Tests run:** locally on macOS dev workstations and on Ubuntu CI. They do not require network access. They do not require any agent CLI to be installed (no `claude`, `codex`, or `cursor-agent` invocations).
- **Experiments harness:** the `scripts/experiments/` tooling is for *operator-driven* multi-agent reruns. It does NOT run in CI — running an experiment requires a private rerun root with isolated clones of target repos. See `docs/architecture.md` and the deck's methodology slide for the protocol.

## Agent-Context Maintenance

- **Update the pack when** adding a CLI subcommand, changing tier defaults, adding a new agent extractor, shipping a new schema version, or restructuring the experiments pipeline.
- **Most-patched section:** `20_CODE_MAP.md` "High-Impact Paths" and "Quick Lookup Shortcuts" — refreshed whenever a new core file is added or an existing one's role shifts.
- **Less-patched but watch:** `30_BEHAVIORAL_INVARIANTS.md` "File Families" counts. Any new file under one of the listed globs invalidates the count. Re-verify with `git ls-files <glob> | wc -l` after structural changes.
- **`.agent-context/` lives in this repo's `main` branch** — same review path as code changes. PRs that change the pack should call out the rationale in the PR body.
- **Sync target:** if you update this pack, also bring `examples/hello-service/.agent-context/current/` and `examples/agent-chorus-reference/` up to date if their templates have drifted from the new canonical.
