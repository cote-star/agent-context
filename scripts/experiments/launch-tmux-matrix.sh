#!/usr/bin/env bash
# launch-tmux-matrix.sh — open a tmux session for one repo's experiment runs.
#
# Usage:
#   scripts/experiments/launch-tmux-matrix.sh <alias>
#
#   RERUN_ROOT=/custom/path scripts/experiments/launch-tmux-matrix.sh <alias>
#
# Creates session "rerun-<alias>" with ONE window ("cells") containing
# 8 panes in a 4×2 grid (4 agents across, 2 conditions stacked):
#
#   +------------+-----------+------------+--------------+
#   | claude     | codex     | cursor     | opencode     |
#   |   bare     |   bare    |   bare     |   bare       |
#   +------------+-----------+------------+--------------+
#   | claude     | codex     | cursor     | opencode     |
#   |  s_fresh   |  s_fresh  |  s_fresh   |  s_fresh     |
#   +------------+-----------+------------+--------------+
#
# All 8 cells visible at once so permission prompts can't hide on a
# different window. Each pane shows its title (agent / condition) on
# the pane border, the working dir, the invoke hint, and a
# `cat <prompt-file> | pbcopy` line to copy that cell's prompt.
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
# to copy/paste into the agent CLI. ALIAS is injected literally so the
# agent writes a concrete `"repo": "<alias>"` value (not a placeholder).
build_prompt() {
  local agent="$1" capture="$2" condition="$3" outfile="$4"
  cat > "$outfile" <<EOF
Read ../EXPERIMENT.md and follow it exactly.

agent           = $agent
capture_method  = $capture
condition       = $condition
repo            = $ALIAS

Write one JSON result file per task (L1, L2, M1, M2, H1, H2) to:
  ../results/$agent/$condition/<task_id>.json

The schema is at ../result.schema.json. Required fields include:
  task_id
  agent='$agent'
  capture_method='$capture'
  condition='$condition'
  repo='$ALIAS'
  started_at, finished_at  (ISO 8601 UTC, e.g. 2026-05-04T15:00:00Z)
  files_opened_count, dead_ends
  first_correct_file_hop, files_opened_after_first_correct_hop, post_hit_dead_ends
  tool_calls (object), duration_seconds
  answer (your text), citations (array of {path, line, note})
  correct='ungraded', correctness_notes=''
  grading_method='ungraded'
  quality_self_score (1-10), risk_flag (boolean), risk_flag_explanation

Set correct='ungraded' — the reviewer grades later.
For non-cli capture_method (capture_method != 'cli'), tool-level fields
(tool_calls, first_correct_file_hop, files_opened_after_first_correct_hop,
post_hit_dead_ends) may be null.

Optional fields (leave null if your CLI doesn't expose them — the harness
will extract post-hoc from session telemetry):
  tokens_input, tokens_output, tokens_total, tokens_cached, cost_usd
  model_id (the exact model identifier you ran)
  permission_prompts_count (how many times you paused for approval)
  interrupted (true if you hit a turn/context cap, false otherwise)

Do NOT read GROUND_TRUTH.md. Cite exact files and line numbers for
factual claims. Track files opened, dead ends, durations honestly.
EOF
}

# --- Pane setup ----------------------------------------------------------

# Send keys to a specific pane addressed by tmux pane ID (#{pane_id}).
# Stable across layout changes — preferred over indexed addressing.
setup_pane_by_id() {
  local pane_id="$1" condition="$2" agent="$3" capture="$4" invoke_hint="$5"
  local promptfile="$RERUN_DIR/.prompt-${agent}-${condition}.txt"
  build_prompt "$agent" "$capture" "$condition" "$promptfile"

  # Pane title shows up in the pane border (pane-border-status top).
  tmux select-pane -t "$pane_id" -T "$agent / $condition"

  tmux send-keys -t "$pane_id" "cd '$RERUN_DIR/$condition'" Enter
  tmux send-keys -t "$pane_id" "clear" Enter
  tmux send-keys -t "$pane_id" "echo '== $agent / $condition (capture=$capture) =='" Enter
  tmux send-keys -t "$pane_id" "echo 'Out: ../results/$agent/$condition/<task>.json'" Enter
  tmux send-keys -t "$pane_id" "echo ''" Enter
  tmux send-keys -t "$pane_id" "echo 'INVOKE: $invoke_hint'" Enter
  tmux send-keys -t "$pane_id" "echo ''" Enter
  tmux send-keys -t "$pane_id" "echo 'Prompt file:'" Enter
  tmux send-keys -t "$pane_id" "echo '  $promptfile'" Enter
  tmux send-keys -t "$pane_id" "echo ''" Enter
  tmux send-keys -t "$pane_id" "echo 'Copy with:  cat $promptfile | pbcopy'" Enter
  tmux send-keys -t "$pane_id" "echo ''" Enter
}

