"""Per-tier init coverage.

Confirms `agent-context init --tier {1,2,3}` copies the right templates and
writes the right routing-block content. The tier flag is the only switch a
user sets at adoption time, so each tier must produce a coherent pack on
its own.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "bin" / "agent-context"

TIER_1_FILES = {"20_CODE_MAP.md", "search_scope.json"}
TIER_2_FILES = TIER_1_FILES | {
    "00_START_HERE.md",
    "30_BEHAVIORAL_INVARIANTS.md",
    "manifest.json",
    "acceptance_tests.md",
}
TIER_3_FILES = TIER_2_FILES | {
    "10_SYSTEM_OVERVIEW.md",
    "40_OPERATIONS_AND_RELEASE.md",
    "routes.json",
    "completeness_contract.json",
    "reporting_rules.json",
}


def _init(target: str, tier: int, force: bool = False) -> subprocess.CompletedProcess:
    args = [sys.executable, str(CLI), "init", "--tier", str(tier)]
    if force:
        args.append("--force")
    args.append(target)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _content_files(target: pathlib.Path) -> set[str]:
    current = target / ".agent-context" / "current"
    return {p.name for p in current.iterdir() if p.is_file()}


class Tier1InitTests(unittest.TestCase):
    def test_copies_only_two_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _init(tmpdir, 1)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(_content_files(pathlib.Path(tmpdir)), TIER_1_FILES)

    def test_writes_simple_claude_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 1)
            claude = (pathlib.Path(tmpdir) / "CLAUDE.md").read_text()
            # Tier 1 routing points at the code map only; it must not mention
            # the tier-2+ files because those are absent from the pack.
            self.assertIn("20_CODE_MAP.md", claude)
            self.assertNotIn("00_START_HERE.md", claude)
            self.assertNotIn("30_BEHAVIORAL_INVARIANTS.md", claude)

    def test_writes_simple_agents_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 1)
            agents = (pathlib.Path(tmpdir) / "AGENTS.md").read_text()
            self.assertIn("20_CODE_MAP.md", agents)
            self.assertNotIn("routes.json", agents)
            self.assertNotIn("completeness_contract.json", agents)


class Tier2InitTests(unittest.TestCase):
    def test_copies_six_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _init(tmpdir, 2)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(_content_files(pathlib.Path(tmpdir)), TIER_2_FILES)

    def test_writes_full_claude_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 2)
            claude = (pathlib.Path(tmpdir) / "CLAUDE.md").read_text()
            # Tier 2+ routing references the 3-file read order.
            self.assertIn("00_START_HERE.md", claude)
            self.assertIn("30_BEHAVIORAL_INVARIANTS.md", claude)
            self.assertIn("20_CODE_MAP.md", claude)

    def test_does_not_use_authority_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 2)
            agents = (pathlib.Path(tmpdir) / "AGENTS.md").read_text()
            # Tier 2 has no authority files — AGENTS.md must not point to them.
            self.assertNotIn("routes.json", agents)
            self.assertNotIn("completeness_contract.json", agents)


class Tier3InitTests(unittest.TestCase):
    def test_copies_full_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _init(tmpdir, 3)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(_content_files(pathlib.Path(tmpdir)), TIER_3_FILES)

    def test_writes_authority_agents_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 3)
            agents = (pathlib.Path(tmpdir) / "AGENTS.md").read_text()
            self.assertIn("routes.json", agents)
            self.assertIn("completeness_contract.json", agents)
            self.assertIn("search_scope.json", agents)

    def test_manifest_records_tier_3(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 3)
            import json

            manifest = json.loads(
                (pathlib.Path(tmpdir) / ".agent-context" / "current" / "manifest.json").read_text()
            )
            self.assertEqual(manifest.get("tier"), 3)


class TierDowngradeTests(unittest.TestCase):
    """`init --force --tier N` must reset the pack to tier N, not leave stale higher-tier files."""

    def test_force_downgrade_3_to_1_removes_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 3)
            _init(tmpdir, 1, force=True)
            self.assertEqual(_content_files(pathlib.Path(tmpdir)), TIER_1_FILES)

    def test_force_downgrade_3_to_2_removes_authority_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _init(tmpdir, 3)
            _init(tmpdir, 2, force=True)
            self.assertEqual(_content_files(pathlib.Path(tmpdir)), TIER_2_FILES)


if __name__ == "__main__":
    unittest.main()
