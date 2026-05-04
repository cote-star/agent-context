#!/usr/bin/env bash
# preflight-check.sh — verify a prepared rerun directory is ready to launch agents.
#
# Run this AFTER scripts/experiments/run-matrix.sh and AFTER any manual edits
# to EXPERIMENT.md / GROUND_TRUTH.md. Confirms:
#
#   1. EXPERIMENT.md exists and has no TODO markers.
#   2. GROUND_TRUTH.md exists and has no TODO markers.
#   3. structured_fresh has .agent-context/current/.
#   4. structured_fresh passes agent-context verify.
#   5. structured_fresh passes agent-context freshness against the given base ref.
#   6. Every grep command embedded in fenced code blocks in GROUND_TRUTH.md
#      returns at least one line when run against the bare/ copy.
#
# Usage:
#   scripts/experiments/preflight-check.sh \
#     --rerun ~/agent-context-reruns/agent-chorus \
#     --base-ref origin/main \
#     [--agent-context-bin /path/to/bin/agent-context]
#
# Or to check every rerun under a matrix output:
#   scripts/experiments/preflight-check.sh --matrix-out ~/agent-context-reruns
#
# Exit codes:
#   0  every rerun READY
#   1  invocation error
#   2  one or more reruns NOT-READY
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/preflight-check.sh \
    --rerun PATH \
    --base-ref REF \
    [--agent-context-bin PATH] \
    [--max-pack-age-days N]

  scripts/experiments/preflight-check.sh \
    --matrix-out PATH \
    [--base-ref REF] \
    [--agent-context-bin PATH] \
    [--max-pack-age-days N]

Checks each rerun directory for readiness before agents launch.

--max-pack-age-days N    Optional. Reject packs whose manifest.json
                         generated_at is older than N days. Use for
                         experiment runs to prevent stale-pack slippage
                         beyond the standard freshness check (which only
                         catches code-changed-without-pack-update).
                         Recommended: 14 for experiment runs.
USAGE
}

RERUN=""
MATRIX_OUT=""
BASE_REF="origin/main"
AGENT_CONTEXT_BIN=""
MAX_PACK_AGE_DAYS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rerun) RERUN="${2:-}"; shift 2 ;;
    --matrix-out) MATRIX_OUT="${2:-}"; shift 2 ;;
    --base-ref) BASE_REF="${2:-}"; shift 2 ;;
    --agent-context-bin) AGENT_CONTEXT_BIN="${2:-}"; shift 2 ;;
    --max-pack-age-days) MAX_PACK_AGE_DAYS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$RERUN" && -z "$MATRIX_OUT" ]]; then
  usage >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "$AGENT_CONTEXT_BIN" ]]; then
  AGENT_CONTEXT_BIN="$REPO_ROOT/bin/agent-context"
fi

if [[ ! -x "$AGENT_CONTEXT_BIN" ]]; then
  echo "ERROR: agent-context binary not executable: $AGENT_CONTEXT_BIN" >&2
  exit 1
fi

# IMPORTANT: the public CLI's `freshness` subcommand intentionally returns 0
# even when check_freshness.sh detects stale context (see bin/agent-context
# cmd_freshness: "Advisory only — never propagate failure"). For experiments
# we need a hard gate, so we call check_freshness.sh directly and propagate
# its exit code. Path resolved relative to this script's repo root.
FRESHNESS_SCRIPT="$REPO_ROOT/tools/check_freshness.sh"
if [[ ! -f "$FRESHNESS_SCRIPT" ]]; then
  echo "ERROR: check_freshness.sh not found at $FRESHNESS_SCRIPT" >&2
  exit 1
fi

