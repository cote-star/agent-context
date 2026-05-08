"""Coverage for tools/check_freshness.sh.

The freshness script compares two git revs and fails when context-relevant
source files changed without a corresponding `.agent-context/` update. Each
test builds a minimal git history in a tmpdir and runs the script with a
known --base-ref so behaviour is deterministic regardless of the surrounding
environment.
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from tests._helpers import commit_all, init_git_repo, write_file


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "check_freshness.sh"


def _run_in(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(SCRIPT), *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


class FreshnessTests(unittest.TestCase):
    def test_no_changes_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "src/app.py", "v1\n")
            commit_all(repo, "base")
            commit_all(repo, "empty advance")  # HEAD differs from base, no diff content

            result = _run_in(repo, "--base-ref", "HEAD~1")
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)

    def test_code_change_with_pack_change_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "src/app.py", "v1\n")
            write_file(repo, ".agent-context/current/20_CODE_MAP.md", "# v1\n")
            commit_all(repo, "base")

            write_file(repo, "src/app.py", "v2\n")
            write_file(repo, ".agent-context/current/20_CODE_MAP.md", "# v2\n")
            commit_all(repo, "code + pack updated")

            result = _run_in(repo, "--base-ref", "HEAD~1")
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_pack_change_only_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "src/app.py", "v1\n")
            commit_all(repo, "base")

            write_file(repo, ".agent-context/current/20_CODE_MAP.md", "# new\n")
            commit_all(repo, "pack only")

            result = _run_in(repo, "--base-ref", "HEAD~1")
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_code_change_without_pack_change_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "src/app.py", "v1\n")
            commit_all(repo, "base")

            write_file(repo, "src/app.py", "v2\n")
            commit_all(repo, "code only")

            result = _run_in(repo, "--base-ref", "HEAD~1")
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR", result.stdout)
            self.assertIn(".agent-context/", result.stdout)

    def test_paths_override_targets_custom_directory(self) -> None:
        """A repo whose code lives outside the default paths still gets gated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            write_file(repo, "domain/handlers.py", "v1\n")
            commit_all(repo, "base")

            write_file(repo, "domain/handlers.py", "v2\n")
            commit_all(repo, "code only")

            # With default paths (app/ src/ lib/ migrations/) the change is invisible.
            default = _run_in(repo, "--base-ref", "HEAD~1")
            self.assertEqual(default.returncode, 0)

            # With --paths domain/ the same change is now context-relevant and fails.
            override = _run_in(repo, "--base-ref", "HEAD~1", "--paths", "domain/")
            self.assertEqual(override.returncode, 1)
            self.assertIn("ERROR", override.stdout)

    def test_unknown_argument_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = pathlib.Path(tmpdir)
            init_git_repo(repo)
            commit_all(repo, "base")

            result = _run_in(repo, "--bogus")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown argument", result.stderr)


if __name__ == "__main__":
    unittest.main()
