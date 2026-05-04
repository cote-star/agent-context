#!/usr/bin/env bash
# Prepare isolated bare and fresh-structured repo copies for Codex/Cursor reruns.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/prepare-codex-cursor-rerun.sh \
    --source /path/to/target-repo \
    --out ~/agent-context-reruns/target-repo \
    [--base-ref origin/main] [--agent-context-bin /path/to/bin/agent-context] [--force]

Creates:
  OUT/bare
  OUT/structured_fresh
  OUT/EXPERIMENT.md
  OUT/GROUND_TRUTH.md
  OUT/result.schema.json
  OUT/results/{codex,cursor}/{bare,structured_fresh}

The source repo must be clean. The structured copy must already contain a fresh,
filled .agent-context/current/ pack that passes verify and freshness.
USAGE
}

SOURCE=""
OUT=""
BASE_REF="origin/main"
AGENT_CONTEXT_BIN=""
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="${2:-}"; shift 2 ;;
    --out)
      OUT="${2:-}"; shift 2 ;;
    --base-ref)
      BASE_REF="${2:-}"; shift 2 ;;
    --agent-context-bin)
      AGENT_CONTEXT_BIN="${2:-}"; shift 2 ;;
    --force)
      FORCE=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

if [[ -z "$SOURCE" || -z "$OUT" ]]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "$AGENT_CONTEXT_BIN" ]]; then
  AGENT_CONTEXT_BIN="$REPO_ROOT/bin/agent-context"
fi

SOURCE="$(cd "$SOURCE" && pwd)"
OUT="${OUT/#\~/$HOME}"

if [[ ! -d "$SOURCE/.git" ]]; then
  echo "ERROR: source is not a git repo: $SOURCE" >&2
  exit 1
fi

if [[ ! -x "$AGENT_CONTEXT_BIN" ]]; then
  echo "ERROR: agent-context binary is not executable: $AGENT_CONTEXT_BIN" >&2
  exit 1
fi

if [[ -n "$(git -C "$SOURCE" status --porcelain)" ]]; then
  echo "ERROR: source repo has uncommitted changes. Commit/stash first so the experiment is reproducible." >&2
  git -C "$SOURCE" status --short >&2
  exit 1
fi

if [[ -e "$OUT" ]]; then
  if [[ "$FORCE" -ne 1 ]]; then
    echo "ERROR: output path exists: $OUT" >&2
    echo "Re-run with --force to replace it." >&2
    exit 1
  fi
  rm -rf "$OUT"
fi

mkdir -p "$OUT"

echo "Cloning source into isolated conditions..."
git clone --quiet --no-hardlinks "$SOURCE" "$OUT/bare"
git clone --quiet --no-hardlinks "$SOURCE" "$OUT/structured_fresh"

echo "Stripping agent-context from bare condition..."
rm -rf "$OUT/bare/.agent-context"
python3 - "$OUT/bare" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
begin = "<!-- agent-context:begin -->"
end = "<!-- agent-context:end -->"
pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.S)
for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules"):
    path = root / name
    if not path.exists():
        continue
    text = path.read_text()
    new = pattern.sub("", text).lstrip("\n")
    if new.strip():
        path.write_text(new)
    else:
        path.unlink()
PY

echo "Validating structured_fresh condition..."
if [[ ! -d "$OUT/structured_fresh/.agent-context/current" ]]; then
  echo "ERROR: structured_fresh copy has no .agent-context/current/ pack." >&2
  echo "Create and fill the pack in the source repo first, then rerun this script." >&2
  exit 1
fi

git -C "$OUT/structured_fresh" fetch --quiet origin >/dev/null 2>&1 || true
"$AGENT_CONTEXT_BIN" verify "$OUT/structured_fresh"
"$AGENT_CONTEXT_BIN" freshness "$OUT/structured_fresh" --base-ref "$BASE_REF"

