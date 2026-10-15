"""Canonical routing layout coverage.

`--layout canonical` writes one AGENTS.md shared by every agent and a
CLAUDE.md whose managed block starts with a literal, unfenced `@AGENTS.md`
import. GEMINI.md is opt-in, .cursorrules is only refreshed when present,
unmanaged text survives, and re-running is a no-op. The per-agent layout
remains available explicitly for legacy callers.
"""

from __future__ import annotations

import pathlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "bin" / "agent-context"
BEGIN = "<!-- agent-context:begin -->"
END = "<!-- agent-context:end -->"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, check=False)


def _managed(text: str) -> str:
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


class CanonicalLayoutTests(unittest.TestCase):
    def _pack(self, tmp: str, tier: int = 3) -> pathlib.Path:
        root = pathlib.Path(tmp)
        r = _run("init", "--tier", str(tier), "--layout", "canonical", str(root))
        self.assertEqual(r.returncode, 0, r.stderr)
        return root

    def test_init_canonical_writes_agents_and_claude_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "CLAUDE.md").exists())
            self.assertFalse((root / "GEMINI.md").exists())
            self.assertFalse((root / ".cursorrules").exists())

    def test_claude_block_starts_with_literal_unfenced_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            text = (root / "CLAUDE.md").read_text()
            lines = text.splitlines()
            self.assertEqual(lines[0], BEGIN)
            self.assertEqual(lines[1], "@AGENTS.md")
            self.assertNotIn("```", text)

    def test_agents_block_carries_merged_flow_and_untrusted_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            block = _managed((root / "AGENTS.md").read_text())
            for needle in ("00_START_HERE.md", "routes.json", "completeness_contract.json",
                           "search_scope.json", "30_BEHAVIORAL_INVARIANTS.md", "20_CODE_MAP.md",
                           "reporting_rules.json", "Untrusted content", "read_order"):
                self.assertIn(needle, block)
            self.assertNotIn("work/", block)
            self.assertNotIn("play/", block)

    def test_tier_changes_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp, tier=1)
            block = _managed((root / "AGENTS.md").read_text())
            self.assertIn("20_CODE_MAP.md", block)
            self.assertNotIn("routes.json", block)

    def test_gemini_opt_in_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            (root / "GEMINI.md").write_text("teammate text\n")
            r = _run("routing", "--layout", "canonical", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((root / "GEMINI.md").read_text(), "teammate text\n")
            r = _run("routing", "--layout", "canonical", "--include-gemini", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (root / "GEMINI.md").read_text()
            self.assertIn("Follow AGENTS.md", _managed(text))
            self.assertIn("teammate text", text)

    def test_cursorrules_refreshed_only_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            self.assertFalse((root / ".cursorrules").exists())
            (root / ".cursorrules").write_text(f"{BEGIN}\nold\n{END}\n")
            r = _run("routing", "--layout", "canonical", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Follow AGENTS.md", _managed((root / ".cursorrules").read_text()))

    def test_routing_is_idempotent_and_preserves_unmanaged_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            agents = root / "AGENTS.md"
            agents.write_text(agents.read_text() + "\nRepo-specific rules:\n- keep me\n")
            claude = root / "CLAUDE.md"
            claude.write_text(claude.read_text() + "\nClaude note: keep me too\n")
            before = (agents.read_bytes(), claude.read_bytes())
            r = _run("routing", "--layout", "canonical", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("0 file(s) changed", r.stdout)
            self.assertEqual((agents.read_bytes(), claude.read_bytes()), before)
            self.assertIn("- keep me", agents.read_text())
            self.assertIn("Claude note: keep me too", claude.read_text())

    def test_routing_migrates_per_agent_pack_to_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            r = _run("init", "--tier", "3", "--layout", "per-agent", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((root / "GEMINI.md").exists())
            gemini_before = (root / "GEMINI.md").read_bytes()
            r = _run("routing", "--layout", "canonical", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((root / "CLAUDE.md").read_text().splitlines()[1], "@AGENTS.md")
            self.assertIn("routes.json", _managed((root / "AGENTS.md").read_text()))
            self.assertIn("Follow AGENTS.md", _managed((root / ".cursorrules").read_text()))
            # A legacy managed GEMINI.md must not keep the old per-agent policy.
            self.assertNotEqual((root / "GEMINI.md").read_bytes(), gemini_before)
            self.assertIn("Follow AGENTS.md", _managed((root / "GEMINI.md").read_text()))
            self.assertNotIn("read these 3 files", (root / "GEMINI.md").read_text())

    def test_routing_reads_tier_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _run("init", "--tier", "2", str(root))
            r = _run("routing", "--layout", "canonical", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 2)", r.stdout)
            self.assertNotIn("routes.json", _managed((root / "AGENTS.md").read_text()))

    def test_routing_legacy_eight_file_pack_routes_as_tier_2(self) -> None:
        """Pre-0.5 filled pack: tier-2 files plus overview/operations, no authority files, no recorded tier.

        Regression for the installed-wheel smoke failure where routing inferred tier 3 from
        10_SYSTEM_OVERVIEW.md and refused the pack as incomplete. The verifier calls this shape
        tier 2; routing must agree and only reference files the pack ships.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "hello-service"
            shutil.copytree(REPO_ROOT / "examples" / "hello-service", root)
            current = root / ".agent-context" / "current"
            self.assertNotIn("tier", json.loads((current / "manifest.json").read_text()))
            self.assertTrue((current / "10_SYSTEM_OVERVIEW.md").exists())
            self.assertFalse((current / "routes.json").exists())
            before = {p.name: p.read_bytes() for p in current.iterdir()}
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 2)", r.stdout)
            self.assertIn("inferred from pack files", r.stdout)
            self.assertEqual(before, {p.name: p.read_bytes() for p in current.iterdir()})
            block = _managed((root / "AGENTS.md").read_text())
            for shipped in ("00_START_HERE.md", "30_BEHAVIORAL_INVARIANTS.md", "20_CODE_MAP.md", "search_scope.json"):
                self.assertIn(shipped, block)
            for absent in ("routes.json", "completeness_contract.json", "reporting_rules.json"):
                self.assertNotIn(absent, block)
            self.assertEqual(_managed((root / "CLAUDE.md").read_text()).splitlines()[0], "@AGENTS.md")
            r = _run("verify", str(root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("tier 2", r.stdout)

    def test_routing_infers_tier_3_when_manifest_omits_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            manifest_path = root / ".agent-context/current/manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest.pop("tier")
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 3)", r.stdout)
            self.assertIn("routes.json", _managed((root / "AGENTS.md").read_text()))

    def test_unrecorded_pack_missing_one_authority_file_routes_to_shipped_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            manifest_path = root / ".agent-context/current/manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest.pop("tier")
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            (root / ".agent-context/current/reporting_rules.json").unlink()
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 2)", r.stdout)
            self.assertNotIn("reporting_rules.json", _managed((root / "AGENTS.md").read_text()))

    def test_recorded_tier_3_missing_authority_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            (root / ".agent-context/current/routes.json").unlink()
            before = (root / "AGENTS.md").read_bytes()
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("routes.json", r.stderr)
            self.assertEqual(before, (root / "AGENTS.md").read_bytes())

    def test_tier_precedence_explicit_over_manifest_over_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)  # 11 files on disk: inference alone would say tier 3
            manifest_path = root / ".agent-context/current/manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["tier"] = 2
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 2)", r.stdout)
            self.assertNotIn("inferred", r.stdout)
            self.assertNotIn("routes.json", _managed((root / "AGENTS.md").read_text()))
            r = _run("routing", "--tier", "1", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(tier 1)", r.stdout)
            self.assertNotIn("30_BEHAVIORAL_INVARIANTS.md", _managed((root / "AGENTS.md").read_text()))

    def test_routing_preserves_crlf_line_endings_and_unmanaged_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            claude = root / "CLAUDE.md"
            claude.write_bytes(b"hello\r\nworld\r\n")
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            data = claude.read_bytes()
            self.assertTrue(data.startswith(BEGIN.encode() + b"\r\n@AGENTS.md\r\n"))
            self.assertTrue(data.endswith(b"\r\nhello\r\nworld\r\n"))
            self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), "no bare LF introduced")
            again = _run("routing", str(root))
            self.assertIn("0 file(s) changed", again.stdout)
            self.assertEqual(claude.read_bytes(), data)
            r = _run("verify", str(root))
            self.assertNotIn("CLAUDE.md does not reference", r.stdout + r.stderr)

    def test_gemini_without_managed_block_is_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            (root / "GEMINI.md").write_text("# Handwritten Gemini notes\n")
            r = _run("routing", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((root / "GEMINI.md").read_text(), "# Handwritten Gemini notes\n")

    def test_routing_requires_existing_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            r = _run("routing", "--layout", "canonical", tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("init", r.stderr)

    def test_per_agent_explicit_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            r = _run("init", "--tier", "3", "--layout", "per-agent", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("@AGENTS.md", (root / "CLAUDE.md").read_text())
            self.assertTrue((root / "GEMINI.md").exists())
            self.assertTrue((root / ".cursorrules").exists())

    def test_default_init_and_routing_are_canonical_for_every_tier(self) -> None:
        for tier in (1, 2, 3):
            with self.subTest(tier=tier), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                self.assertEqual(_run("init", "--tier", str(tier), tmp).returncode, 0)
                before = {p.name: p.read_bytes() for p in (root / ".agent-context/current").iterdir()}
                result = _run("routing", tmp)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"(tier {tier})", result.stdout)
                self.assertIn("0 file(s) changed", result.stdout)
                self.assertEqual(before, {p.name: p.read_bytes() for p in (root / ".agent-context/current").iterdir()})
                self.assertEqual(_managed((root / "CLAUDE.md").read_text()).splitlines()[0], "@AGENTS.md")
                self.assertFalse((root / "GEMINI.md").exists())

    def test_invalid_manifest_fails_without_changing_routing(self) -> None:
        for content in ('{broken', '[]', '{"tier": 0}', '{"tier": 4}', '{"tier": true}', '{"tier": "2"}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                root = self._pack(tmp)
                before = {p.name: p.read_bytes() for p in (root / "AGENTS.md", root / "CLAUDE.md")}
                (root / ".agent-context/current/manifest.json").write_text(content)
                result = _run("routing", tmp)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(before, {p.name: p.read_bytes() for p in (root / "AGENTS.md", root / "CLAUDE.md")})

    def test_missing_pack_reference_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            (root / ".agent-context/current/30_BEHAVIORAL_INVARIANTS.md").unlink()
            before = (root / "AGENTS.md").read_bytes()
            result = _run("routing", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("30_BEHAVIORAL_INVARIANTS.md", result.stderr)
            self.assertEqual(before, (root / "AGENTS.md").read_bytes())

    def test_ambiguous_targets_are_rejected_before_any_write(self) -> None:
        for kind in ("symlink", "hardlink", "directory", "missing-end", "duplicate", "reversed"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = self._pack(tmp)
                agents, claude = root / "AGENTS.md", root / "CLAUDE.md"
                # Make the first destination require an update, so a partial
                # writer would alter it before noticing the second problem.
                agents.write_text(f"{BEGIN}\nold routing\n{END}\nUser policy\n")
                claude.unlink()
                if kind == "symlink": claude.symlink_to("AGENTS.md")
                elif kind == "hardlink": os.link(agents, claude)
                elif kind == "directory": claude.mkdir()
                elif kind == "missing-end": claude.write_text(BEGIN + "\nnotes\n")
                elif kind == "duplicate": claude.write_text((BEGIN + "\nnotes\n" + END + "\n") * 2)
                else: claude.write_text(END + "\nnotes\n" + BEGIN)
                before = agents.read_bytes()
                result = _run("routing", tmp)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertEqual(before, agents.read_bytes())

    def test_init_preflights_before_replacing_filled_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            pack = root / ".agent-context/current/20_CODE_MAP.md"
            pack.write_text("Maintainer-authored content\n")
            (root / "CLAUDE.md").unlink()
            (root / "CLAUDE.md").symlink_to("AGENTS.md")
            result = _run("init", "--force", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(pack.read_text(), "Maintainer-authored content\n")

    def test_verify_accepts_canonical_layout_and_rejects_bare_pointer_without_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            r = _run("verify", str(root))
            self.assertNotIn("CLAUDE.md does not reference", r.stdout + r.stderr)
            # Break the import target: CLAUDE.md now points at nothing useful.
            (root / "AGENTS.md").write_text("unrelated\n")
            r = _run("verify", str(root))
            self.assertIn("CLAUDE.md does not reference", r.stdout + r.stderr)

    def test_verify_resolves_gemini_pointer_through_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._pack(tmp)
            r = _run("routing", "--layout", "canonical", "--include-gemini", str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run("verify", str(root))
            self.assertNotIn("GEMINI.md does not reference", r.stdout + r.stderr)

    def test_verify_does_not_treat_claude_prose_or_code_examples_as_imports(self) -> None:
        for adapter in ("Follow AGENTS.md", "```text\n@AGENTS.md\n```", "~~~\n@AGENTS.md\n~~~", "`@AGENTS.md`",
                        "    @AGENTS.md", "\t@AGENTS.md", "<!--\n@AGENTS.md\n-->"):
            with self.subTest(adapter=adapter), tempfile.TemporaryDirectory() as tmp:
                root = self._pack(tmp)
                (root / "CLAUDE.md").write_text(adapter + "\n")
                r = _run("verify", str(root))
                self.assertIn("CLAUDE.md does not reference", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
