#!/usr/bin/env bash
# launch-tmux-batch.sh — open a 6-lane tmux session for the full Q2 matrix.
#
# This is the operator-friendly launcher. Instead of 7 repo sessions × 6 panes
# (=42 visible cells), it opens one session with 6 lanes:
#
#   claude/bare, claude/structured_fresh,
#   codex/bare,  codex/structured_fresh,
#   cursor/bare, cursor/structured_fresh
#
# Each lane runs all active repos sequentially through run-agent-lane.sh. The
# lane runner starts a fresh non-interactive agent process per repo, preserving
# repo-level independence without requiring the operator to shepherd 42 panes.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/launch-tmux-batch.sh [--start] [--force] [--dry-run-lanes]

Environment:
  RERUN_ROOT=/custom/path   default: ~/agent-context-reruns/q2-2026-private

Options:
  --start          Press Enter in all lanes immediately after creating tmux.
                   Without this, commands are preloaded for inspection and you
                   press Enter in each pane.
  --force          Pass --force to run-agent-lane.sh (rerun cells with 6 JSONs).
  --dry-run-lanes  Pass --dry-run to run-agent-lane.sh.

After launch:
  tmux attach -t rerun-q2-batch
USAGE
}

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }

START=0
FORCE=0
DRY_RUN_LANES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START=1; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run-lanes) DRY_RUN_LANES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_LANE="$SCRIPT_DIR/run-agent-lane.sh"
[[ -x "$RUN_LANE" ]] || die "lane runner is not executable: $RUN_LANE"

RERUN_ROOT="${RERUN_ROOT:-$HOME/agent-context-reruns/q2-2026-private}"
RERUN_ROOT="${RERUN_ROOT/#\~/$HOME}"
[[ -d "$RERUN_ROOT" ]] || die "rerun root not found: $RERUN_ROOT"

SESSION="rerun-q2-batch"
ALIASES="agent-chorus,ml-pipeline-reference,react-frontend-reference,backend-service-reference,polyglot-monorepo-reference,org-second-brain,daemon-reference"

command -v tmux >/dev/null || die "tmux not installed"
for cli in claude codex cursor-agent; do
  command -v "$cli" >/dev/null || warn "$cli not found on PATH"
done

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already exists."
  echo "Attach: tmux attach -t $SESSION"
  echo "Kill:   tmux kill-session -t $SESSION"
  exit 0
fi

lane_cmd() {
  local agent="$1" condition="$2"
  local cmd="$RUN_LANE --agent $agent --condition $condition --rerun-root '$RERUN_ROOT' --aliases '$ALIASES'"
  [[ "$FORCE" -eq 1 ]] && cmd="$cmd --force"
  [[ "$DRY_RUN_LANES" -eq 1 ]] && cmd="$cmd --dry-run"
  printf '%s' "$cmd"
}

setup_pane() {
  local pane_id="$1" agent="$2" condition="$3"
  local title="$agent / $condition"
  local cmd
  cmd="$(lane_cmd "$agent" "$condition")"
  # Use AGENT_CONTEXT_REPO if exported, otherwise resolve from git, otherwise
  # fall back to the script's own parent of parent (script lives at
  # scripts/experiments/launch-tmux-batch.sh inside the repo).
  local repo_root="${AGENT_CONTEXT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
  repo_root="${repo_root:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  tmux select-pane -t "$pane_id" -T "$title"
  tmux send-keys -t "$pane_id" "cd '$repo_root'" Enter
  tmux send-keys -t "$pane_id" "clear" Enter
  tmux send-keys -t "$pane_id" "echo '== $title lane =='" Enter
  tmux send-keys -t "$pane_id" "echo 'Runs all 7 repos sequentially; fresh agent process per repo.'" Enter
  tmux send-keys -t "$pane_id" "echo 'Logs land under <rerun>/_logs/$agent/$condition/'" Enter
  tmux send-keys -t "$pane_id" "echo ''" Enter
  tmux send-keys -t "$pane_id" "$cmd"
  if [[ "$START" -eq 1 ]]; then
    tmux send-keys -t "$pane_id" Enter
  fi
}

tmux new-session -d -s "$SESSION" -n lanes -x 220 -y 60

P_TL_1=$(tmux list-panes -t "$SESSION:lanes" -F '#{pane_id}' | head -1)
P_TL_2=$(tmux split-window -h -t "$P_TL_1" -P -F '#{pane_id}')
P_TL_3=$(tmux split-window -h -t "$P_TL_2" -P -F '#{pane_id}')
tmux select-layout -t "$SESSION:lanes" even-horizontal

P_BL_1=$(tmux split-window -v -t "$P_TL_1" -P -F '#{pane_id}')
P_BL_2=$(tmux split-window -v -t "$P_TL_2" -P -F '#{pane_id}')
P_BL_3=$(tmux split-window -v -t "$P_TL_3" -P -F '#{pane_id}')

tmux setw -t "$SESSION:lanes" pane-border-status top
tmux setw -t "$SESSION:lanes" pane-border-format ' #T '

setup_pane "$P_TL_1" "claude" "bare"
setup_pane "$P_TL_2" "codex" "bare"
setup_pane "$P_TL_3" "cursor" "bare"
setup_pane "$P_BL_1" "claude" "structured_fresh"
setup_pane "$P_BL_2" "codex" "structured_fresh"
setup_pane "$P_BL_3" "cursor" "structured_fresh"

tmux select-pane -t "$P_TL_1"

cat <<EOF
Batch tmux session ready.

  Attach:  tmux attach -t $SESSION
  Kill:    tmux kill-session -t $SESSION

Shape:
  6 lanes total: claude/codex/cursor × bare/structured_fresh
  Each lane runs all 7 repos sequentially.
  Each repo gets a fresh non-interactive agent process.

$(if [[ "$START" -eq 1 ]]; then echo "Lanes were started immediately."; else echo "Commands are preloaded but not started. Press Enter in each pane when ready."; fi)
EOF
