#!/usr/bin/env bash
# run-claude-interactive-lane.sh — drive one Claude lane through the 7-repo slate
# using interactive `claude` (web/SSO auth), one fresh session per repo.
#
# Why this exists: `claude -p` headless requires API auth; this workstation uses
# web/SSO. Interactive `claude` works and writes per-session JSONL under
# ~/.claude/projects/<cwd-hash>/<session-id>.jsonl, so post-hoc token extraction
# via chorus continues to work.
#
# Usage (run two panes in parallel, one per condition):
#   scripts/experiments/run-claude-interactive-lane.sh --condition bare
#   scripts/experiments/run-claude-interactive-lane.sh --condition structured_fresh
#
# Loop per alias:
#   1. Skip if results dir already has 6 JSONs (and not --force).
#   2. cd into the alias's bare/ or structured_fresh/ clone.
#   3. Copy the prompt file contents to the clipboard (pbcopy on macOS).
#   4. Launch `claude` interactive in that cwd. You paste once and wait.
#   5. When claude exits, verify result_count == 6. If short, prompt to relaunch.
#   6. Advance to next alias.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/run-claude-interactive-lane.sh \
    --condition bare|structured_fresh \
    [--rerun-root PATH] \
    [--aliases alias1,alias2,...] \
    [--force]

Drives interactive `claude` through one condition's lane, one repo at a time.
You paste the prompt once per repo, claude does the work, /exit to advance.

Options:
  --force       Run even if 6 result JSON files already exist for that cell.
USAGE
}

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }

CONDITION=""
RERUN_ROOT="$HOME/agent-context-reruns/q2-2026-private"
ALIASES_CSV="agent-chorus,ml-pipeline-reference,react-frontend-reference,backend-service-reference,polyglot-monorepo-reference,org-second-brain,daemon-reference"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --condition) CONDITION="${2:-}"; shift 2 ;;
    --rerun-root) RERUN_ROOT="${2:-}"; shift 2 ;;
    --aliases) ALIASES_CSV="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

case "$CONDITION" in
  bare|structured_fresh) ;;
  "") usage >&2; exit 1 ;;
  *) die "unsupported condition: $CONDITION (expected bare or structured_fresh)" ;;
esac

RERUN_ROOT="${RERUN_ROOT/#\~/$HOME}"
[[ -d "$RERUN_ROOT" ]] || die "rerun root not found: $RERUN_ROOT"
command -v claude >/dev/null || die "claude not found on PATH"

CLIP=""
if command -v pbcopy >/dev/null 2>&1; then
  CLIP="pbcopy"
elif command -v xclip >/dev/null 2>&1; then
  CLIP="xclip -selection clipboard"
elif command -v wl-copy >/dev/null 2>&1; then
  CLIP="wl-copy"
fi

count_results() {
  local outdir="$1"
  find "$outdir" -maxdepth 1 -name '*.json' -not -name '*.judge.json' 2>/dev/null \
    | wc -l | tr -d ' '
}

