# Contributing

Thanks for taking the time. This is a small repo with a clear scope — a navigation contract for AI agents working in large codebases. The core templates, verifier, and design docs are distilled from a canonical skill source maintained outside this public repo, and changes there flow through a three-way sync. Please read `docs/SYNC.md` before opening a PR.

## How to propose changes

1. **Templates, verifier, or design docs**: the canonical source is a private skill repository maintained outside this public repo. If you can, open the PR there first. If you do not have access, open a PR or issue here and we will route it. See `docs/SYNC.md` for the policy.
2. **Public-repo-only surfaces** (the Python CLI in `bin/agent-context`, the sync script in `scripts/`, the worked example under `examples/`, the README, or the CI workflows): PRs here, directly.
3. Keep PRs focused. One logical change per PR.
4. Run the checks before pushing:
   ```bash
   python3 -m unittest discover -s tests -v
   bin/agent-context verify examples/hello-service
   ```

## How to report bugs

Open a GitHub issue with:

- A short description.
- What you ran (`bin/agent-context ...`) and what you expected.
- The actual output, verbatim.
- Your Python version and OS.

If the bug is in the pack content itself (for example, a template that is confusing), note that — it is usually a canonical-source fix. See `docs/SYNC.md`.

## Three-way sync reminder

This repo is one of three tracks. Changes to core content flow from the canonical skill source to here and to `agent-chorus`. Public-repo-only changes live here. `docs/SYNC.md` has the full policy and a table of what belongs in each track.

## Licensing

By submitting a contribution, you agree to license it under the [MIT License](LICENSE) that covers this repo. There is no separate CLA or DCO sign-off requirement.
