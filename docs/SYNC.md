# Three-Way Sync Policy

`agent-context` lives in **three parallel tracks**. This doc says which track is the source of truth, what belongs in each, how often they sync, and how to run the sync script.

## Intro

The canonical source is the internal team skill repository:

    ~/sandbox/work/cross-team-repos/team_skills/skills/agent-context/

Two derived tracks consume it:

- **`agent-chorus/skills/agent-context/`** — the chorus-bundled skill. Includes chorus-specific invocation paths and session-coordination assumptions.
- **`agent-context/` (this repo)** — the public distribution. Includes the tier 3 authority layer, but no chorus-specific refs. Friendly Python CLI (`bin/agent-context`) replaces chorus CLI invocations.

```
                    team_skills (canonical)
                    /                      \
                   /                        \
       agent-chorus/skills                  agent-context (public)
       (bundled skill)                      (distilled public)
```

## What belongs in each track

| Layer | team_skills | agent-chorus/skills | agent-context (public) |
|---|---|---|---|
| Content markdown (00–40 templates) | yes | yes | yes |
| Acceptance tests template | yes | yes | yes |
| Navigation (`search_scope.json`) | yes | yes | yes |
| Manifest (informational) | yes | yes | yes |
| Design principles doc | yes | yes | yes |
| Architecture doc | yes | yes | yes |
| Authority layer (`routes.json`, `completeness_contract.json`, `reporting_rules.json`) | yes | yes | yes |
| Python verify/freshness scripts | yes | yes | yes |
| Chorus CLI invocation in getting-started | yes | yes | **no** (replaced with `bin/agent-context`) |
| Internal team refs (Edelman-DxI, stream-models, etc.) | yes | no | no |

## Cadence

- **Immediate (within ~1 day)**: a gap fix a user reports against a derived track. Land in `team_skills` first, sync to the other derived track, then sync to the reporter's home track last.
- **Batched (weekly / release)**: design principle evolution, template restructures, new invariants. Canonical merges first, soaks in internal use for a few days, then propagates to both derived tracks in a single pass.
- **Release-coupled**: when `agent-chorus` cuts a version, the skill sync is part of release prep. Same applies to tagged releases of this public repo.

## Using `scripts/sync-from-canonical.sh`

From the repo root:

```bash
# Preview what would change, without writing anything.
scripts/sync-from-canonical.sh --dry-run

# Real sync (default canonical path = ~/sandbox/work/...).
scripts/sync-from-canonical.sh

# Pin to a specific canonical clone.
scripts/sync-from-canonical.sh --canonical-path /path/to/team_skills/skills/agent-context

# Review the changes, then commit.
git diff
git commit -m "chore: sync from team_skills@<sha>"
```

The script is **idempotent** — running it twice yields the same state as once. After copying, it runs a JSON template-marker scan to catch template leaks. It does not commit on your behalf; review the diff first.

### Files the sync script deliberately does NOT overwrite

Three files are public-variant-by-design and are maintained in this repo. The sync script logs them as "HOLD" and leaves them alone:

- `tools/verify_agent_context.py` — keeps public CLI behavior and stdlib-only validation while avoiding internal-only assumptions from the canonical environment.
- `templates/manifest.json` — uses `agent_context_version` rather than the internal skill-version field.
- `docs/architecture.md` — describes the public CLI and tier model rather than chorus-specific runtime behavior.

If the canonical versions of those files change in a way that affects the public-variant logic, the maintainer merges the changes by hand.

## How to contribute

**Default path: PR against the canonical source first.**

1. For templates, scripts, and design docs, open your PR against
   `team_skills/skills/agent-context/`. It will propagate here on the next sync.
2. If you hit a bug that is specific to the public repo (for example, something about the Python CLI or the worked example), open an issue or PR here.
3. Public-repo-only changes — the Python CLI (`bin/agent-context`), the sync script, the worked example under `examples/`, the README, the CI workflows — live here and do not sync upstream.

If you are unsure which track a change belongs in, ask in the issue before you start.
