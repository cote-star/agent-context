"""agent-context CLI — author, verify, and maintain agent-context artifacts.

Stdlib-only Python 3.8+. Subcommands:

    agent-context init [path] [--force] [--tier 1|2|3] [--install-hook]
    agent-context verify [path]
    agent-context doctor
    agent-context freshness [path] [--base-ref origin/main]
    agent-context install-hook [path]
    agent-context install-skill [--agent claude|codex|cursor] [--dest PATH] [--force] [--dry-run]
    agent-context --version
    agent-context --help

Data layout: templates/, tools/, and skill/ live as siblings of this module
inside the installed package. During development those siblings are symlinks
to the canonical repo-root directories; in an installed wheel they are real
files. Either way, ``pathlib.Path(__file__).parent / "templates"`` finds them.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Optional, Tuple


__version__ = "0.4.1"


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

TIER_1_TEMPLATES = [
    "20_CODE_MAP.md",
    "search_scope.json",
]

TIER_2_TEMPLATES = TIER_1_TEMPLATES + [
    "00_START_HERE.md",
    "30_BEHAVIORAL_INVARIANTS.md",
    "manifest.json",
    "acceptance_tests.md",
]

TIER_3_TEMPLATES = TIER_2_TEMPLATES + [
    "10_SYSTEM_OVERVIEW.md",
    "40_OPERATIONS_AND_RELEASE.md",
    "routes.json",
    "completeness_contract.json",
    "reporting_rules.json",
]

TIER_MAP = {1: TIER_1_TEMPLATES, 2: TIER_2_TEMPLATES, 3: TIER_3_TEMPLATES}


# ---------------------------------------------------------------------------
# Routing block templates
# ---------------------------------------------------------------------------

SENTINEL_BEGIN = "<!-- agent-context:begin -->"
SENTINEL_END = "<!-- agent-context:end -->"
HOOK_SENTINEL_BEGIN = "# agent-context:pre-push:begin"
HOOK_SENTINEL_END = "# agent-context:pre-push:end"

CLAUDE_ROUTING = """\
BEFORE starting any task, read these 3 files in order:
1. .agent-context/current/00_START_HERE.md
2. .agent-context/current/30_BEHAVIORAL_INVARIANTS.md
3. .agent-context/current/20_CODE_MAP.md
Do NOT open repo source files until steps 1-3 are complete.
Then open only files .agent-context identifies as relevant to your task."""

CLAUDE_ROUTING_TIER1 = """\
BEFORE starting any task, read .agent-context/current/20_CODE_MAP.md.
Do NOT open repo source files until you have read the code map.
Then open only files the code map identifies as relevant to your task."""

AGENTS_ROUTING_TIER3 = """\
1. Read .agent-context/current/routes.json to identify task type
2. Load contracts from .agent-context/current/completeness_contract.json + .agent-context/current/search_scope.json
3. Search ONLY within scoped directories defined in search_scope.json
4. Do not open repo source files before step 3"""

AGENTS_ROUTING_SIMPLE = """\
1. Read .agent-context/current/20_CODE_MAP.md to identify relevant files
2. Load search boundaries from .agent-context/current/search_scope.json
3. Search ONLY within scoped directories defined in search_scope.json
4. Do not open repo source files before step 2"""


# ---------------------------------------------------------------------------
# Install-layout helpers
# ---------------------------------------------------------------------------


_MODULE_DIR = pathlib.Path(__file__).resolve().parent


def _package_data_dir() -> pathlib.Path:
    """Directory containing bundled templates/, tools/, skill/ siblings of this module."""
    return _MODULE_DIR


def _templates_dir() -> pathlib.Path:
    return _package_data_dir() / "templates"


def _tools_dir() -> pathlib.Path:
    return _package_data_dir() / "tools"


def _skill_dir() -> pathlib.Path:
    return _package_data_dir() / "skill"


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def _which(cmd: str) -> str:
    return shutil.which(cmd) or ""


def _git_head(cwd: pathlib.Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except FileNotFoundError:
        pass
    return ""


def _git_path(cwd: pathlib.Path, rel_path: str) -> Optional[pathlib.Path]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-path", rel_path],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            path = pathlib.Path(out.stdout.strip())
            if not path.is_absolute():
                path = cwd / path
            return path.resolve()
    except FileNotFoundError:
        pass
    return None


def _utc_now_iso() -> str:
    try:
        return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except AttributeError:  # pragma: no cover — ancient Python
        return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Routing block upsert
# ---------------------------------------------------------------------------


def _upsert_routing_block(file_path: pathlib.Path, content: str) -> bool:
    """Insert or replace a managed routing block in a file.

    Returns True if the file was created or modified.
    """
    block = f"{SENTINEL_BEGIN}\n{content}\n{SENTINEL_END}\n"

    if file_path.exists():
        text = file_path.read_text()
        if SENTINEL_BEGIN in text and SENTINEL_END in text:
            import re
            pattern = re.compile(
                re.escape(SENTINEL_BEGIN) + r".*?" + re.escape(SENTINEL_END),
                re.DOTALL,
            )
            new_text = pattern.sub(block.rstrip(), text)
            if new_text != text:
                file_path.write_text(new_text)
                return True
            return False
        else:
            file_path.write_text(block + "\n" + text)
            return True
    else:
        file_path.write_text(block)
        return True


def _install_pre_push_hook(target_root: pathlib.Path) -> Tuple[str, str]:
    hook_path = _git_path(target_root, "hooks/pre-push")
    if hook_path is None:
        return ("error", "git repository not found; skipping pre-push hook install")

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    block = f"""\
{HOOK_SENTINEL_BEGIN}
# Advisory only: warn when context-relevant files changed without .agent-context updates.
if [ -f ".agent-context/tools/pre-push-hook.sh" ]; then
  sh .agent-context/tools/pre-push-hook.sh "$@"
