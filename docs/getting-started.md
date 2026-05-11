# Getting Started with Agent Context

## 1. Install the skill

Clone the repo once so your agent can use the bundled skill:

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
```

Then install or register `~/agent-context/skills/agent-context` with your agent:

| Agent | Setup |
|---|---|
| Claude Code | `cp -r ~/agent-context/skills/agent-context ~/.claude/skills/` |
| Codex | register `~/agent-context/skills/agent-context/agents/openai.yaml` with your Codex skill registry |
| Cursor | open the target repo; Cursor reads `.cursorrules` after the pack exists |

## 2. Ask your agent to author the pack

Open Claude Code, Cursor, Codex, or another coding agent in the repo you want to create context for. The repo should have **50+ files or 3+ subsystems** to benefit most from agent-context.

Ask:

> Use the agent-context skill to build context for this repo.

The skill drives scaffold → subsystem inventory → filled templates → grep-backed acceptance tests → verification → freshness hook guidance. It may invoke the CLI scaffold:

```bash
~/agent-context/bin/agent-context init --tier 3 --install-hook .
```

That scaffold creates `.agent-context/current/` with the full pack: 5 markdown docs, 3 authority JSON files, `search_scope.json`, `manifest.json`, and `acceptance_tests.md`. It also copies helper tools into `.agent-context/tools/` and writes managed routing blocks to agent rule files. `init` is the bootstrap step; the skill is the authoring workflow.

The skill then fills the pack:

1. `00_START_HERE.md` — entrypoint, fast facts, task routing, stop rules
2. `10_SYSTEM_OVERVIEW.md` — architecture, runtime flow, silent failure modes
3. `20_CODE_MAP.md` — navigation index, lookup shortcuts, tracing flows
4. `30_BEHAVIORAL_INVARIANTS.md` — testable invariants, change checklists, file families
5. `40_OPERATIONS_AND_RELEASE.md` — validation commands, CI checks, deploy, release

You should end with a reviewable diff that contains the `.agent-context/` pack plus managed routing blocks.

## 3. Review and verify the pack

```bash
~/agent-context/bin/agent-context verify .
~/agent-context/bin/agent-context freshness . --base-ref origin/main
~/agent-context/bin/agent-context doctor
```

`verify` runs machine-checkable structural and semantic validation. `freshness` checks whether relevant code changed without corresponding context updates. `doctor` audits local setup. Fix any reported issues, then re-run until the pack passes.

Review the diff like code:
- No `REPLACE` markers remain
- Every JSON artifact has repo-specific entries
- `CLAUDE.md` says **"BEFORE starting any task, read these 3 files"**
- `AGENTS.md` includes **"Search ONLY within scoped directories"**
- Acceptance tests cite concrete source evidence

## 4. Test one bare-vs-context task

Pick the painful workflow that motivated the pack. Run the same request once against a bare clone and once against the context-enabled clone. Compare files opened, dead ends, missing surfaces, and production-risk mistakes.

## 5. Set up CI enforcement

Add an `agent-context` verification step to your PR workflow. This should fail PRs when context-relevant code changes without a corresponding pack update.

This is not required for the initial commit, but should be set up before the pack is treated as production-ready. Prefer patching the repo's existing PR workflow rather than adding a second competing workflow. Use [`ci-adaptation.md`](ci-adaptation.md) to choose the right workflow and source-root paths for the repo.

A reference CI job is provided in [`references/ci-example.yml`](references/ci-example.yml). It assumes the repo contains:
- `.agent-context/tools/verify_agent_context.py`
- `.agent-context/tools/check_freshness.sh`
- `.agent-context/tools/pre-push-hook.sh`

Those helpers are copied from this repo during `init` and should then be wired into the repo's CI. Install or refresh the advisory pre-push hook with:

```bash
~/agent-context/bin/agent-context install-hook .
```

If the repo already has an unmanaged pre-push hook, the command preserves it and writes `.git/hooks/pre-push.agent-context.sample` so you can merge the freshness block into the existing hook chain deliberately.

If CI enforcement can't be set up yet, document it as a follow-up in `40_OPERATIONS_AND_RELEASE.md` so the gap is tracked.

## 6. Review and merge

Open a PR. The pack should pass the quality bar:
- Every markdown file has content (no `REPLACE` markers remaining)
- Every JSON artifact has repo-specific entries
- `CLAUDE.md` says **"BEFORE starting any task, read these 3 files"**
- `AGENTS.md` includes **"Search ONLY within scoped directories"**
- `python3 .agent-context/tools/verify_agent_context.py` passes from the repo root
- `agent-context install-hook .` has installed, refreshed, or documented the advisory hook follow-up
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

## Advanced/manual/scripted setup

You can use the CLI directly when no agent is in the loop, or when you are scripting repo bootstrap:

```bash
git clone https://github.com/cote-star/agent-context.git ~/agent-context
cd /path/to/your-repo
~/agent-context/bin/agent-context init --tier 3 --install-hook .
```

Use `--tier 1` for a minimal code-map-only pack, or `--tier 2` for a starter pack without system overview, operations docs, or authority contracts. `--tier 3` (the default) gives you everything.

Direct CLI setup leaves `REPLACE` markers for you or an agent to fill manually before `verify` will pass.
