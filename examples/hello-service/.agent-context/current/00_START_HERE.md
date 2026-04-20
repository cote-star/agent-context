# hello-service — Agent Context

**MANDATORY before starting work.** Do NOT open repo source files until steps 1-3 are complete.

## Fast Facts

| Field | Value |
|---|---|
| Product | hello-service — minimal HTTP greeter used as an agent-context worked example |
| Languages | Python 3.8+ (stdlib only) |
| Package manager | none (stdlib) |
| Quality gate | `python3 -m unittest discover -s tests -v` |
| Core risk | Silent mis-parse of the `name` query param leading to the wrong greeting |
| Version | `src/__init__.py` `__version__` string |

## Scope Rule

This agent context covers the hello-service code under `src/` and its tests under `tests/`. It does NOT cover the broader agent-context tooling at the parent repo root.

## Read Order

1. This file (fast facts, scope, stop rules)
2. `10_SYSTEM_OVERVIEW.md`
3. `20_CODE_MAP.md` or `30_BEHAVIORAL_INVARIANTS.md` depending on task type
4. Then open source files as needed for your task

## Stop Rules

Before opening any source file, check whether your answer is already in the agent context:

- "Where is X configured?" -> `20_CODE_MAP.md`
- "What files change for Y?" -> `30_BEHAVIORAL_INVARIANTS.md`
- "How do I validate Z?" -> `40_OPERATIONS_AND_RELEASE.md`
- "What is the runtime shape?" -> `10_SYSTEM_OVERVIEW.md`

If the pack answers your question, do not open additional files. If it does not, use `search_scope.json` to bound your search.

## Not Covered in Detail

- Parent repo's `bin/`, `tools/`, `templates/`, and `scripts/` — those belong to the agent-context tooling, not to hello-service.