echo "Writing experiment scaffold..."
mkdir -p \
  "$OUT/results/claude/bare" \
  "$OUT/results/claude/structured_fresh" \
  "$OUT/results/codex/bare" \
  "$OUT/results/codex/structured_fresh" \
  "$OUT/results/cursor/bare" \
  "$OUT/results/cursor/structured_fresh" \
  "$OUT/results/opencode/bare" \
  "$OUT/results/opencode/structured_fresh"

cp "$REPO_ROOT/docs/experiments/result.schema.json" "$OUT/result.schema.json"

# Reproducibility provenance — read by apply-provenance.py post-run to stamp
# anchor fields into each result JSON. See docs/experiments/q2-2026-rerun/METHODOLOGY.md.
SOURCE_SHA="$(git -C "$SOURCE" rev-parse HEAD)"
MANIFEST_PATH="$OUT/structured_fresh/.agent-context/current/manifest.json"
if [[ -f "$MANIFEST_PATH" ]]; then
  PACK_MANIFEST_SHA="$(shasum -a 256 "$MANIFEST_PATH" | awk '{print $1}')"
else
  PACK_MANIFEST_SHA=""
fi
CLI_VERSION="$("$AGENT_CONTEXT_BIN" --version 2>/dev/null | awk '{print $2}')"
PREPARED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - "$OUT/_provenance.json" "$SOURCE" "$SOURCE_SHA" "$PACK_MANIFEST_SHA" "$CLI_VERSION" "$BASE_REF" "$PREPARED_AT" <<'PY'
import json, sys
out, source, sha, pack_sha, cli_v, base_ref, ts = sys.argv[1:8]
data = {
    "source_repo_path": source,
    "source_repo_sha": sha,
    "pack_manifest_sha": pack_sha or None,
    "agent_context_cli_version": cli_v or None,
    "base_ref": base_ref,
    "prepared_at": ts,
}
with open(out, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
echo "Wrote provenance: $OUT/_provenance.json"

cat > "$OUT/EXPERIMENT.md" <<'EOF'
# Agent-Context Fresh-Pack Rerun

Read this entire file before starting.

## Rules

1. Run tasks in order.
2. Do not read `GROUND_TRUTH.md`.
3. Write one JSON result file per task under the path provided in your launch prompt.
4. Result JSON must match `../result.schema.json`.
5. Set `correct` to `ungraded`; the human reviewer will grade later.
6. Cite exact files and line numbers for factual claims.
7. Track task-local files opened, dead ends, first correct file hop, post-hit dead ends, tool calls, and duration honestly.

## Tasks

Replace these placeholders with six repo-specific tasks before running agents.

### L1 -- Lookup
Question: TODO

### L2 -- Lookup
Question: TODO

### M1 -- Impact analysis
Question: TODO

### M2 -- Impact analysis
Question: TODO

### H1 -- Planning
Question: TODO

### H2 -- Diagnosis
Question: TODO
EOF

cat > "$OUT/GROUND_TRUTH.md" <<'EOF'
# Ground Truth

Reviewer-only. Agents must not read this file.

Fill exact expected answers, required citations, correctness rubric, and risk criteria for each task before grading.
EOF

cat <<EOF

Ready.

Experiment root:
  $OUT

Next steps:
  1. Edit $OUT/EXPERIMENT.md with six tasks.
  2. Edit $OUT/GROUND_TRUTH.md with reviewer answers.
  3. Start fresh Codex and Cursor sessions for both conditions.
  4. Grade JSON results.
  5. Summarize:

     $REPO_ROOT/scripts/experiments/summarize-results.py \\
       $OUT/results \\
       --schema $OUT/result.schema.json

Codex launch examples:
  cd $OUT/bare
  codex "Read ../EXPERIMENT.md and follow it exactly. Agent=codex. Condition=bare. Write results under ../results/codex/bare/."

  cd $OUT/structured_fresh
  codex "Read ../EXPERIMENT.md and follow it exactly. Agent=codex. Condition=structured_fresh. Write results under ../results/codex/structured_fresh/."
EOF