# --- Build the matrix: ONE window, 8 panes in 4×2 grid ------------------
# Layout target:
#   +-------------+-------------+-------------+-------------+
#   | claude/bare | codex/bare  | cursor/bare | opencode/   |
#   |             |             |             |   bare      |
#   +-------------+-------------+-------------+-------------+
#   | claude/sf   | codex/sf    | cursor/sf   | opencode/sf |
#   +-------------+-------------+-------------+-------------+
# 4 agents left-to-right (same order on both rows). Top row = bare,
# bottom row = structured_fresh. All 8 cells visible at once so you
# never miss a permission prompt.

# Step 1: create session. The -x/-y flags set the headless canvas
# large enough to accommodate 8 panes; tmux refits to the actual
# terminal size on attach. Without this, splits fail with "no space
# for new pane" because the default 80x24 canvas can't hold 4 columns.
tmux new-session -d -s "$SESSION" -n cells -x 240 -y 60

# Step 2: build 4 columns by splitting horizontally with explicit
# pane-ID targeting (so each split goes to the rightmost column, not
# the recursively shrinking active pane).
P_TL_1=$(tmux list-panes -t "$SESSION:cells" -F '#{pane_id}' | head -1)
P_TL_2=$(tmux split-window -h -t "$P_TL_1" -P -F '#{pane_id}')
P_TL_3=$(tmux split-window -h -t "$P_TL_2" -P -F '#{pane_id}')
P_TL_4=$(tmux split-window -h -t "$P_TL_3" -P -F '#{pane_id}')
tmux select-layout -t "$SESSION:cells" even-horizontal

# Step 3: split each column vertically to add the bottom row. Default
# split is 50/50 per column, so the result is a clean 4-column × 2-row
# grid. (We deliberately do NOT call `select-layout tiled` afterwards
# because tmux's tiled algorithm picks based on aspect ratio and on a
# narrow canvas would scramble our 4×2 into a 3×3-ish layout.)
P_BL_1=$(tmux split-window -v -t "$P_TL_1" -P -F '#{pane_id}')
P_BL_2=$(tmux split-window -v -t "$P_TL_2" -P -F '#{pane_id}')
P_BL_3=$(tmux split-window -v -t "$P_TL_3" -P -F '#{pane_id}')
P_BL_4=$(tmux split-window -v -t "$P_TL_4" -P -F '#{pane_id}')

# Step 4: even-vertical evens out the row heights within each column.
# (No 4×2 grid built-in — but the column splits + this row-evening get
# us where we want without the tiled scramble.)

# Step 5: per-pane title border so each cell is labeled.
tmux setw -t "$SESSION:cells" pane-border-status top
tmux setw -t "$SESSION:cells" pane-border-format ' #T '

# Step 6: assign cells to known pane IDs.
#   Top row    = bare condition for each agent
#   Bottom row = structured_fresh for each agent
#   Columns left-to-right: claude, codex, cursor, opencode
setup_pane_by_id "$P_TL_1" "bare"             "claude"   "cli"    "claude    (interactive: run 'claude' and paste the prompt)"
setup_pane_by_id "$P_TL_2" "bare"             "codex"    "cli"    "codex     (interactive: run 'codex' and paste the prompt)"
setup_pane_by_id "$P_TL_3" "bare"             "cursor"   "cli"    "cursor-agent   (interactive: 'cursor-agent' then paste the prompt)"
setup_pane_by_id "$P_TL_4" "bare"             "opencode" "tunnel" "OPENCODE_MODEL=ollama/devstral-small-2 opencode-play"
setup_pane_by_id "$P_BL_1" "structured_fresh" "claude"   "cli"    "claude    (interactive)"
setup_pane_by_id "$P_BL_2" "structured_fresh" "codex"    "cli"    "codex     (interactive)"
setup_pane_by_id "$P_BL_3" "structured_fresh" "cursor"   "cli"    "cursor-agent   (interactive)"
setup_pane_by_id "$P_BL_4" "structured_fresh" "opencode" "tunnel" "OPENCODE_MODEL=ollama/devstral-small-2 opencode-play"

# Step 7: land focus on the top-left (claude/bare).
tmux select-pane -t "$P_TL_1"

cat <<EOF

Tmux session ready.

  Attach:    tmux attach -t $SESSION
  Detach:    Ctrl-b d
  Pane:      Ctrl-b o (next pane) | Ctrl-b arrows (directional)
  Zoom one:  Ctrl-b z (toggle a pane to fullscreen and back)
  Kill all:  tmux kill-session -t $SESSION

One window, 8 panes. Top row = bare. Bottom row = structured_fresh.
Columns left-to-right: claude, codex, cursor, opencode.

Per pane:
  1. Invoke the CLI shown in 'INVOKE'.
  2. Paste the prompt — easiest from another terminal:
       cat $RERUN_DIR/.prompt-<agent>-<condition>.txt | pbcopy
     then Cmd-V into the agent.
  3. Wait for 6 JSON result files under ../results/<agent>/<condition>/.

Prompt files for copy-paste:
  $RERUN_DIR/.prompt-{claude,codex,cursor,opencode}-{bare,structured_fresh}.txt
EOF
