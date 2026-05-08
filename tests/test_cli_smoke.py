"""CLI smoke + idempotency coverage.

Covers user-visible CLI surface that the existing `test_verify` suite skips:
the `--version` and no-arg paths, init's `--force` semantics, init outside a
git repo, hook idempotency, and the `freshness` command's advisory contract.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests._helpers import commit_all, init_git_repo, write_file


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "bin" / "agent-context"

HOOK_BEGIN = "agent-context:pre-push:begin"
HOOK_END = "agent-context:pre-push:end"
ROUTING_BEGIN = "agent-context:begin"
ROUTING_END = "agent-context:end"


def _run(args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_cli_version() -> str:
    import re
    text = (REPO_ROOT / "bin" / "agent-context").read_text()
    return re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


class SmokeTests(unittest.TestCase):
    def test_version_flag_prints_cli_version(self) -> None:
        result = _run(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"agent-context {_read_cli_version()}", result.stdout)

    def test_no_args_prints_help_and_exits_zero(self) -> None:
        result = _run([])
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout.lower())
        self.assertIn("init", result.stdout)
        self.assertIn("verify", result.stdout)


class InitForceTests(unittest.TestCase):
    def test_init_without_force_fails_when_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = _run(["init", tmpdir])
            self.assertEqual(first.returncode, 0, msg=first.stderr)

            second = _run(["init", tmpdir])
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists", second.stderr)
            self.assertIn("--force", second.stderr)

    def test_init_with_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _run(["init", tmpdir])
            current = pathlib.Path(tmpdir) / ".agent-context" / "current"
            sentinel = current / "20_CODE_MAP.md"
            sentinel.write_text("MUTATED\n")

            second = _run(["init", "--force", tmpdir])
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            # --force should restore the template; mutation is gone.
            self.assertNotEqual(sentinel.read_text(), "MUTATED\n")


class InitOutsideGitTests(unittest.TestCase):
    def test_init_outside_git_repo_does_not_leak_template_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(["init", tmpdir])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            manifest = json.loads(
                (pathlib.Path(tmpdir) / ".agent-context" / "current" / "manifest.json").read_text()
            )
            # The template ships git_revision="FULL_SHA"; init must overwrite it
            # with a real SHA when in a git repo, or with "" when not.
            self.assertEqual(manifest.get("git_revision"), "")


class InitRoutingIdempotencyTests(unittest.TestCase):
    def test_re_running_init_does_not_duplicate_routing_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _run(["init", tmpdir])
            first_claude = (pathlib.Path(tmpdir) / "CLAUDE.md").read_text()
            self.assertEqual(first_claude.count(ROUTING_BEGIN), 1)

            _run(["init", "--force", tmpdir])
            second_claude = (pathlib.Path(tmpdir) / "CLAUDE.md").read_text()
            self.assertEqual(
                second_claude.count(ROUTING_BEGIN), 1,
                msg=f"routing block duplicated:\n{second_claude}",
            )
            self.assertEqual(second_claude.count(ROUTING_END), 1)

    def test_init_preserves_user_content_outside_sentinels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = pathlib.Path(tmpdir)
            target.mkdir(parents=True, exist_ok=True)
            (target / "CLAUDE.md").write_text(
                "# Project header\n\nHand-written line.\n"
            )
            _run(["init", tmpdir])
            text = (target / "CLAUDE.md").read_text()
            self.assertIn("# Project header", text)
            self.assertIn("Hand-written line.", text)
            self.assertIn(ROUTING_BEGIN, text)


class InstallHookTests(unittest.TestCase):
    def test_install_hook_standalone_creates_managed_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo, with_hooks_path=True)
            result = _run(["install-hook", tmpdir])
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            hook = repo / ".git" / "hooks" / "pre-push"
            self.assertTrue(hook.is_file())
            self.assertIn(HOOK_BEGIN, hook.read_text())

    def test_install_hook_re_run_updates_managed_block_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo, with_hooks_path=True)
            _run(["install-hook", tmpdir])

            second = _run(["install-hook", tmpdir])
            self.assertEqual(second.returncode, 0, msg=second.stderr)

            hook_text = (repo / ".git" / "hooks" / "pre-push").read_text()
            self.assertEqual(
                hook_text.count(HOOK_BEGIN), 1,
                msg=f"hook block duplicated:\n{hook_text}",
            )
            self.assertEqual(hook_text.count(HOOK_END), 1)

    def test_install_hook_outside_git_repo_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run(["install-hook", tmpdir])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("git repository not found", result.stdout + result.stderr)


class FreshnessAdvisoryTests(unittest.TestCase):
    def test_freshness_command_exits_zero_even_when_underlying_fails(self) -> None:
        """`agent-context freshness` is advisory: never propagates exit non-zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "src/app.py", "v1\n")
            commit_all(repo, "base")
            write_file(repo, "src/app.py", "v2\n")
            commit_all(repo, "code only")  # underlying script returns 1

            result = _run(["freshness", "--base-ref", "HEAD~1", tmpdir])
            self.assertEqual(
                result.returncode, 0,
                msg=f"freshness CLI must exit 0 (advisory). stdout={result.stdout!r} stderr={result.stderr!r}",
            )
            self.assertIn("advisory", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
