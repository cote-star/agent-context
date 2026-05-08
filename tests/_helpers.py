"""Shared subprocess + git helpers for the test suite.

Tests that drive a real `git` process need the same deterministic identity
and a clean signing config to be reproducible across machines and CI. These
helpers consolidate that boilerplate so individual tests stay focused on
behaviour rather than environment plumbing.
"""

from __future__ import annotations

import os
import pathlib
import subprocess


def git_env() -> dict:
    """Deterministic env so commits don't depend on the host's git config."""
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }


def git(repo: pathlib.Path, *args: str) -> None:
    """Run a git command in `repo` with the deterministic identity env."""
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        env=git_env(),
    )


def init_git_repo(repo: pathlib.Path, with_hooks_path: bool = False) -> None:
    """`git init` with a known default branch and signing disabled.

    `with_hooks_path=True` pins `core.hooksPath` to `.git/hooks` so hook tests
    don't get blindsided by a host-level `core.hooksPath` override.
    """
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "commit.gpgsign", "false")
    if with_hooks_path:
        git(repo, "config", "core.hooksPath", ".git/hooks")


def commit_all(repo: pathlib.Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, "--allow-empty")


def write_file(repo: pathlib.Path, rel: str, body: str = "x\n") -> None:
    """Create parent dirs as needed and write `body` at `repo/rel`."""
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
