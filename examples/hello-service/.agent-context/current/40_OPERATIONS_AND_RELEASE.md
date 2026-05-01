# Operations and Release

## Validation Commands

| Command | What it checks | When to run |
|---|---|---|
| `python3 -m unittest discover -s tests -v` | Unit tests | On every change |
| `python3 -m src.server` | Smoke-run the server | Before merging server.py changes |
| `../../bin/agent-context verify .` | Pack integrity | When touching `.agent-context/current/` |

## CI / Workflow Integration

- Workflow file patched or created: the parent repo's `.github/workflows/ci.yml` runs `bin/agent-context verify examples/hello-service` on push and PR.
- Chosen `CONTEXT_RELEVANT_PATHS`: `src/ tests/`
- Verifier command: `python3 ../../tools/verify_agent_context.py --repo-root .`
- Freshness mode: follow-up (this example does not maintain its own git history).
- Rationale: the worked example lives inside the parent agent-context repo; the parent repo's CI exercises verify end-to-end.

## Release Flow

1. Bump `__version__` in `src/__init__.py`.
2. Update any affected pack entry (usually `10_SYSTEM_OVERVIEW.md` command list).
3. The parent agent-context repo's release flow picks up the example as part of its tag.

## Environment / Operational Notes

- No persistent state; restart is safe.
- Default bind is `127.0.0.1` — the service is not intended for public exposure.

## agent-context Maintenance

- Update the pack when adding a new endpoint, env var, or source module.
- Sections most likely to need patching: `20_CODE_MAP.md` (new path rows) and `30_BEHAVIORAL_INVARIANTS.md` (new update-checklist rows).
