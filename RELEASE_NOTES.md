# Release Notes

## v0.2.1.4 — 2026-05-04

Deck install-path refresh. Doc-only patch — no CLI or template changes; CLI still self-reports `0.2.1`.

### What's new

- **Deck demo and first-command slides now lead with skill install.** Slides 7 and 17 of the meetup deck previously showed `~/agent-context/bin/agent-context init …` as the user-facing command. They now show per-agent skill install (Claude Code, Codex, Cursor) followed by the same agent prompt — the skill drives scaffold/fill/verify/hook. The CLI is invoked by the skill, not by the audience.

## v0.2.1.3 — 2026-05-04

End-to-end audit follow-up patch. Doc-only patch — no CLI or template changes; CLI still self-reports `0.2.1`.

### What's new

- **Final scrub of self-referential leak.** The `v0.2.1.1` entry no longer quotes the retired internal-source phrasing while describing what was removed.
- **README headline metrics align with deck averages.** README §Results now reports the Claude files-opened and tokens metrics as cross-repo averages (matching the meetup deck) instead of a 2-of-3-repo range that silently excluded the smaller `agent-chorus` repo.
- **SKILL.md drift guard.** New `tests/test_skill_sync.py` fails CI if the root `SKILL.md` and `skills/agent-context/SKILL.md` diverge, so the installable skill cannot quietly drift from the public source-of-truth.

## v0.2.1.2 — 2026-05-04

Public evidence-alignment audit patch. Doc-only patch — no CLI or template changes; CLI still self-reports `0.2.1`.

### What's new

- **Deck and README evidence now match.** README and evidence docs now separate older Claude-heavy reviewer-graded evidence from the current Codex/Cursor meetup run, using the same per-agent metrics as the deck.
- **Release-note scrub tightened.** The `v0.2.1.1` note now avoids spelling out retired private repo names while describing the scrub.

## v0.2.1.1 — 2026-05-04

Public-readiness scrub. Doc-only patch — no CLI or template changes; CLI still self-reports `0.2.1`.

### What's new

- **Removed remaining private-repo references.** `CONTRIBUTING.md`, `docs/SYNC.md`, and `talk/README.md` now use the same neutral "canonical skill source maintained outside this public repo" phrasing as the rest of the repo. No retired internal-source names remain in the public tree.
- **Talk README uses repo-relative paths.** `talk/README.md` now documents `open talk/index.html` and `python3 -m http.server 8000` from the repo root instead of a maintainer-specific home directory layout.

## v0.2.1 — 2026-05-04

Meetup demo hardening release. The public repo and the included skill now match the workflow shown in the talk: an agent can scaffold a repo, fill the pack, verify it, set up local freshness warnings, and document or wire CI enforcement.

### What's new

- **Public repo cleanup for the meetup.** Private rerun harnesses and task
  artifacts now stay local and ignored; the tracked repo focuses on the product
  surface: CLI, templates, tools, examples, docs, evidence, talk, and skill.
- **Installable skill package.** The root `SKILL.md` remains the public
  source-of-truth, and `skills/agent-context/SKILL.md` mirrors it for agent
  skill registries. `skills/agent-context/agents/openai.yaml` adds Codex/OpenAI
  metadata so agents can discover the workflow as an installable skill.
- **Hook setup is now first-class.** `agent-context init --install-hook .` copies `pre-push-hook.sh` into `.agent-context/tools/` and installs an advisory `.git/hooks/pre-push` freshness hook when safe. `agent-context install-hook .` can be run later to install or refresh the hook. Existing unmanaged hooks are preserved and a `pre-push.agent-context.sample` chain block is written for deliberate manual merge.
- **Skill workflow now completes the demo promise.** `SKILL.md` explicitly drives agents through pack creation, subsystem inventory, acceptance tests, verify, advisory hook setup, and CI/freshness follow-up documentation.
- **Helper tool set completed.** Fresh packs now carry `verify_agent_context.py`, `check_freshness.sh`, and `pre-push-hook.sh` together, so the repo can verify itself without depending on the original checkout.
- **Agent-chorus learnings folded back.** The setup workflow now emphasizes hard multi-hop tasks, runtime parity, audit-path completeness, and freshness as a hard gate for evidence runs — lessons surfaced while refreshing the agent-chorus reference pack and redaction/parity tasks.
- **Polyglot skills-repo learnings folded back.** The skill keeps the production `enumerate before narrate` pattern, cross-language file-family checklists, negative guidance, and "silent fallback" risk callouts used to catch map/default bugs in a polyglot skills repo.
- **Docs aligned for live demo.** README, getting started, architecture docs, and CI reference now describe the same setup path: `init --tier 3 --install-hook`, fill via the skill, `verify`, `freshness`, and CI adaptation.

