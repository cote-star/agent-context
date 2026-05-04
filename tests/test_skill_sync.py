"""Guard against drift between root SKILL.md and the installable skill copy."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ROOT_SKILL = REPO_ROOT / "SKILL.md"
INSTALLABLE_SKILL = REPO_ROOT / "skills" / "agent-context" / "SKILL.md"


class SkillSyncTest(unittest.TestCase):
    def test_root_and_installable_skill_are_byte_identical(self) -> None:
        self.assertTrue(ROOT_SKILL.exists(), f"missing: {ROOT_SKILL}")
        self.assertTrue(INSTALLABLE_SKILL.exists(), f"missing: {INSTALLABLE_SKILL}")
        root = ROOT_SKILL.read_bytes()
        installable = INSTALLABLE_SKILL.read_bytes()
        self.assertEqual(
            root,
            installable,
            "SKILL.md and skills/agent-context/SKILL.md have drifted. "
            "Update one to match the other (or replace the duplicate with a symlink) "
            "so the installable skill stays in sync with the public source-of-truth.",
        )


if __name__ == "__main__":
    unittest.main()
