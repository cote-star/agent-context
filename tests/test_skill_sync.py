"""Guard against drift between root SKILL.md/templates/tools and the installable skill copy.

The installable skill at `skills/agent-context/` is bundled with its own
`templates/` and `tools/` so a fresh install (`cp -r skills/agent-context
~/.claude/skills/`) is self-contained: SKILL.md, the starter templates it
references, and the helper tools it copies into `.agent-context/tools/` are
all present without needing the rest of the repo on disk.

These tests catch silent drift between the canonical root copies and the
bundled-in-skill copies.
"""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "agent-context"

BUNDLED_TOOLS = ("verify_agent_context.py", "check_freshness.sh", "pre-push-hook.sh")


class SkillSyncTest(unittest.TestCase):
    def test_root_and_installable_skill_md_are_byte_identical(self) -> None:
        root_skill = REPO_ROOT / "SKILL.md"
        installable_skill = SKILL_ROOT / "SKILL.md"
        self.assertTrue(root_skill.exists(), f"missing: {root_skill}")
        self.assertTrue(installable_skill.exists(), f"missing: {installable_skill}")
        self.assertEqual(
            root_skill.read_bytes(),
            installable_skill.read_bytes(),
            "SKILL.md and skills/agent-context/SKILL.md have drifted. "
            "Update one to match the other so the installable skill stays in sync "
            "with the public source-of-truth.",
        )

    def test_root_templates_match_bundled_skill_templates(self) -> None:
        root_dir = REPO_ROOT / "templates"
        bundled_dir = SKILL_ROOT / "templates"
        self.assertTrue(root_dir.is_dir(), f"missing: {root_dir}")
        self.assertTrue(
            bundled_dir.is_dir(),
            f"missing bundled templates dir at {bundled_dir} - the installable "
            "skill must ship its own copy of templates/ so a fresh install is "
            "self-contained.",
        )
        root_files = sorted(p.name for p in root_dir.iterdir() if p.is_file())
        bundled_files = sorted(p.name for p in bundled_dir.iterdir() if p.is_file())
        self.assertEqual(
            root_files,
            bundled_files,
            "templates/ file lists differ between repo root and the installable skill. "
            "Add or remove the same file in both locations.",
        )
        for name in root_files:
            self.assertEqual(
                (root_dir / name).read_bytes(),
                (bundled_dir / name).read_bytes(),
                f"templates/{name} differs between repo root and skills/agent-context/. "
                "Update one to match the other.",
            )

    def test_bundled_skill_tools_match_root_tools(self) -> None:
        root_dir = REPO_ROOT / "tools"
        bundled_dir = SKILL_ROOT / "tools"
        self.assertTrue(root_dir.is_dir(), f"missing: {root_dir}")
        self.assertTrue(
            bundled_dir.is_dir(),
            f"missing bundled tools dir at {bundled_dir} - the installable skill "
            "must ship the helper tools it tells the agent to copy "
            "(verify_agent_context.py, check_freshness.sh, pre-push-hook.sh).",
        )
        for name in BUNDLED_TOOLS:
            root_file = root_dir / name
            bundled_file = bundled_dir / name
            self.assertTrue(root_file.exists(), f"missing in repo root: {root_file}")
            self.assertTrue(
                bundled_file.exists(),
                f"missing in installable skill: {bundled_file} - bundle this helper "
                "tool with the skill so a fresh install is self-contained.",
            )
            self.assertEqual(
                root_file.read_bytes(),
                bundled_file.read_bytes(),
                f"tools/{name} differs between repo root and skills/agent-context/. "
                "Update one to match the other.",
            )


if __name__ == "__main__":
    unittest.main()
