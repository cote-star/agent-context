#!/usr/bin/env bash
# run-matrix.sh — orchestrate the fresh-pack rerun across multiple repos.
#
# Reads a matrix.config (one repo per line) and for each repo:
#   1. Confirms the source repo has a clean working tree.
#   2. Confirms the source repo has a fresh, verified .agent-context/ pack.
#   3. Calls prepare-codex-cursor-rerun.sh to create isolated bare and
#      structured_fresh copies + scaffolds EXPERIMENT.md / GROUND_TRUTH.md.
#   4. Calls scaffold-tasks.py to populate EXPERIMENT.md and GROUND_TRUTH.md
#      from the matching docs/experiments/tasks/<task_template>.md file.
#   5. Reports PASS / FAIL / REQUIRES-EDIT per repo.
#
# Usage:
#   scripts/experiments/run-matrix.sh \
#     --config docs/experiments/matrix.config \
#     --out ~/agent-context-reruns
#
# matrix.config format:
#   <name>:<source_path>:<base_ref>:<task_template>
#
# See docs/experiments/matrix.config.example for the canonical template.
#
# Exit codes:
#   0  every repo PASS
#   1  invocation error (missing config / out)
#   2  one or more repos FAIL (hard error: dirty tree, no pack, verify/freshness fail)
#   3  every repo OK but at least one is REQUIRES-EDIT (TODO markers still in tasks)

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/run-matrix.sh \
    --config docs/experiments/matrix.config \
    --out ~/agent-context-reruns \
    [--agent-context-bin /path/to/bin/agent-context] [--force] [--allow-todo]

Required:
  --config        Path to matrix.config (one repo per line).
  --out           Root directory under which each repo's rerun copy is created.

Optional:
  --agent-context-bin  Override the agent-context binary path. Default: bin/agent-context in this repo.
  --force              Re-run even if a per-repo output dir already exists (passes through).
  --allow-todo         Allow TODO markers in EXPERIMENT.md / GROUND_TRUTH.md (mark rerun REQUIRES-EDIT).

Output:
  <out>/<repo_name>/  one prepared rerun per matrix.config row.
  <out>/_matrix.report.md   markdown summary written at the end.
USAGE
}

CONFIG=""
OUT=""
AGENT_CONTEXT_BIN=""
FORCE=0
ALLOW_TODO=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --agent-context-bin) AGENT_CONTEXT_BIN="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --allow-todo) ALLOW_TODO=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$CONFIG" || -z "$OUT" ]]; then
  usage >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PREP_SCRIPT="$SCRIPT_DIR/prepare-codex-cursor-rerun.sh"
SCAFFOLD_SCRIPT="$SCRIPT_DIR/scaffold-tasks.py"
TASKS_DIR="$REPO_ROOT/docs/experiments/tasks"
# Strict freshness gate. The agent-context CLI's freshness subcommand
# returns 0 even when drift is detected (advisory by design); for
# experiment runs we want hard failure on stale, so we call the
# underlying shell script directly. Same pattern as preflight-check.sh.
FRESHNESS_SCRIPT="$REPO_ROOT/tools/check_freshness.sh"

if [[ -z "$AGENT_CONTEXT_BIN" ]]; then
  AGENT_CONTEXT_BIN="$REPO_ROOT/bin/agent-context"
fi

if [[ ! -x "$AGENT_CONTEXT_BIN" ]]; then
  echo "ERROR: agent-context binary not executable: $AGENT_CONTEXT_BIN" >&2
  exit 1
fi
if [[ ! -f "$FRESHNESS_SCRIPT" ]]; then
  echo "ERROR: check_freshness.sh not found at $FRESHNESS_SCRIPT" >&2
  exit 1
fi
if [[ ! -x "$PREP_SCRIPT" ]]; then
  echo "ERROR: prep script not executable: $PREP_SCRIPT" >&2
  exit 1
fi
if [[ ! -f "$SCAFFOLD_SCRIPT" ]]; then
  echo "ERROR: scaffold script not found: $SCAFFOLD_SCRIPT" >&2
  exit 1
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: config file not found: $CONFIG" >&2
  exit 1
fi

OUT="${OUT/#\~/$HOME}"
mkdir -p "$OUT"

REPORT="$OUT/_matrix.report.md"
{
  echo "# Matrix run report"
  echo
  echo "_Generated: $(date -u +'%Y-%m-%dT%H:%M:%SZ')_"
  echo
  echo "| Repo | Status | Notes |"
  echo "|---|---|---|"
} > "$REPORT"

