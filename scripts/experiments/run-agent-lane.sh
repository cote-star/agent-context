#!/usr/bin/env bash
# run-agent-lane.sh — run one agent/condition lane across the active repo slate.
#
# A "lane" is one agent × one condition, for example:
#   claude / bare
#   codex  / structured_fresh
#
# The script runs each repo in a fresh non-interactive agent process, using the
# per-repo prompt files emitted by launch-tmux-matrix.sh / prepare scaffolding.
# This keeps the operator surface to 6 lanes while avoiding one giant multi-repo
# chat that leaks context from repo to repo.
#
# Usage:
#   scripts/experiments/run-agent-lane.sh --agent claude --condition bare
#   scripts/experiments/run-agent-lane.sh --agent codex --condition structured_fresh --force
#
# Defaults:
#   rerun root must be passed with --rerun-root or RERUN_ROOT
#   aliases=the active public rerun slate

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/experiments/run-agent-lane.sh \
    --agent claude|codex|cursor \
    --condition bare|structured_fresh \
    [--model MODEL_ID] \
    [--rerun-root PATH] \
    [--aliases alias1,alias2,...] \
    [--force] \
    [--dry-run]

Runs one agent/condition lane across all requested aliases. Each alias is run in
a fresh non-interactive agent process from that alias's bare/ or
structured_fresh/ clone. Expected output per alias: 6 result JSON files.

Options:
  --model       Cursor model id (e.g. claude-opus-4-7-medium, composer-2-fast).
                Only valid with --agent cursor. When set, results land under a
                per-model subdirectory so concurrent cursor lanes with
                different models don't overwrite each other.
  --force       Run even if 6 result JSON files already exist for that cell.
  --dry-run     Print commands and prompt paths, but do not invoke agents.

Examples:
  scripts/experiments/run-agent-lane.sh --agent claude --condition bare
  scripts/experiments/run-agent-lane.sh --agent cursor --condition structured_fresh --dry-run
  scripts/experiments/run-agent-lane.sh --agent cursor --condition bare \
    --model claude-opus-4-7-medium --dry-run
USAGE
}

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }

AGENT=""
CONDITION=""
MODEL=""
RERUN_ROOT="${RERUN_ROOT:-}"
# org-second-brain dropped from default 2026-05-10 — interactive claude
# session ran in circles without writing results; pack/EXPERIMENT setup
# needs review before re-including. Other agents' results for that repo
# are also held back (see <rerun>/org-second-brain/.skipped).
ALIASES_CSV="agent-chorus,ml-pipeline-reference,react-frontend-reference,backend-service-reference,polyglot-monorepo-reference,daemon-reference"
FORCE=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="${2:-}"; shift 2 ;;
    --condition) CONDITION="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --rerun-root) RERUN_ROOT="${2:-}"; shift 2 ;;
    --aliases) ALIASES_CSV="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

# slugify: lowercase, replace any run of non-[a-z0-9-] with a single '-',
# then collapse runs of '-' and trim leading/trailing '-'.
# Examples:
#   "Claude Opus 4.7 Medium"  -> "claude-opus-4-7-medium"
#   "claude-opus-4-7-medium"  -> "claude-opus-4-7-medium"
#   "Composer 2 Fast"         -> "composer-2-fast"
slugify() {
  local s="$1"
  s="$(printf '%s' "$s" | tr '[:upper:]' '[:lower:]')"
  s="$(printf '%s' "$s" | sed -e 's/[^a-z0-9-]\{1,\}/-/g' -e 's/-\{2,\}/-/g' -e 's/^-//' -e 's/-$//')"
  printf '%s' "$s"
}

case "$AGENT" in
  claude|codex|cursor) ;;
  "") usage >&2; exit 1 ;;
  *) die "unsupported agent: $AGENT (expected claude, codex, cursor)" ;;
esac

case "$CONDITION" in
  bare|structured_fresh) ;;
  "") usage >&2; exit 1 ;;
  *) die "unsupported condition: $CONDITION (expected bare or structured_fresh)" ;;
esac

if [[ -n "$MODEL" && "$AGENT" != "cursor" ]]; then
  die "--model is only supported with --agent cursor in this harness (got --agent $AGENT)"
fi

RERUN_ROOT="${RERUN_ROOT/#\~/$HOME}"
[[ -n "$RERUN_ROOT" ]] || die "rerun root required: pass --rerun-root PATH or set RERUN_ROOT"
[[ -d "$RERUN_ROOT" ]] || die "rerun root not found: $RERUN_ROOT"

case "$AGENT" in
  claude) command -v claude >/dev/null || die "claude not found on PATH" ;;
  codex) command -v codex >/dev/null || die "codex not found on PATH" ;;
  cursor) command -v cursor-agent >/dev/null || die "cursor-agent not found on PATH" ;;
esac

IFS=',' read -r -a ALIASES <<< "$ALIASES_CSV"

_cleanup_tmp_prompt() {
  if [[ -n "${tmp_prompt:-}" && -f "$tmp_prompt" ]]; then
    rm -f "$tmp_prompt"
  fi
}

