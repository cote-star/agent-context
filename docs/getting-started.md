# Getting Started with Agent Context

## 1. Clone and install

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 .
```

This scaffolds `.agent-context/current/` with the full pack: 5 markdown docs, 3 authority JSON files, `search_scope.json`, `manifest.json`, and `acceptance_tests.md`. It also copies helper tools into `.agent-context/tools/`.

Use `--tier 1` for a minimal code-map-only pack, or `--tier 2` for a starter pack without system overview, operations docs, or authority contracts. `--tier 3` (the default) gives you everything.

## 2. Open a session in the target repo

Open Claude Code, Cursor, or Codex in the repo you want to create context for. The repo should have **50+ files or 3+ subsystems** to benefit most from a context pack.

## 3. Fill the templates

Each template file contains `REPLACE` markers. Work through them in order:

1. `00_START_HERE.md` — entrypoint, fast facts, task routing, stop rules
2. `10_SYSTEM_OVERVIEW.md` — architecture, runtime flow, silent failure modes
3. `20_CODE_MAP.md` — navigation index, lookup shortcuts, tracing flows
4. `30_BEHAVIORAL_INVARIANTS.md` — testable invariants, change checklists, file families
5. `40_OPERATIONS_AND_RELEASE.md` — validation commands, CI checks, deploy, release

You can fill these manually or ask an agent: **"Fill the agent context templates for this repo"** — the agent reads the pack structure and fills markers from the codebase.

## 4. Verify the pack

```bash
~/agent-context/bin/agent-context verify .
```

This runs machine-checkable structural and semantic validation. Fix any reported issues, then re-run until it exits 0.

## 5. Set up CI enforcement

Add an `agent-context` verification step to your PR workflow. This should fail PRs when context-relevant code changes without a corresponding pack update.

This is not required for the initial commit, but should be set up before the pack is treated as production-ready. Prefer patching the repo's existing PR workflow rather than adding a second competing workflow. Use [`ci-adaptation.md`](ci-adaptation.md) to choose the right workflow and source-root paths for the repo.

A reference CI job is provided in [`references/ci-example.yml`](references/ci-example.yml). It assumes the repo contains:
- `.agent-context/tools/verify_context_pack.py`
- `.agent-context/tools/check_freshness.sh`

Those helpers are copied from this repo during `init` and should then be wired into the repo's CI. An advisory pre-push hook is at [`../tools/pre-push-hook.sh`](../tools/pre-push-hook.sh):

```bash
cp ~/agent-context/tools/pre-push-hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

If CI enforcement can't be set up yet, document it as a follow-up in `40_OPERATIONS_AND_RELEASE.md` so the gap is tracked.

## 6. Review and merge

Open a PR. The pack should pass the quality bar:
- Every markdown file has content (no `REPLACE` markers remaining)
- Every JSON artifact has repo-specific entries
- `CLAUDE.md` says **"BEFORE starting any task, read these 3 files"**
- `AGENTS.md` includes **"Search ONLY within scoped directories"**
- `python3 .agent-context/tools/verify_context_pack.py` passes from the repo root
- CI verification is either set up or documented as a follow-up with the chosen workflow and `CONTEXT_RELEVANT_PATHS`

## 7. After merge — it just works

Every agent session reads the routing block and follows the pack. No extra per-person workflow is required. Agents that support `CLAUDE.md` or `AGENTS.md` will pick up the context automatically.

## 8. Keeping it fresh

| Scenario | What happens |
|---|---|
| Agent opens a PR | Agent includes `.agent-context` updates as a separate commit |
| Human merges code | Say "update the agent context" — agent diffs and proposes per-section patches |
| CI check fails | Code changed but pack wasn't updated — update the pack before merging |
| Pre-push hook warns | Advisory only, never blocks — update when convenient |
| Freshness check via CLI | Run `bin/agent-context freshness . --base-ref origin/main` to check locally |