run_cell() {
  local alias="$1"
  local rerun="$RERUN_ROOT/$alias"
  local cwd="$rerun/$CONDITION"
  local prompt="$rerun/.prompt-claude-$CONDITION.txt"
  local outdir="$rerun/results/claude/$CONDITION"
  local logdir="$rerun/_logs/claude/$CONDITION"
  local started
  started="$(date -u +'%Y%m%dT%H%M%SZ')"

  [[ -d "$cwd" ]] || { warn "$alias: missing condition dir: $cwd"; return 2; }
  [[ -f "$prompt" ]] || { warn "$alias: missing prompt file: $prompt"; return 2; }
  [[ -d "$outdir" ]] || { warn "$alias: missing results dir: $outdir"; return 2; }
  mkdir -p "$logdir"

  local existing
  existing="$(count_results "$outdir")"
  if [[ "$existing" == "6" && "$FORCE" -ne 1 ]]; then
    echo "[$alias][claude/$CONDITION] SKIP: already has 6 result JSONs"
    return 0
  fi

  cat <<BANNER

=================================================================
[$alias][claude/$CONDITION]   ($existing/6 existing, target 6)
cwd:    $cwd
prompt: $prompt
out:    $outdir
log:    $logdir/$started.log
=================================================================
BANNER

  if [[ -n "$CLIP" ]]; then
    if eval "$CLIP" < "$prompt"; then
      echo "✓ Prompt copied to clipboard ($(wc -c <"$prompt" | tr -d ' ') bytes). Paste with cmd-V into claude."
    else
      echo "(clipboard copy failed — cat the prompt manually:  cat '$prompt')"
    fi
  else
    echo "(no clipboard tool found — cat the prompt manually:  cat '$prompt')"
  fi

  cat <<'GUIDE'

Next steps:
  1. claude will launch in the cwd shown above.
  2. Paste the prompt (cmd-V), press Return, let claude do its work.
  3. When claude has written all 6 JSONs and you see its summary, type /exit.
  4. This script will then verify the result count and advance.
GUIDE

  read -r -p "Press Return to launch claude in $cwd ... " _

  # Launch claude on a real TTY (NO pipe — piping would force --print mode).
  # We log only the launch metadata; claude's interactive TUI is watched live.
  echo "started_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$logdir/$started.log"
  echo "cwd=$cwd" >> "$logdir/$started.log"
  ( cd "$cwd" && claude ) || true
  echo "finished_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$logdir/$started.log"

  local count
  count="$(count_results "$outdir")"
  echo "result_count=$count/6" >> "$logdir/$started.log"
  echo
  echo "[$alias][claude/$CONDITION] post-claude result_count=$count/6"

  while [[ "$count" -lt 6 ]]; do
    echo
    read -r -p "Only $count/6 JSONs. Re-launch claude in same cwd to fill gaps? [y/N/skip] " ans
    case "${ans:-N}" in
      y|Y|yes|YES)
        started="$(date -u +'%Y%m%dT%H%M%SZ')"
        echo "started_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$logdir/$started.log"
        echo "cwd=$cwd" >> "$logdir/$started.log"
        ( cd "$cwd" && claude ) || true
        echo "finished_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$logdir/$started.log"
        count="$(count_results "$outdir")"
        echo "result_count=$count/6" >> "$logdir/$started.log"
        echo "[$alias][claude/$CONDITION] post-relaunch result_count=$count/6"
        ;;
      skip|SKIP|s)
        warn "$alias: leaving at $count/6 and advancing"
        return 2
        ;;
      *)
        warn "$alias: leaving at $count/6 and advancing"
        return 2
        ;;
    esac
  done

  echo "[$alias][claude/$CONDITION] OK: 6/6 results"
  return 0
}

IFS=',' read -r -a ALIASES <<< "$ALIASES_CSV"
FAILS=0
DONE=0
TOTAL="${#ALIASES[@]}"

cat <<HDR

================================================================
 Claude interactive lane: condition=$CONDITION  aliases=$TOTAL
 rerun-root: $RERUN_ROOT
================================================================
HDR

for alias in "${ALIASES[@]}"; do
  alias="$(echo "$alias" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [[ -z "$alias" ]] && continue
  DONE=$((DONE + 1))
  echo
  echo "(${DONE}/${TOTAL}) -> $alias"
  if ! run_cell "$alias"; then
    FAILS=$((FAILS + 1))
  fi
done

echo
if [[ "$FAILS" -eq 0 ]]; then
  echo "LANE OK: claude/$CONDITION completed all $TOTAL aliases at 6/6"
else
  echo "LANE PARTIAL: claude/$CONDITION had $FAILS alias(es) below 6/6 — rerun the script to fill gaps (skip rule keeps 6/6 cells stable)"
  exit 2
fi
