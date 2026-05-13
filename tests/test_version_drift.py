"""Guard against version drift across CLI, SKILL.md frontmatter, README badge, and pyproject.

Catches the regression where a release tag advances but ancillary version
surfaces (skill metadata, README badge, packaging metadata) lag behind. The CLI
``__version__`` in ``agent_context/cli.py`` is the source of truth; every other
surface must match.
"""

from __future__ import annotations

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

CLI_VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)
SKILL_VERSION_RE = re.compile(r'^metadata:\n  version:\s*"([^"]+)"', re.MULTILINE)
BADGE_VERSION_RE = re.compile(r"badge/version-([0-9][0-9A-Za-z.\-]*)-")
PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _cli_version() -> str:
    text = (REPO_ROOT / "agent_context" / "cli.py").read_text()
    match = CLI_VERSION_RE.search(text)
    if not match:
        raise AssertionError("could not find __version__ in agent_context/cli.py")
    return match.group(1)


def _skill_frontmatter_version(skill_path: pathlib.Path) -> str:
    match = SKILL_VERSION_RE.search(skill_path.read_text())
    if not match:
        raise AssertionError(f"could not find frontmatter version in {skill_path}")
    return match.group(1)


def _readme_badge_version() -> str:
    match = BADGE_VERSION_RE.search((REPO_ROOT / "README.md").read_text())
    if not match:
        raise AssertionError("could not find version badge in README.md")
    return match.group(1)


def _pyproject_version() -> str:
    match = PYPROJECT_VERSION_RE.search((REPO_ROOT / "pyproject.toml").read_text())
    if not match:
        raise AssertionError("could not find version in pyproject.toml")
    return match.group(1)


class VersionDriftTests(unittest.TestCase):
    """All version surfaces must agree with agent_context/cli.py __version__."""

    def test_root_skill_md_version_matches_cli(self) -> None:
        cli = _cli_version()
        skill = _skill_frontmatter_version(REPO_ROOT / "SKILL.md")
        self.assertEqual(
            cli,
            skill,
            f"agent_context/cli.py __version__={cli!r} does not match "
            f"SKILL.md frontmatter version={skill!r}. Bump both together.",
        )

    def test_installable_skill_md_version_matches_cli(self) -> None:
        cli = _cli_version()
        skill = _skill_frontmatter_version(
            REPO_ROOT / "skills" / "agent-context" / "SKILL.md"
        )
        self.assertEqual(
            cli,
            skill,
            f"agent_context/cli.py __version__={cli!r} does not match "
            f"skills/agent-context/SKILL.md frontmatter version={skill!r}.",
        )

    def test_readme_badge_version_matches_cli(self) -> None:
        cli = _cli_version()
        badge = _readme_badge_version()
        self.assertEqual(
            cli,
            badge,
            f"agent_context/cli.py __version__={cli!r} does not match "
            f"README.md version badge={badge!r}. Update the badge URL on bumps.",
        )

    def test_pyproject_version_matches_cli(self) -> None:
        cli = _cli_version()
        pyproject = _pyproject_version()
        self.assertEqual(
            cli,
            pyproject,
            f"agent_context/cli.py __version__={cli!r} does not match "
            f"pyproject.toml version={pyproject!r}. Bump both together.",
        )


if __name__ == "__main__":
    unittest.main()
