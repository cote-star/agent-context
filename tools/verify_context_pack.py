#!/usr/bin/env python3
"""Verify the machine-checkable subset of an agent-context pack.

Public (navigation-only) variant: checks content + navigation + manifest layers.
The authority layer (routes.json, completeness_contract.json, reporting_rules.json)
is intentionally not part of the public pack contract. The canonical verifier in
team_skills/skills/agent-context/scripts/ additionally enforces that layer; this
file is the public-repo derivative and is maintained here — it is NOT overwritten
by scripts/sync-from-canonical.sh.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REQUIRED_PACK_FILES = [
    ".agent-context/current/00_START_HERE.md",
    ".agent-context/current/10_SYSTEM_OVERVIEW.md",
    ".agent-context/current/20_CODE_MAP.md",
    ".agent-context/current/30_BEHAVIORAL_INVARIANTS.md",
    ".agent-context/current/40_OPERATIONS_AND_RELEASE.md",
    ".agent-context/current/search_scope.json",
    ".agent-context/current/manifest.json",
    ".agent-context/current/acceptance_tests.md",
]

TEMPLATE_PATTERN = re.compile(r"\{name\}|\{domain\}|\{module\}|REPLACE")
SOURCE_ROOT_HINTS = ("app", "src", "lib", "services", "models", "packages", "pkg")
CODE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
}
GENERIC_DIR_NAMES = {
    "api",
    "apis",
    "app",
    "apps",
    "common",
    "core",
    "helpers",
    "lib",
    "libs",
    "models",
    "pkg",
    "services",
    "shared",
    "src",
    "tests",
    "utils",
}
FEATURE_PARENT_NAMES = {
    "api",
    "apis",
    "clients",
    "commands",
    "core",
    "endpoints",
    "features",
    "gateways",
    "integrations",
    "jobs",
    "pipelines",
    "routes",
    "service",
    "services",
    "workers",
}
INTEGRATION_DIR_NAMES = {
    "ai_gateway",
    "bigquery",
    "databricks",
    "dynamo_db",
    "elasticsearch",
    "kafka",
    "mlflow",
    "mongodb",
    "mysql",
    "openai",
    "postgres",
    "redis",
    "s3",
    "snowflake",
    "sqs",
}
MIN_SIGNIFICANT_CODE_FILES = 3
MAX_SIGNIFICANT_DEPTH = 3


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"unable to read {path}: {exc}") from exc


def read_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(read_text(path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def ensure_exists_and_nonempty(root: pathlib.Path, rel_path: str, errors: list[str]) -> None:
    path = root / rel_path
    if not path.exists():
        errors.append(f"missing required file: {rel_path}")
    elif path.stat().st_size == 0:
        errors.append(f"empty required file: {rel_path}")


def validate_template_markers(root: pathlib.Path, errors: list[str]) -> None:
    for path in (root / ".agent-context/current").glob("*.json"):
        text = read_text(path)
        if TEMPLATE_PATTERN.search(text):
            errors.append(f"template marker found in JSON artifact: {path.relative_to(root)}")


def validate_manifest(root: pathlib.Path, errors: list[str]) -> None:
    manifest_path = root / ".agent-context/current/manifest.json"
    manifest = read_json(manifest_path)
    for key in ["version", "generated_at", "repo", "git_revision", "files"]:
        if key not in manifest:
            errors.append(f"manifest missing key: {key}")
    files = manifest.get("files", {})
    for key in ["content", "navigation"]:
        if key not in files or not isinstance(files[key], list) or not files[key]:
            errors.append(f"manifest.files missing non-empty list: {key}")


def validate_search_scope(root: pathlib.Path, errors: list[str]) -> None:
    scope_path = root / ".agent-context/current/search_scope.json"
    scope = read_json(scope_path)
    for family, data in scope.get("task_families", {}).items():
        if family.startswith("_EXAMPLE"):
            errors.append(f"remove example task family: {family}")
        for rel_path in data.get("search_directories", []):
            if not (root / rel_path).exists():
                errors.append(f"search_scope {family}: missing search directory: {rel_path}")
        for rel_path in data.get("exclude_from_search", []):
            # Exclusions may legitimately not exist; do not fail on these.
            if TEMPLATE_PATTERN.search(rel_path):
                errors.append(f"search_scope {family}: template marker in exclude path: {rel_path}")
        for shortcut in data.get("verification_shortcuts", []):
            rel_path = shortcut.get("file")
            look_for = shortcut.get("look_for", "")
            if not rel_path:
                errors.append(f"search_scope {family}: verification shortcut missing file")
                continue
            path = root / rel_path
            if not path.exists():
                errors.append(f"search_scope {family}: missing verification file: {rel_path}")
                continue
            if look_for and look_for not in read_text(path):
                errors.append(
                    f"search_scope {family}: look_for string not found in {rel_path}: {look_for}"
                )


def is_code_file(path: pathlib.Path) -> bool:
    return path.is_file() and path.suffix.lower() in CODE_EXTENSIONS


def count_code_files(directory: pathlib.Path) -> int:
    return sum(1 for path in directory.rglob("*") if is_code_file(path))


def qualifies_as_subsystem(
    source_root_name: str, rel_parts: tuple[str, ...], basename: str, code_files: int
) -> bool:
    if any(part in {"common", "helpers", "shared", "utils"} for part in rel_parts[:-1]):
        return False
    if basename in INTEGRATION_DIR_NAMES:
        return True
    if any(part in FEATURE_PARENT_NAMES for part in rel_parts[:-1]):
        return True
    if source_root_name in {"src", "lib", "services", "packages", "pkg"} and len(rel_parts) == 1:
        return code_files >= 6
    return False


def discover_significant_directories(root: pathlib.Path) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []

    for hint in SOURCE_ROOT_HINTS:
        source_root = root / hint
        if not source_root.is_dir():
            continue

        for path in source_root.rglob("*"):
            if not path.is_dir():
                continue
            depth = len(path.relative_to(source_root).parts)
            if depth < 1 or depth > MAX_SIGNIFICANT_DEPTH:
                continue
            if path.name.lower() in GENERIC_DIR_NAMES:
                continue

            code_files = count_code_files(path)
            if code_files < MIN_SIGNIFICANT_CODE_FILES:
                continue
            rel_parts = path.relative_to(source_root).parts
            if not qualifies_as_subsystem(hint, rel_parts, path.name.lower(), code_files):
                continue

            candidates.append((path.relative_to(root).as_posix(), code_files))

    # Prefer specific subsystem directories over broad parent directories.
    ordered = sorted(set(candidates), key=lambda item: (item[0].count("/"), item[0]))
    paths = [rel_path for rel_path, _ in ordered]
    significant: list[tuple[str, int]] = []
    for rel_path, code_files in ordered:
        if any(other != rel_path and other.startswith(f"{rel_path}/") for other in paths):
            continue
        significant.append((rel_path, code_files))

    return significant


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def remove_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)")
    return pattern.sub("", text)


def gather_pack_text(root: pathlib.Path) -> tuple[str, str]:
    current_dir = root / ".agent-context/current"
    start_here_path = current_dir / "00_START_HERE.md"
    start_here = read_text(start_here_path)
    not_covered = extract_markdown_section(start_here, "Not Covered in Detail")

    pack_parts: list[str] = [remove_markdown_section(start_here, "Not Covered in Detail")]
    for path in sorted(current_dir.glob("*")):
        if path == start_here_path or not path.is_file():
            continue
        pack_parts.append(read_text(path))

    return "\n".join(pack_parts), not_covered


def validate_coverage(root: pathlib.Path, errors: list[str]) -> None:
    significant_dirs = discover_significant_directories(root)
    if not significant_dirs:
        return

    pack_text, not_covered = gather_pack_text(root)

    missing = [
        f"{rel_path} ({code_files} code files)"
        for rel_path, code_files in significant_dirs
        if rel_path not in pack_text and rel_path not in not_covered
    ]
    if missing:
        errors.append(
            "coverage check: significant source directories are absent from the pack; "
            "add coverage or list them under 'Not Covered in Detail': "
            + ", ".join(missing)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("repo_root_positional", nargs="?", default=None,
                        help="Optional positional repo-root (same as --repo-root)")
    args = parser.parse_args()

    chosen_root = args.repo_root_positional or args.repo_root
    root = pathlib.Path(chosen_root).resolve()
    errors: list[str] = []

    for rel_path in REQUIRED_PACK_FILES:
        ensure_exists_and_nonempty(root, rel_path, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    validate_template_markers(root, errors)
    validate_manifest(root, errors)
    validate_search_scope(root, errors)
    validate_coverage(root, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("OK: agent-context pack passed machine-checkable validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
