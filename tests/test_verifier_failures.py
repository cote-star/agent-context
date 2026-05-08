"""Verifier failure-mode coverage.

Each test copies `examples/hello-service` (a tier-2 pack) into a tmpdir,
mutates exactly one field to inject a known violation, and asserts the
verifier surfaces the expected error. Tier-3-only validators (contracts
and the authority manifest list) are not yet covered here; they're
implicitly exercised through `init --tier 3` in `test_init_tiers.py`.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "bin" / "agent-context"
HELLO = REPO_ROOT / "examples" / "hello-service"


def _verify(target: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "verify", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )


def _copy_hello(tmpdir: str) -> pathlib.Path:
    """Copy the worked example into tmpdir/repo and return its path."""
    dest = pathlib.Path(tmpdir) / "repo"
    shutil.copytree(HELLO, dest)
    return dest


def _read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


class TemplateMarkerTests(unittest.TestCase):
    def test_template_marker_in_search_scope_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            scope = repo / ".agent-context" / "current" / "search_scope.json"
            data = _read_json(scope)
            data["task_families"]["feature_work"]["description"] = "REPLACE this"
            _write_json(scope, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("template marker", result.stdout)

    def test_template_marker_in_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            manifest = repo / ".agent-context" / "current" / "manifest.json"
            data = _read_json(manifest)
            data["repo"] = "{module}"
            _write_json(manifest, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("template marker", result.stdout)


class ManifestTests(unittest.TestCase):
    def test_manifest_missing_version_key_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            manifest = repo / ".agent-context" / "current" / "manifest.json"
            data = _read_json(manifest)
            del data["version"]
            _write_json(manifest, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest", result.stdout)
            self.assertIn("version", result.stdout)

    def test_manifest_files_content_must_be_nonempty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            manifest = repo / ".agent-context" / "current" / "manifest.json"
            data = _read_json(manifest)
            data["files"]["content"] = []
            _write_json(manifest, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest", result.stdout)
            self.assertIn("content", result.stdout)


class SearchScopeTests(unittest.TestCase):
    def test_example_task_family_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            scope = repo / ".agent-context" / "current" / "search_scope.json"
            data = _read_json(scope)
            data["task_families"]["_EXAMPLE_leftover"] = {
                "description": "leftover example",
                "search_directories": ["src"],
                "exclude_from_search": [],
                "verification_shortcuts": [],
            }
            _write_json(scope, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            # Match on the unique identifier rather than the full sentence.
            self.assertIn("_EXAMPLE_leftover", result.stdout)

    def test_missing_search_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            scope = repo / ".agent-context" / "current" / "search_scope.json"
            data = _read_json(scope)
            data["task_families"]["feature_work"]["search_directories"].append(
                "does/not/exist"
            )
            _write_json(scope, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing search directory: does/not/exist", result.stdout)

    def test_look_for_string_must_appear_in_target_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            scope = repo / ".agent-context" / "current" / "search_scope.json"
            data = _read_json(scope)
            data["task_families"]["feature_work"]["verification_shortcuts"][0][
                "look_for"
            ] = "definitely_not_in_the_source"
            _write_json(scope, data)

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("look_for string not found", result.stdout)


class RoutingFileTests(unittest.TestCase):
    def test_claude_md_without_any_context_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            (repo / "CLAUDE.md").write_text(
                "# Project notes\n\nNothing here references the agent-context pack.\n"
            )
            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("CLAUDE.md", result.stdout)
            self.assertIn("reference", result.stdout)

    def test_claude_md_must_reference_invariants_at_tier_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            (repo / "CLAUDE.md").write_text(
                "Read .agent-context/current/00_START_HERE.md and "
                ".agent-context/current/20_CODE_MAP.md before starting.\n"
            )
            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("CLAUDE.md", result.stdout)
            self.assertIn("30_BEHAVIORAL_INVARIANTS.md", result.stdout)


class CoverageTests(unittest.TestCase):
    """The coverage validator scans for significant source dirs missing from the pack."""

    def _add_significant_dir(self, repo: pathlib.Path, name: str) -> None:
        # Place a feature-style subdirectory under src/ with enough code files to
        # trip MIN_SIGNIFICANT_CODE_FILES (3) and qualify as a feature parent.
        feature_dir = repo / "src" / "features" / name
        feature_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (feature_dir / f"mod_{i}.py").write_text(f"def fn_{i}():\n    pass\n")

    def test_significant_dir_absent_from_pack_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            self._add_significant_dir(repo, "billing")

            result = _verify(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("coverage check", result.stdout)
            self.assertIn("billing", result.stdout)

    def test_significant_dir_under_not_covered_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = _copy_hello(tmpdir)
            self._add_significant_dir(repo, "billing")

            # Augment the existing "Not Covered in Detail" section instead of
            # appending a second one — extract_markdown_section only matches
            # the first occurrence.
            start_here = repo / ".agent-context" / "current" / "00_START_HERE.md"
            text = start_here.read_text()
            text = text.replace(
                "## Not Covered in Detail\n",
                "## Not Covered in Detail\n\n- src/features/billing — out of scope for the worked example\n",
                1,
            )
            start_here.write_text(text)

            result = _verify(repo)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"verify failed unexpectedly: {result.stdout}\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
