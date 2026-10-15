# REPLACE: Repo Name — Agent Context

**MANDATORY before starting work.** Complete the applicable read order below before opening repo source files.

## Fast Facts

| Field | Value |
|---|---|
| Product | REPLACE: product/service/library name |
| Languages | REPLACE: primary languages and frameworks |
| Package manager | REPLACE: uv / npm / pnpm / cargo / etc. |
| Quality gate | REPLACE: primary validation commands |
| Core risk | REPLACE: most likely silent failure or production-risk area |
| Version | REPLACE: release/versioning mechanism |

## Scope Rule

This agent context covers REPLACE: the code and operational areas the pack is intended to guide. It does NOT cover REPLACE: adjacent systems or directories outside that scope.

## Read Order

1. This file (fast facts, scope, stop rules), then `30_BEHAVIORAL_INVARIANTS.md`.
2. Select the task in `routes.json` and follow its `read_order` and applicable named patterns. Load the completeness, search-scope and reporting contracts. Read only the follow-on files required for that task.
3. Legacy standard pack only (tier 2, no `routes.json`): read `20_CODE_MAP.md` and `search_scope.json` instead; do not require system-overview or operations files.
4. Before source inspection, read `20_CODE_MAP.md` if not already loaded, then search only within the scoped directories.

## Stop Rules

Before opening any source file, check whether your answer is already in the agent context:

- "Where is X configured?" → `20_CODE_MAP.md`
- "What files change for Y?" → `30_BEHAVIORAL_INVARIANTS.md`
- "How do I validate Z?" → `40_OPERATIONS_AND_RELEASE.md` when present; otherwise the quality gate above
- "What is the runtime shape?" → `10_SYSTEM_OVERVIEW.md` when present; otherwise `20_CODE_MAP.md`

If the pack answers your question, do not open additional files. If it does not, use `search_scope.json` to bound your search.

## Not Covered in Detail

REPLACE: List any subsystems from the inventory that exist in the repo but are not covered in depth by this pack. Include directory path and a one-line description so agents know they exist even though the pack doesn't guide them. Remove this section if every subsystem is covered.