run_cell() {
  local alias="$1"
  local rerun="$RERUN_ROOT/$alias"
  local cwd="$rerun/$CONDITION"
  local prompt="$rerun/.prompt-$AGENT-$CONDITION.txt"
  local outdir="$rerun/results/$AGENT/$CONDITION"
  local logdir="$rerun/_logs/$AGENT/$CONDITION"
  local model_slug=""
  if [[ -n "$MODEL" ]]; then
    model_slug="$(slugify "$MODEL")"
    outdir="$outdir/$model_slug"
    logdir="$logdir/$model_slug"
  fi
  local started
  started="$(date -u +'%Y%m%dT%H%M%SZ')"

  [[ -d "$cwd" ]] || die "$alias: missing condition dir: $cwd"
  [[ -f "$prompt" ]] || die "$alias: missing prompt file: $prompt"
  [[ -d "$outdir" ]] || die "$alias: missing results dir: $outdir"
  mkdir -p "$logdir"

  # When --model is set, the result outdir gains a model-slug subdir, but the
  # prompt file (generated by launch-tmux-matrix.sh, model-agnostic) still
  # tells the agent to write to ../results/$AGENT/$CONDITION/<task>.json. The
  # agent would then write outside the model-aware outdir and run-agent-lane.sh
  # would not see the JSONs as completed. Substitute the path in a temp prompt
  # so the agent writes to the model-aware outdir.
  local tmp_prompt=""
  trap _cleanup_tmp_prompt RETURN
  if [[ -n "$MODEL" ]]; then
    tmp_prompt="$(mktemp -t agent-context-prompt-XXXXXX)"
    sed "s|results/$AGENT/$CONDITION/|results/$AGENT/$CONDITION/$model_slug/|g" "$prompt" > "$tmp_prompt"
    prompt="$tmp_prompt"
  fi

  local existing
  existing="$(find "$outdir" -maxdepth 1 -name '*.json' -not -name '*.judge.json' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$existing" == "6" && "$FORCE" -ne 1 ]]; then
    echo "[$alias][$AGENT/$CONDITION] SKIP: already has 6 result JSONs ($outdir)"
    return 0
  fi

  echo
  echo "================================================================="
  echo "[$alias][$AGENT/$CONDITION] START"
  if [[ -n "$MODEL" ]]; then
    echo "model:  $MODEL"
  fi
  echo "cwd:    $cwd"
  echo "prompt: $prompt"
  echo "out:    $outdir"
  echo "log:    $logdir/$started.log"
  echo "================================================================="

  if [[ "$DRY_RUN" -eq 1 ]]; then
    case "$AGENT" in
      claude) echo "(cd '$cwd' && claude -p --permission-mode bypassPermissions \"\$(cat '$prompt')\")" ;;
      codex) echo "(cd '$cwd' && codex exec --dangerously-bypass-approvals-and-sandbox - < '$prompt')" ;;
      cursor)
        if [[ -n "$MODEL" ]]; then
          echo "(cd '$cwd' && cursor-agent --print --trust --force --workspace '$cwd' --model '$MODEL' \"\$(cat '$prompt')\")"
        else
          echo "(cd '$cwd' && cursor-agent --print --trust --force --workspace '$cwd' \"\$(cat '$prompt')\")"
        fi
        ;;
    esac
    if [[ -n "$tmp_prompt" ]]; then
      echo "--- effective prompt (model-substituted) ---"
      cat "$tmp_prompt"
      echo "--- end effective prompt ---"
    fi
    return 0
  fi

  set +e
  case "$AGENT" in
    claude)
      (cd "$cwd" && claude -p --permission-mode bypassPermissions "$(cat "$prompt")") \
        > "$logdir/$started.log" 2>&1
      ;;
    codex)
      (cd "$cwd" && codex exec --dangerously-bypass-approvals-and-sandbox - < "$prompt") \
        > "$logdir/$started.log" 2>&1
      ;;
    cursor)
      if [[ -n "$MODEL" ]]; then
        (cd "$cwd" && cursor-agent --print --trust --force --workspace "$cwd" --model "$MODEL" "$(cat "$prompt")") \
          > "$logdir/$started.log" 2>&1
      else
        (cd "$cwd" && cursor-agent --print --trust --force --workspace "$cwd" "$(cat "$prompt")") \
          > "$logdir/$started.log" 2>&1
      fi
      ;;
  esac
  local rc=$?
  set -e

  local count
  count="$(find "$outdir" -maxdepth 1 -name '*.json' -not -name '*.judge.json' 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$rc" -ne 0 ]]; then
    warn "$alias $AGENT/$CONDITION exited rc=$rc; result_count=$count/6; see $logdir/$started.log"
    return "$rc"
  fi
  if [[ "$count" != "6" ]]; then
    warn "$alias $AGENT/$CONDITION finished but result_count=$count/6; see $logdir/$started.log"
    return 2
  fi

  echo "[$alias][$AGENT/$CONDITION] OK: 6/6 results"
}

FAILS=0
for alias in "${ALIASES[@]}"; do
  alias="$(echo "$alias" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [[ -z "$alias" ]] && continue
  if ! run_cell "$alias"; then
    FAILS=$((FAILS + 1))
  fi
done

echo
if [[ "$FAILS" -eq 0 ]]; then
  echo "LANE OK: $AGENT/$CONDITION completed for ${#ALIASES[@]} aliases"
else
  echo "LANE PARTIAL: $AGENT/$CONDITION had $FAILS failing alias(es)"
  exit 2
fi
