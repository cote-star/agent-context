#!/usr/bin/env bash
# launch-tmux-matrix.sh — open a tmux session for one repo's experiment runs.
#
# Usage:
#   scripts/experiments/launch-tmux-matrix.sh <alias>
#
#   RERUN_ROOT=/custom/path scripts/experiments/launch-tmux-matrix.sh <alias>
#
# Creates session "rerun-<alias>" with 4 windows (claude, codex, cursor,
# opencode), each with 2 panes (top=bare, bottom=structured_fresh). Each
# pane:
#   - cd's into the right working directory
#   - shows the agent + condition identity
#   - shows the invoke hint (which CLI to run)
#   - cats the exact prompt to copy/paste
#
# The script does NOT auto-execute agent CLIs — the operator pastes the
# prompt into each pane after invoking the appropriate CLI. This keeps
# every cell auditable: bare and structured_fresh runs are visible in
# the same session, with stdout still flowing through the operator.
#
# Pre-conditions:
#   - prepare-codex-cursor-rerun.sh has populated $RERUN_ROOT/$alias/
#     with bare/, structured_fresh/, EXPERIMENT.md, GROUND_TRUTH.md,
#     and results/{claude,codex,cursor,opencode}/{bare,structured_fresh}/
#   - tmux installed
#   - The four agent CLIs are reachable on PATH (warn-only, not hard fail —
#     OpenCode tunnel may be down)
#
# Exit codes:
#   0  session created (or already existed; re-attach with tmux attach)
#   1  invocation error (missing arg, missing dir, missing tmux)
#   2  missing required pre-condition (no rerun dir, no EXPERIMENT.md)

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/launch-tmux-matrix.sh <alias>

  RERUN_ROOT=/custom/path scripts/experiments/launch-tmux-matrix.sh <alias>

Opens a tmux session "rerun-<alias>" with 4 windows (one per agent) and
2 panes per window (bare, structured_fresh). Each pane shows the prompt
to paste into the agent CLI.

After the script finishes:
  tmux attach -t rerun-<alias>

To kill the session and start over:
  tmux kill-session -t rerun-<alias>
USAGE
}

die() { echo "ERROR: $1" >&2; exit "${2:-1}"; }
warn() { echo "WARN: $*" >&2; }

