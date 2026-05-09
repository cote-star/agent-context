"""Coverage for the --model extension in scripts/experiments/run-agent-lane.sh.

Phase 3 of the rerun harness needs to run two cursor-agent lanes in parallel
with different models (e.g. composer-2-fast vs claude-opus-4-7-medium).
Without --model, both lanes write into the same results directory and clobber
each other. These tests pin the contract that:

  * --model is wired through to cursor-agent's CLI.
  * --model produces a per-model results path so concurrent lanes are safe.
  * --model is rejected for codex/claude (cursor-only knob in this harness).
  * Omitting --model preserves the legacy path layout.
  * The slugify helper canonicalises arbitrary model strings.

All tests run with --dry-run so no actual agent is invoked. The shell script
also requires real on-disk scaffolding (condition dir, prompt file, results
dir) before it reaches the dry-run echo, so each test stages a minimal
RERUN_ROOT layout in a tmpdir.
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "experiments" / "run-agent-lane.sh"

ALIAS = "demo-repo"


def _stage_rerun_root(root: pathlib.Path, agent: str, condition: str,
                      model_slug: str | None = None) -> None:
    """Lay down the minimum structure run-agent-lane.sh expects on disk.

    The script asserts the existence of:
      * <root>/<alias>/<condition>/                         (cwd)
      * <root>/<alias>/.prompt-<agent>-<condition>.txt      (prompt file)
      * <root>/<alias>/results/<agent>/<condition>[/slug]/  (outdir)

    When --model is set, the outdir gains a per-model subdir; we mirror that
    here so the script's existence check passes.
    """
    alias_root = root / ALIAS
    (alias_root / condition).mkdir(parents=True, exist_ok=True)
    (alias_root / f".prompt-{agent}-{condition}.txt").write_text("noop\n")
    results = alias_root / "results" / agent / condition
    if model_slug is not None:
        results = results / model_slug
    results.mkdir(parents=True, exist_ok=True)


def _run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT),
         "--rerun-root", str(root),
         "--aliases", ALIAS,
         "--dry-run",
         *args],
        capture_output=True,
        text=True,
        check=False,
    )


class RunAgentLaneModelTests(unittest.TestCase):
    def test_cursor_with_model_includes_flag_in_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "cursor", "bare",
                              model_slug="claude-opus-4-7-medium")

            result = _run(root,
                          "--agent", "cursor",
                          "--condition", "bare",
                          "--model", "claude-opus-4-7-medium")

            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            self.assertIn("--model 'claude-opus-4-7-medium'", result.stdout)
            self.assertIn("cursor-agent", result.stdout)

    def test_cursor_with_model_uses_model_aware_outdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "cursor", "bare",
                              model_slug="claude-opus-4-7-medium")

            result = _run(root,
                          "--agent", "cursor",
                          "--condition", "bare",
                          "--model", "claude-opus-4-7-medium")

            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            expected = (
                f"out:    {root}/{ALIAS}/results/cursor/bare/"
                "claude-opus-4-7-medium"
            )
            self.assertIn(expected, result.stdout)
            # Header should also surface the model so operators see it.
            self.assertIn("model:  claude-opus-4-7-medium", result.stdout)

    def test_model_rejected_for_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "codex", "bare")

            result = _run(root,
                          "--agent", "codex",
                          "--condition", "bare",
                          "--model", "claude-opus-4-7-medium")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--model", result.stderr)
            self.assertIn("cursor", result.stderr)

    def test_model_rejected_for_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "claude", "bare")

            result = _run(root,
                          "--agent", "claude",
                          "--condition", "bare",
                          "--model", "claude-opus-4-7-medium")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--model", result.stderr)
            self.assertIn("cursor", result.stderr)

    def test_cursor_without_model_preserves_legacy_path(self) -> None:
        """No --model means the existing results/<agent>/<condition>/ path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "cursor", "structured_fresh")

            result = _run(root,
                          "--agent", "cursor",
                          "--condition", "structured_fresh")

            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            expected = (
                f"out:    {root}/{ALIAS}/results/cursor/structured_fresh"
            )
            self.assertIn(expected, result.stdout)
            # No per-model subdir suffix should appear after the path.
            self.assertNotIn(f"{expected}/", result.stdout)
            # Dry-run echo should NOT carry --model.
            self.assertNotIn("--model", result.stdout)
            # Header should NOT surface a model line either.
            self.assertNotIn("model:  ", result.stdout)

    def test_prompt_path_substituted_for_model_aware_outdir(self) -> None:
        """The agent's prompt tells it where to write result JSONs. With --model,
        the outdir gains a model-slug subdir, so the prompt's `results/<agent>/
        <condition>/<task>.json` references must be rewritten to include the
        slug — otherwise the agent writes outside the model-aware outdir and
        the lane sees zero completed JSONs.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "cursor", "bare",
                              model_slug="claude-opus-4-7-medium")
            # Replace the noop prompt with a realistic one carrying the
            # legacy result-path that the agent would normally read.
            prompt_path = root / ALIAS / ".prompt-cursor-bare.txt"
            prompt_path.write_text(
                "Write one JSON result file per task to:\n"
                "  ../results/cursor/bare/<task_id>.json\n"
            )

            result = _run(root,
                          "--agent", "cursor",
                          "--condition", "bare",
                          "--model", "claude-opus-4-7-medium")

            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            # The dry-run echoes the effective (substituted) prompt body.
            self.assertIn("--- effective prompt", result.stdout)
            self.assertIn(
                "../results/cursor/bare/claude-opus-4-7-medium/<task_id>.json",
                result.stdout,
            )
            # And the legacy unsubstituted line must NOT appear in the
            # effective prompt — substitution must replace, not append.
            effective = result.stdout.split("--- effective prompt", 1)[1]
            self.assertNotIn(
                "../results/cursor/bare/<task_id>.json",
                effective,
            )

    def test_no_model_leaves_prompt_unsubstituted(self) -> None:
        """Without --model, the prompt is passed through unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _stage_rerun_root(root, "cursor", "bare")
            (root / ALIAS / ".prompt-cursor-bare.txt").write_text(
                "Write one JSON result file per task to:\n"
                "  ../results/cursor/bare/<task_id>.json\n"
            )
            result = _run(root, "--agent", "cursor", "--condition", "bare")
            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            # No effective-prompt block should be emitted when MODEL is unset.
            self.assertNotIn("--- effective prompt", result.stdout)

    def test_slugify_normalises_freeform_model_string(self) -> None:
        """Freeform model strings get lowercased + dasherised consistently."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # The script's outdir existence check uses the *slugified* path,
            # so we mirror what slugify will produce.
            _stage_rerun_root(root, "cursor", "bare",
                              model_slug="claude-opus-4-7-medium")

            result = _run(root,
                          "--agent", "cursor",
                          "--condition", "bare",
                          "--model", "Claude Opus 4.7 Medium")

            self.assertEqual(result.returncode, 0,
                             msg=result.stdout + result.stderr)
            expected_path = (
                f"out:    {root}/{ALIAS}/results/cursor/bare/"
                "claude-opus-4-7-medium"
            )
            self.assertIn(expected_path, result.stdout)
            # The original (unslugified) model id is preserved on the
            # cursor-agent invocation and the header line.
            self.assertIn("--model 'Claude Opus 4.7 Medium'", result.stdout)
            self.assertIn("model:  Claude Opus 4.7 Medium", result.stdout)


if __name__ == "__main__":
    unittest.main()
