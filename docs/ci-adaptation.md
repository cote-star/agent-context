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

## Common Layouts

### Single App

Use the app's source, tests, migrations, and workflow/config paths:

```yaml
env:
  CONTEXT_RELEVANT_PATHS: app/ tests/ migrations/ .github/workflows/
```

This should usually be a hard gate once the initial pack is reviewed.

### Monorepo

Start with the package roots that the pack claims to cover. Do not gate
uncovered workspaces until the pack says how agents should navigate them.

```yaml
env:
  CONTEXT_RELEVANT_PATHS: services/api/ apps/web/ packages/shared/ .github/workflows/
```

If each workspace owns its own pack, run the verifier from that workspace
and pass paths relative to that workspace:

```yaml
- name: Verify API agent context
  working-directory: services/api
  env:
    CONTEXT_RELEVANT_PATHS: app/ tests/ migrations/
  run: |
    python3 .agent-context/tools/verify_agent_context.py
    sh .agent-context/tools/check_freshness.sh --base-ref origin/${{ github.base_ref }}
```

### Generated Or Vendored Code

Generated and vendored paths should be excluded from freshness unless the
pack explicitly teaches agents to edit the generator or vendoring policy.

Prefer gating the source of truth:

```yaml
env:
  CONTEXT_RELEVANT_PATHS: proto/ generators/ src/ tests/
```

Avoid gating generated outputs:

```yaml
# Usually wrong: generated files create noisy freshness failures.
CONTEXT_RELEVANT_PATHS: generated/ vendor/ dist/
```

### Multiple Runtime Roots

When one repo has separate runtime surfaces, include the shared contracts
and the operational glue that connects them:

```yaml
env:
  CONTEXT_RELEVANT_PATHS: api/ web/ workers/ packages/contracts/ .github/workflows/
```

If the pack covers only one runtime root, freshness should be advisory for
the uncovered roots until a pack update includes them.

## Blocking Versus Advisory Freshness

Use freshness as a **blocking** gate when:

- The pack is reviewed and merged through the normal code-review path.
- `CONTEXT_RELEVANT_PATHS` matches the pack's declared scope.
- The repo has stable source roots and low generated-file churn.
- The team expects agents to rely on the pack for impact analysis.

Keep freshness **advisory** when:

- The pack is new, incomplete, or being trialed.
- Source roots are still moving.
- Generated or vendored paths cannot be cleanly separated yet.
- The workflow cannot reliably compare against the PR base ref.

Advisory mode should still print the changed context paths. Treat the
warning as a review prompt: either update `.agent-context/current/`, narrow
`CONTEXT_RELEVANT_PATHS`, or record why the change is outside pack scope.

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

## Copyable GitHub Actions Variants

Patch one of these into the selected PR workflow.

### Hard Gate

```yaml
- name: Verify agent context
  run: python3 .agent-context/tools/verify_agent_context.py

- name: Check agent-context freshness
  env:
    BASE_REF: origin/${{ github.base_ref }}
    CONTEXT_RELEVANT_PATHS: app/ src/ lib/ tests/ .github/workflows/
  run: sh .agent-context/tools/check_freshness.sh
```

### Advisory Freshness

```yaml
- name: Verify agent context
  run: python3 .agent-context/tools/verify_agent_context.py

- name: Check agent-context freshness (advisory)
  env:
    BASE_REF: origin/${{ github.base_ref }}
    CONTEXT_RELEVANT_PATHS: app/ src/ lib/ tests/ .github/workflows/
  run: sh .agent-context/tools/check_freshness.sh || true
```

### Integrity Only

Use this while a repo is still deciding its freshness paths:

```yaml
- name: Verify agent context
  run: python3 .agent-context/tools/verify_agent_context.py
```