check_rerun() {
  local dir="$1"
  local label="$2"
  local fail=0

  echo
  echo "----- preflight: $label -----"

  if [[ ! -d "$dir/bare" || ! -d "$dir/structured_fresh" ]]; then
    echo "FAIL: $label missing bare/ or structured_fresh/"
    return 1
  fi

  if [[ ! -f "$dir/EXPERIMENT.md" ]]; then
    echo "FAIL: missing EXPERIMENT.md"; fail=1
  elif grep -q 'TODO' "$dir/EXPERIMENT.md"; then
    echo "FAIL: EXPERIMENT.md still has TODO markers"; fail=1
  else
    echo "OK: EXPERIMENT.md ready"
  fi

  if [[ ! -f "$dir/GROUND_TRUTH.md" ]]; then
    echo "FAIL: missing GROUND_TRUTH.md"; fail=1
  elif grep -q 'TODO' "$dir/GROUND_TRUTH.md"; then
    echo "FAIL: GROUND_TRUTH.md still has TODO markers"; fail=1
  else
    echo "OK: GROUND_TRUTH.md ready"
  fi

  if [[ ! -d "$dir/structured_fresh/.agent-context/current" ]]; then
    echo "FAIL: structured_fresh has no .agent-context/current/"; fail=1
  elif ! "$AGENT_CONTEXT_BIN" verify "$dir/structured_fresh" >/dev/null 2>&1; then
    echo "FAIL: structured_fresh fails agent-context verify"; fail=1
  else
    echo "OK: structured_fresh passes verify"
  fi

  if [[ -d "$dir/structured_fresh/.git" ]]; then
    # Call check_freshness.sh DIRECTLY, not via the CLI. The CLI's freshness
    # subcommand swallows non-zero exit codes (advisory by design). For
    # experiments we want hard failure on stale.
    #
    # Use the if/else pattern so `set -e` cannot abort the script before we
    # report FAIL — bare `var=$(failing)` in a non-conditional context would
    # exit immediately. The conditional context here keeps set -e suppressed
    # for this assignment regardless of how check_rerun is invoked.
    local freshness_out=""
    local freshness_rc=0
    if freshness_out=$(cd "$dir/structured_fresh" && sh "$FRESHNESS_SCRIPT" --base-ref "$BASE_REF" 2>&1); then
      echo "OK: structured_fresh passes freshness against $BASE_REF"
    else
      freshness_rc=$?
      echo "FAIL: structured_fresh fails freshness against $BASE_REF (exit=$freshness_rc)"
      if [[ -n "$freshness_out" ]]; then
        echo "  output: $freshness_out"
      fi
      fail=1
    fi
  else
    echo "WARN: structured_fresh has no .git — skipping freshness check"
  fi

  # Manifest-age gate: reject packs sealed too long ago, even if no code changed.
  # Belt-and-suspenders for experiment runs; opt-in via --max-pack-age-days.
  if [[ -n "$MAX_PACK_AGE_DAYS" ]]; then
    local manifest="$dir/structured_fresh/.agent-context/current/manifest.json"
    if [[ ! -f "$manifest" ]]; then
      echo "FAIL: manifest-age gate: no manifest.json found"; fail=1
    else
      local age_status
      age_status=$(python3 - "$manifest" "$MAX_PACK_AGE_DAYS" <<'PY'
import json, sys, datetime
manifest_path, max_days = sys.argv[1], int(sys.argv[2])
try:
    data = json.loads(open(manifest_path).read())
except Exception as exc:
    print(f"FAIL: manifest unreadable: {exc}")
    sys.exit(0)
ts = data.get("generated_at")
if not ts:
    print("FAIL: manifest has no generated_at field")
    sys.exit(0)
try:
    sealed = datetime.datetime.strptime(ts.rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
except Exception as exc:
    print(f"FAIL: manifest generated_at unparseable ({ts}): {exc}")
    sys.exit(0)
now = datetime.datetime.now(datetime.timezone.utc)
delta_days = (now - sealed).days
if delta_days > max_days:
    print(f"FAIL: pack sealed {delta_days}d ago (>{max_days}d limit) -- re-verify or re-seal before experiment")
else:
    print(f"OK: pack sealed {delta_days}d ago (<= {max_days}d limit)")
PY
)
      echo "$age_status"
      if [[ "$age_status" == FAIL* ]]; then fail=1; fi
    fi
  fi

  # Run every fenced bash block in GROUND_TRUTH.md against bare/
  if [[ -f "$dir/GROUND_TRUTH.md" ]]; then
    local grep_total=0
    local grep_empty=0
    local in_block=0
    while IFS= read -r line; do
      if [[ "$line" =~ ^\`\`\`bash ]]; then
        in_block=1
        continue
      fi
      if [[ "$in_block" -eq 1 && "$line" =~ ^\`\`\` ]]; then
        in_block=0
        continue
      fi
      if [[ "$in_block" -eq 1 ]]; then
        # only run lines that look like grep / find / test commands
        case "$line" in
          grep*|find*|test*|*\|*head*) ;;
          *) continue ;;
        esac
        grep_total=$((grep_total + 1))
        # Run with bare as cwd so paths resolve to source repo files
        if ! ( cd "$dir/bare" && eval "$line" ) >/dev/null 2>&1; then
          grep_empty=$((grep_empty + 1))
          echo "FAIL: ground-truth check returned empty/error: $line"
        fi
      fi
    done < "$dir/GROUND_TRUTH.md"
    if [[ "$grep_total" -eq 0 ]]; then
      echo "WARN: GROUND_TRUTH.md has no fenced bash blocks to verify"
    elif [[ "$grep_empty" -gt 0 ]]; then
      echo "FAIL: $grep_empty/$grep_total ground-truth checks empty/errored"
      fail=1
    else
      echo "OK: $grep_total/$grep_total ground-truth checks return non-empty"
    fi
  fi

  if [[ "$fail" -eq 0 ]]; then
    echo "READY: $label"
    return 0
  else
    echo "NOT-READY: $label"
    return 1
  fi
}

OVERALL_FAIL=0

if [[ -n "$RERUN" ]]; then
  RERUN="${RERUN/#\~/$HOME}"
  if ! check_rerun "$RERUN" "$(basename "$RERUN")"; then
    OVERALL_FAIL=1
  fi
fi

if [[ -n "$MATRIX_OUT" ]]; then
  MATRIX_OUT="${MATRIX_OUT/#\~/$HOME}"
  for sub in "$MATRIX_OUT"/*/; do
    [[ -d "$sub" ]] || continue
    name="$(basename "$sub")"
    [[ "$name" == _* ]] && continue
    if ! check_rerun "${sub%/}" "$name"; then
      OVERALL_FAIL=1
    fi
  done
fi

echo
if [[ "$OVERALL_FAIL" -eq 0 ]]; then
  echo "ALL-READY"
  exit 0
else
  echo "NOT-READY: see FAIL lines above"
  exit 2
fi
