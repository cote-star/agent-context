# CI Adaptation Guide

Use this guide when wiring `agent-context` verification into a repo's existing automation.

## Goal

Patch the repo's existing pull-request gate whenever possible. Do not add a second competing CI workflow unless there is no suitable PR workflow to extend.

## Workflow Selection Order

1. Prefer the main PR workflow already required for merge.
2. If multiple PR workflows exist, choose the one that:
   - checks out the full repo
   - already installs the repo runtime
   - is expected to run on most code changes
3. Only create a dedicated `agent-context` workflow if no existing PR workflow is a safe integration point.

## Runtime Reuse Rules

- Reuse the runtime setup already present in the workflow.
- If the workflow already sets up Python, call `python3 .agent-context/tools/verify_agent_context.py`.
- If the workflow already uses shell-only steps, you may call the verifier via `python3` directly.
- Do not introduce a second package manager or runtime path just for agent-context.

## Choosing CONTEXT_RELEVANT_PATHS

Base the freshness paths on the scope claimed in `00_START_HERE.md`.

Typical examples:

- FastAPI / Python backend:
  `app/ tests/ migrations/ .github/workflows/`
- Node / frontend:
  `src/ app/ public/ tests/ .github/workflows/`
- Library / CLI:
  `src/ lib/ tests/ scripts/`
- Infrastructure:
  `terraform/ modules/ env/ scripts/ .github/workflows/`
- ML / data:
  `models/ pipelines/ src/ tests/`

Rules:

- Include directories that define behavior, architecture, or operational gates.
- Include workflow/config directories when the agent context claims to cover operations or CI.
- Exclude generated output, vendored dependencies, and caches.
- Prefer a narrow set that matches the repo over generic defaults.

## What To Record In 40_OPERATIONS_AND_RELEASE.md

- The workflow file patched or created
- The chosen `CONTEXT_RELEVANT_PATHS`
- The verifier command used
- Whether freshness is a hard gate or a documented follow-up
- Any repo-specific caveats

## Acceptable Outcomes

- Best: existing PR workflow patched, verifier step added, freshness hard-gated
- Acceptable: existing PR workflow patched, integrity gated, freshness documented as follow-up
- Fallback: dedicated workflow added because no safe existing PR workflow exists