FAIL_COUNT=0
EDIT_COUNT=0
PASS_COUNT=0

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%%#*}"
  line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [[ -z "$line" ]] && continue

  IFS=':' read -r NAME SOURCE BASE_REF TASK_TEMPLATE <<< "$line"
  NAME="$(echo "$NAME" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  SOURCE="$(echo "$SOURCE" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  BASE_REF="$(echo "$BASE_REF" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  TASK_TEMPLATE="$(echo "$TASK_TEMPLATE" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

  if [[ -z "$NAME" || -z "$SOURCE" || -z "$BASE_REF" || -z "$TASK_TEMPLATE" ]]; then
    echo "WARN: skipping malformed config row: $raw_line" >&2
    continue
  fi

  echo
  echo "================================================================="
  echo "[$NAME] starting"
  echo "================================================================="

  status="UNKNOWN"
  notes=""
  per_out="$OUT/$NAME"

  # --- Step 1: source pre-flight ---
  if [[ ! -d "$SOURCE" ]]; then
    status="FAIL"; notes="source path not a directory: $SOURCE"
  elif [[ ! -d "$SOURCE/.git" ]]; then
    status="FAIL"; notes="source is not a git repo: $SOURCE"
  elif [[ -n "$(git -C "$SOURCE" status --porcelain)" ]]; then
    status="FAIL"; notes="source has uncommitted changes; commit/stash first"
  elif [[ ! -d "$SOURCE/.agent-context/current" ]]; then
    status="FAIL"; notes="source has no .agent-context/current/ pack; run init + fill first"
  fi

  # --- Step 2: pack freshness on source ---
  # Use strict freshness (tools/check_freshness.sh) directly. The CLI's
  # freshness subcommand swallows non-zero exit codes by design.
  if [[ "$status" == "UNKNOWN" ]]; then
    if ! "$AGENT_CONTEXT_BIN" verify "$SOURCE" >/dev/null 2>&1; then
      status="FAIL"; notes="agent-context verify failed on source pack"
    else
      fresh_out=""
      if fresh_out=$(cd "$SOURCE" && sh "$FRESHNESS_SCRIPT" --base-ref "$BASE_REF" 2>&1); then
        :
      else
        status="FAIL"
        notes="strict freshness failed on source pack (drift detected against $BASE_REF): $fresh_out"
      fi
    fi
  fi

  # --- Step 3: prepare isolated copies ---
  if [[ "$status" == "UNKNOWN" ]]; then
    prep_args=(--source "$SOURCE" --out "$per_out" --base-ref "$BASE_REF" --agent-context-bin "$AGENT_CONTEXT_BIN")
    if [[ "$FORCE" -eq 1 ]]; then prep_args+=(--force); fi
    if ! "$PREP_SCRIPT" "${prep_args[@]}" > "$per_out.prep.log" 2>&1; then
      status="FAIL"; notes="prepare-codex-cursor-rerun.sh failed; see $per_out.prep.log"
    fi
  fi

  # --- Step 4: populate EXPERIMENT.md and GROUND_TRUTH.md from task template ---
  if [[ "$status" == "UNKNOWN" ]]; then
    template_file="$TASKS_DIR/$TASK_TEMPLATE.md"
    if [[ ! -f "$template_file" ]]; then
      status="FAIL"; notes="task template not found: docs/experiments/tasks/$TASK_TEMPLATE.md"
    else
      scaffold_args=("$template_file" "$per_out")
      if [[ "$ALLOW_TODO" -eq 1 ]]; then scaffold_args+=(--allow-todo); fi
      scaffold_log="$per_out.scaffold.log"
      if python3 "$SCAFFOLD_SCRIPT" "${scaffold_args[@]}" > "$scaffold_log" 2>&1; then
        if grep -q '^WARN: extracted content has TODO markers' "$scaffold_log"; then
          status="REQUIRES-EDIT"; notes="task template still has TODO markers in $TASK_TEMPLATE.md (--allow-todo set); adapt before launching agents"
        else
          status="PASS"; notes="ready to launch agents"
        fi
      else
        rc=$?
        if [[ "$rc" == "2" ]]; then
          status="REQUIRES-EDIT"; notes="task template has TODO markers; adapt $TASK_TEMPLATE.md or rerun with --allow-todo"
        else
          status="FAIL"; notes="scaffold-tasks.py failed; see $scaffold_log"
        fi
      fi
    fi
  fi

  # --- Tally ---
  case "$status" in
    PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    REQUIRES-EDIT) EDIT_COUNT=$((EDIT_COUNT + 1)) ;;
    *) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
  esac
  echo "[$NAME] $status: $notes"
  echo "| \`$NAME\` | $status | $notes |" >> "$REPORT"

done < "$CONFIG"

{
  echo
  echo "## Summary"
  echo
  echo "- PASS: $PASS_COUNT"
  echo "- REQUIRES-EDIT: $EDIT_COUNT"
  echo "- FAIL: $FAIL_COUNT"
  echo
  if [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "**Action: fix FAIL rows before launching agents.**"
  elif [[ "$EDIT_COUNT" -gt 0 ]]; then
    echo "**Action: adapt task templates for REQUIRES-EDIT rows, then re-run preflight-check.sh.**"
  else
    echo "**Action: run \`scripts/experiments/preflight-check.sh\` (with \`--max-pack-age-days 14\`) to gate, then launch each repo via \`scripts/experiments/launch-tmux-matrix.sh <alias>\`. Full protocol: \`docs/experiments/RUNBOOK.md\`.**"
  fi
} >> "$REPORT"

echo
echo "================================================================="
echo "Matrix complete. Report: $REPORT"
echo "PASS=$PASS_COUNT  REQUIRES-EDIT=$EDIT_COUNT  FAIL=$FAIL_COUNT"
echo "================================================================="

if [[ "$FAIL_COUNT" -gt 0 ]]; then exit 2; fi
if [[ "$EDIT_COUNT" -gt 0 ]]; then exit 3; fi
exit 0