if [[ "${1:-}" == "" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ALIAS="$1"
RERUN_ROOT="${RERUN_ROOT:-$HOME/agent-context-reruns/q2-2026-private}"
RERUN_DIR="$RERUN_ROOT/$ALIAS"
SESSION="rerun-$ALIAS"

# --- Pre-conditions -------------------------------------------------------

[[ -d "$RERUN_DIR" ]] || die "Rerun dir not found: $RERUN_DIR. Run prepare-codex-cursor-rerun.sh first." 2
[[ -d "$RERUN_DIR/bare" ]] || die "Missing $RERUN_DIR/bare/" 2
[[ -d "$RERUN_DIR/structured_fresh" ]] || die "Missing $RERUN_DIR/structured_fresh/" 2
[[ -f "$RERUN_DIR/EXPERIMENT.md" ]] || die "Missing $RERUN_DIR/EXPERIMENT.md" 2
[[ -f "$RERUN_DIR/result.schema.json" ]] || die "Missing $RERUN_DIR/result.schema.json" 2

for cond in bare structured_fresh; do
  for agent in claude codex cursor opencode; do
    rdir="$RERUN_DIR/results/$agent/$cond"
    [[ -d "$rdir" ]] || die "Missing results dir: $rdir" 2
  done
done

command -v tmux >/dev/null || die "tmux not installed"

# CLI presence: warn-only. Operator might be running a single agent.
for cli in claude codex cursor-agent opencode-play; do
  command -v "$cli" >/dev/null || warn "$cli not in PATH (its panes will still open; invoke manually if available elsewhere)"
done

# OpenCode tunnel sanity (informational only)
if ! curl -s -m 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:11434/v1/models 2>/dev/null | grep -q '200'; then
  warn "OpenCode local endpoint http://127.0.0.1:11434 not reachable. The opencode pane will open but the agent will fail until the tunnel is up."
fi

# Existing session?
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already exists."
  echo "Attach with:  tmux attach -t $SESSION"
  echo "Kill it with: tmux kill-session -t $SESSION"
  exit 0
fi

# --- Prompt builder -------------------------------------------------------

# Write a per-cell prompt file. The pane will `cat` it for the operator
# to copy/paste into the agent CLI.
build_prompt() {
  local agent="$1" capture="$2" condition="$3" outfile="$4"
  cat > "$outfile" <<EOF
Read ../EXPERIMENT.md and follow it exactly.

agent           = $agent
capture_method  = $capture
condition       = $condition

Write one JSON result file per task (L1, L2, M1, M2, H1, H2) to:
  ../results/$agent/$condition/<task_id>.json

The schema is at ../result.schema.json. Required fields include
task_id, agent='$agent', capture_method='$capture',
condition='$condition', repo (the alias), started_at and finished_at
(ISO 8601 UTC, e.g. 2026-05-04T15:00:00Z), files_opened_count,
dead_ends, first_correct_file_hop, files_opened_after_first_correct_hop,
post_hit_dead_ends, tool_calls (object), duration_seconds, answer (your
text), citations (array of {path, line, note}), correct='ungraded',
correctness_notes='', grading_method='ungraded', quality_self_score
(1-10), risk_flag (boolean), risk_flag_explanation.

Set correct='ungraded' — the reviewer grades later.
For non-cli capture_method (capture_method != 'cli'), tool-level fields
(tool_calls, first_correct_file_hop, files_opened_after_first_correct_hop,
post_hit_dead_ends) may be null.

Do NOT read GROUND_TRUTH.md. Cite exact files and line numbers for
factual claims. Track files opened, dead ends, durations honestly.
EOF
}

# --- Pane setup ----------------------------------------------------------

# Send keys to whatever pane is currently active in the named window.
# Avoids hard-coding pane indices, which depend on tmux's pane-base-index.
setup_active_pane() {
  local window="$1" condition="$2" agent="$3" capture="$4" invoke_hint="$5"
  local promptfile="$RERUN_DIR/.prompt-${agent}-${condition}.txt"
  build_prompt "$agent" "$capture" "$condition" "$promptfile"

  tmux send-keys -t "$window" "cd '$RERUN_DIR/$condition'" Enter
  tmux send-keys -t "$window" "clear" Enter
  tmux send-keys -t "$window" "echo '====== $agent / $condition (capture=$capture) ======'" Enter
  tmux send-keys -t "$window" "echo 'Working dir: \$(pwd)'" Enter
  tmux send-keys -t "$window" "echo 'EXPERIMENT.md: ../EXPERIMENT.md (do NOT read GROUND_TRUTH.md)'" Enter
  tmux send-keys -t "$window" "echo 'Results out:   ../results/$agent/$condition/<task_id>.json'" Enter
  tmux send-keys -t "$window" "echo ''" Enter
  tmux send-keys -t "$window" "echo 'INVOKE: $invoke_hint'" Enter
  tmux send-keys -t "$window" "echo 'Then paste the prompt below into the agent.'" Enter
  tmux send-keys -t "$window" "echo ''" Enter
  tmux send-keys -t "$window" "echo '----- PROMPT (copy this) -----'" Enter
  tmux send-keys -t "$window" "cat '$promptfile'" Enter
  tmux send-keys -t "$window" "echo '------------------------------'" Enter
  tmux send-keys -t "$window" "echo ''" Enter
}

create_window() {
  local agent="$1" capture="$2" invoke_hint="$3"
  local win="$SESSION:$agent"

  if [[ "$agent" == "claude" ]]; then
    tmux new-session -d -s "$SESSION" -n "$agent"
  else
    tmux new-window -t "$SESSION" -n "$agent"
  fi
  # On window creation the single pane is active — set up bare first.
  setup_active_pane "$win" "bare" "$agent" "$capture" "$invoke_hint"
  # Split horizontally; the newly-created bottom pane becomes active.
  tmux split-window -v -t "$win"
  setup_active_pane "$win" "structured_fresh" "$agent" "$capture" "$invoke_hint"
}

# --- Build the matrix ----------------------------------------------------

create_window "claude"   "cli"    "claude   (interactive: just run 'claude' and paste the prompt)"
create_window "codex"    "cli"    "codex    (interactive: just run 'codex' and paste the prompt)"
create_window "cursor"   "cli"    "cursor-agent --print --output-format json   (or run 'cursor-agent' for interactive)"
create_window "opencode" "tunnel" "opencode-play   (uses local OSS tunnel at 127.0.0.1:11434)"

# Land on the claude window so attach starts there. Use directional
# pane select so this works regardless of pane-base-index.
tmux select-window -t "$SESSION:claude"
tmux select-pane -t "$SESSION:claude" -U 2>/dev/null || true

cat <<EOF

Tmux session ready.

  Attach:    tmux attach -t $SESSION
  Detach:    Ctrl-b d
  Switch:    Ctrl-b n  (next window) / Ctrl-b p  (previous)
  Pane:      Ctrl-b o  (next pane in window)
  Kill all:  tmux kill-session -t $SESSION

Eight cells (4 agents × 2 conditions). Per cell:
  1. Invoke the CLI shown in 'INVOKE'.
  2. Paste the prompt printed in the pane.
  3. Wait for the agent to write 6 JSON result files under
     $RERUN_DIR/results/<agent>/<condition>/.

Prompt files (also written here for reference):
  $RERUN_DIR/.prompt-{claude,codex,cursor,opencode}-{bare,structured_fresh}.txt
EOF