fi
{HOOK_SENTINEL_END}
"""

    if hook_path.exists():
        text = hook_path.read_text()
        if HOOK_SENTINEL_BEGIN in text and HOOK_SENTINEL_END in text:
            import re
            pattern = re.compile(
                re.escape(HOOK_SENTINEL_BEGIN) + r".*?" + re.escape(HOOK_SENTINEL_END),
                re.DOTALL,
            )
            new_text = pattern.sub(block.rstrip(), text)
            hook_path.write_text(new_text)
            hook_path.chmod(hook_path.stat().st_mode | 0o111)
            return ("updated", f"Updated managed agent-context block in {hook_path}")

        sample_path = hook_path.with_name("pre-push.agent-context.sample")
        sample_path.write_text(block)
        sample_path.chmod(0o755)
        return (
            "skipped",
            f"Existing pre-push hook preserved at {hook_path}; wrote sample chain block to {sample_path}",
        )

    hook_path.write_text("#!/bin/sh\n" + block)
    hook_path.chmod(0o755)
    return ("installed", f"Installed advisory pre-push hook at {hook_path}")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    target_root = pathlib.Path(args.path or ".").resolve()
    current = target_root / ".agent-context" / "current"
    tier = args.tier

    if current.exists() and not args.force:
        print(
            f"ERROR: {current} already exists. Re-run with --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    templates = _templates_dir()
    if not templates.is_dir():
        print(f"ERROR: templates directory not found at {templates}", file=sys.stderr)
        return 1

    allowed = set(TIER_MAP.get(tier, TIER_3_TEMPLATES))

    current.mkdir(parents=True, exist_ok=True)

    if args.force:
        for existing in current.iterdir():
            if existing.is_file() and existing.name not in allowed:
                existing.unlink()

    copied = 0
    for src in sorted(templates.iterdir()):
        if not src.is_file():
            continue
        if src.name not in allowed:
            continue
        if src.name == "manifest.json":
            manifest_text = src.read_text()
            manifest = json.loads(manifest_text)
            manifest["generated_at"] = _utc_now_iso()
            manifest["repo"] = target_root.name
            manifest["agent_context_version"] = __version__
            manifest["tier"] = tier
            manifest["git_revision"] = _git_head(target_root)
            (current / src.name).write_text(
                json.dumps(manifest, indent=2) + "\n"
            )
        else:
            shutil.copy2(src, current / src.name)
        copied += 1

    print(f"Initialized .agent-context/current/ with {copied} files (tier {tier}) at {current}")

    tools_dest = target_root / ".agent-context" / "tools"
    tools_dest.mkdir(parents=True, exist_ok=True)
    tools_copied = 0
    for tool_name in ["verify_agent_context.py", "check_freshness.sh", "pre-push-hook.sh"]:
        src = _tools_dir() / tool_name
        if src.is_file():
            shutil.copy2(src, tools_dest / tool_name)
            tools_copied += 1
    if tools_copied:
        print(f"Copied {tools_copied} helper tools to .agent-context/tools/")

    if tier >= 2:
        claude_content = CLAUDE_ROUTING
    else:
        claude_content = CLAUDE_ROUTING_TIER1

    if tier >= 3:
        agents_content = AGENTS_ROUTING_TIER3
    else:
        agents_content = AGENTS_ROUTING_SIMPLE

    routing_files = {
        "CLAUDE.md": claude_content,
        "GEMINI.md": claude_content,
        "AGENTS.md": agents_content,
        ".cursorrules": agents_content,
    }

    for filename, content in routing_files.items():
        path = target_root / filename
        if _upsert_routing_block(path, content):
            print(f"  Wrote routing block in {filename}")

    if args.install_hook:
        status, message = _install_pre_push_hook(target_root)
        label = "Hook"
        print(f"{label}: {message}")

    print("Next: fill the REPLACE markers in each template, then run `agent-context verify`.")
    return 0


def cmd_install_hook(args: argparse.Namespace) -> int:
    target_root = pathlib.Path(args.path or ".").resolve()
    tools_dest = target_root / ".agent-context" / "tools"
    tools_dest.mkdir(parents=True, exist_ok=True)

    src = _tools_dir() / "pre-push-hook.sh"
    if src.is_file():
        shutil.copy2(src, tools_dest / "pre-push-hook.sh")
        print("Copied pre-push-hook.sh to .agent-context/tools/")
    else:
        print(f"ERROR: pre-push hook template not found at {src}", file=sys.stderr)
        return 1

    status, message = _install_pre_push_hook(target_root)
    print(message)
    if status == "error":
        return 1
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    target_root = pathlib.Path(args.path or ".").resolve()
    verifier = _tools_dir() / "verify_agent_context.py"
    if not verifier.is_file():
        print(f"ERROR: verifier not found at {verifier}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, str(verifier), "--repo-root", str(target_root)],
        check=False,
    )
    return result.returncode


def cmd_doctor(args: argparse.Namespace) -> int:
    root = pathlib.Path(".").resolve()
    print(f"agent-context doctor — v{__version__}")
    print(f"  python:          {sys.version.split()[0]} ({sys.executable})")
    print(f"  git:             {_which('git') or 'NOT FOUND'}")
    jq_path = _which("jq")
    if jq_path:
        print(f"  jq:              {jq_path}")
    else:
        print("  jq:              NOT FOUND (optional, used for JSON inspection)")
    print(f"  cwd:             {root}")
    print(f"  bundled data:    {_package_data_dir()}")

    current = root / ".agent-context" / "current"
    if current.is_dir():
        file_count = sum(1 for p in current.iterdir() if p.is_file())
        has_authority = all(
            (current / f).exists()
            for f in ["routes.json", "completeness_contract.json", "reporting_rules.json"]
        )
        has_full = all(
            (current / f).exists()
            for f in ["10_SYSTEM_OVERVIEW.md", "40_OPERATIONS_AND_RELEASE.md"]
        )
        if has_authority and has_full:
            tier = 3
        elif (current / "00_START_HERE.md").exists():
            tier = 2
        else:
            tier = 1
        print(f"  agent-context:   present ({file_count} files, tier {tier})")
        freshness_script = _tools_dir() / "check_freshness.sh"
        if freshness_script.is_file():
            try:
                out = subprocess.run(
                    ["sh", str(freshness_script), "--base-ref", "HEAD~1"],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                status_line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
                print(f"  freshness:       {status_line or 'indeterminate'}")
            except Exception as exc:  # noqa: BLE001
                print(f"  freshness:       indeterminate ({exc})")
    else:
        print("  agent-context:   none (run `agent-context init`)")

    for name in ["CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules"]:
        path = root / name
        if path.exists():
            text = path.read_text()
            has_block = SENTINEL_BEGIN in text
            print(f"  {name:18s} {'routing block present' if has_block else 'exists but no routing block'}")

    hook_path = _git_path(root, "hooks/pre-push")
    if hook_path:
        if hook_path.exists():
            hook_text = hook_path.read_text()
            if HOOK_SENTINEL_BEGIN in hook_text and HOOK_SENTINEL_END in hook_text:
                print(f"  pre-push hook:    agent-context managed ({hook_path})")
            else:
                sample = hook_path.with_name("pre-push.agent-context.sample")
                if sample.exists():
                    print(f"  pre-push hook:    unmanaged hook preserved; agent-context sample present ({sample})")
                else:
                    print(f"  pre-push hook:    unmanaged hook present ({hook_path})")
        else:
            print("  pre-push hook:    not installed (run `agent-context install-hook`)")

    return 0


def cmd_freshness(args: argparse.Namespace) -> int:
    target_root = pathlib.Path(args.path or ".").resolve()
    script = _tools_dir() / "check_freshness.sh"
    if not script.is_file():
        print(f"ERROR: freshness script not found at {script}", file=sys.stderr)
        return 0
    cmd = ["sh", str(script), "--base-ref", args.base_ref]
    result = subprocess.run(cmd, cwd=str(target_root), check=False)
    if result.returncode != 0:
        print("(freshness check is advisory; exit non-zero is informational)")
    return 0


# ---------------------------------------------------------------------------
# install-skill: copy bundled skill into an agent's skills directory
# ---------------------------------------------------------------------------


SKILL_DEST_DEFAULTS = {
    "claude": "~/.claude/skills/agent-context",
}


def _resolve_skill_dest(agent: str, dest: Optional[str]) -> pathlib.Path:
    if dest:
        return pathlib.Path(dest).expanduser().resolve()
    default = SKILL_DEST_DEFAULTS.get(agent)
    if default is None:
        raise SystemExit(
            f"No default skill destination for agent {agent!r}; pass --dest PATH."
        )
    return pathlib.Path(default).expanduser().resolve()


def cmd_install_skill(args: argparse.Namespace) -> int:
    src = _skill_dir()
    if not src.is_dir():
        print(f"ERROR: bundled skill not found at {src}", file=sys.stderr)
        return 1

    dest = _resolve_skill_dest(args.agent, args.dest)

    if dest.exists() and not args.force:
        print(
            f"ERROR: {dest} already exists. Re-run with --force to overwrite, "
            f"or pass --dest PATH to install elsewhere.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(f"[dry-run] would copy {src} -> {dest}")
        for item in sorted(src.rglob("*")):
            if item.is_file():
                rel = item.relative_to(src)
                print(f"[dry-run]   {rel}")
        return 0

    if dest.exists() and args.force:
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    print(f"Installed agent-context skill v{__version__} -> {dest}")
    return 0


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-context",
        description="Author, verify, and maintain agent-context artifacts.",
    )
    parser.add_argument("--version", action="version", version=f"agent-context {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser(
        "init",
        help="Copy templates into <path>/.agent-context/current/ and generate routing blocks.",
    )
    p_init.add_argument("path", nargs="?", default=None)
    p_init.add_argument("--force", action="store_true",
                        help="Overwrite an existing .agent-context/current/ directory")
    p_init.add_argument("--tier", type=int, choices=[1, 2, 3], default=3,
                        help="Adoption tier: 1=minimal (2 files), 2=standard (6 files), 3=full (11 files, default)")
    p_init.add_argument("--install-hook", action="store_true",
                        help="Install an advisory .git/hooks/pre-push freshness hook when no unmanaged hook is present")
    p_init.set_defaults(func=cmd_init)

    p_verify = subparsers.add_parser(
        "verify",
        help="Run verify_agent_context.py against <path>/.agent-context/current/.",
    )
    p_verify.add_argument("path", nargs="?", default=None)
    p_verify.set_defaults(func=cmd_verify)

    p_doctor = subparsers.add_parser(
        "doctor",
        help="Print environment info and artifact status.",
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_freshness = subparsers.add_parser(
        "freshness",
        help="Advisory freshness check via check_freshness.sh.",
    )
    p_freshness.add_argument("path", nargs="?", default=None)
    p_freshness.add_argument("--base-ref", default="origin/main")
    p_freshness.set_defaults(func=cmd_freshness)

    p_hook = subparsers.add_parser(
        "install-hook",
        help="Copy and install the advisory pre-push freshness hook.",
    )
    p_hook.add_argument("path", nargs="?", default=None)
    p_hook.set_defaults(func=cmd_install_hook)

    p_skill = subparsers.add_parser(
        "install-skill",
        help="Copy the bundled agent-context skill into an agent's skills directory.",
    )
    p_skill.add_argument("--agent", choices=sorted(SKILL_DEST_DEFAULTS.keys()), default="claude",
                         help="Target agent (default: claude). Use --dest for other agents.")
    p_skill.add_argument("--dest", default=None,
                         help="Override destination directory.")
    p_skill.add_argument("--force", action="store_true",
                         help="Overwrite an existing destination.")
    p_skill.add_argument("--dry-run", action="store_true",
                         help="Print what would be copied without writing.")
    p_skill.set_defaults(func=cmd_install_skill)

    return parser


def main(argv: Optional[list] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return int(args.func(args) or 0)


def main_cli() -> int:
    """Console-script entry point for the `agent-context` command."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