### Compatibility

- Existing v0.2.0 packs remain valid. Re-run `agent-context init --force` only if you intentionally want to refresh templates; otherwise copy or install the hook with `agent-context install-hook .`.
- `agent-context freshness` remains advisory and exits zero by design. CI and experiment harnesses that need hard failure should call `.agent-context/tools/check_freshness.sh` directly, as documented in the rerun methodology.

## v0.2.0 — 2026-05-01

Meetup-ready release. The pack is now fully self-contained with all three layers, a skill definition for agent-driven pack creation, and evidence materials from 78+ graded experiments.

### What's new

- **SKILL.md** — 10-step skill definition adapted from a production polyglot skills repository. Agents can now autonomously create, update, and maintain packs by following the skill. Includes the subsystem inventory step (enumerate before narrate), acceptance test framework (4 tests with grep verification), and CI adaptation guidance.
- **Authority layer templates** — `routes.json`, `completeness_contract.json`, `reporting_rules.json` are now shipped as tier 3 templates. These give trust-and-follow agents (Claude, Gemini) authoritative guidance without needing the chorus CLI.
- **Tier support** — `agent-context init --tier 1|2|3 .` lets you choose adoption level:
  - Tier 1 (minimal): `20_CODE_MAP.md` + `search_scope.json` (2 files)
  - Tier 2 (standard): + start, invariants, manifest, acceptance tests (6 files)
  - Tier 3 (full, default): all 11 files including authority layer
- **Routing block generation** — `init` now creates managed routing blocks in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.cursorrules`. Blocks are tier-aware and use HTML comment sentinels for idempotent upsert.
- **Cursor integration** — `.cursorrules` is generated automatically with the search-and-verify routing pattern. Cursor reads this file natively.
- **Tool copying** — `init` copies `verify_agent_context.py` and `check_freshness.sh` into the target repo's `.agent-context/tools/` so packs are self-verifiable without agent-context installed.
- **Upgraded verifier** — tier-aware validation, authority layer contract checking (glob patterns match real files, no template variables), routing file validation, coverage heuristics.
- **Evidence materials** — figures from agent-recall research (asymmetry contrast, three-track framework, experiment results), metrics summary, full results breakdown, demo assets.
- **Real-world reference pack** — `examples/agent-chorus-reference/` shows a mature tier 3 pack from a 155-file dual-implementation CLI repo.
- **Getting started guide** — step-by-step quickstart for new users.
- **CI example workflow** — reference GitHub Actions job for PR gating.

### Breaking changes

- None. Tier 2 behavior matches v0.1.0 default. Existing packs validate without changes.

---

## v0.1.0 — 2026-04-20

Initial public release.

**Canonical source**: this repo is a distilled public view of a production agent-context skill. Updates flow from canonical to this repo via `scripts/sync-from-canonical.sh`. See `docs/SYNC.md`.

### What's included
- Content layer: 5 markdown templates (`00_START_HERE`, `10_SYSTEM_OVERVIEW`, `20_CODE_MAP`, `30_BEHAVIORAL_INVARIANTS`, `40_OPERATIONS_AND_RELEASE`) + `acceptance_tests.md`.
- Navigation layer: `search_scope.json` template.
- Validation: `verify_agent_context.py` + `check_freshness.sh` (stdlib-only Python + POSIX shell).
- Python CLI: `bin/agent-context init | verify | doctor | freshness`.
- Worked example: `examples/hello-service/` — small service with a filled pack; verify passes out of the box.
- Three-way sync policy + tooling: `scripts/sync-from-canonical.sh` + `docs/SYNC.md`.
