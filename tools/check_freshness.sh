#!/bin/sh
# Check whether context-relevant files changed without a corresponding pack update.

set -eu

BASE_REF="${BASE_REF:-origin/main}"
CONTEXT_RELEVANT_PATHS="${CONTEXT_RELEVANT_PATHS:-app/ src/ lib/ migrations/}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-ref)
      BASE_REF="$2"
      shift 2
      ;;
    --paths)
      CONTEXT_RELEVANT_PATHS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

CODE_CHANGED=$(git diff --name-only "$BASE_REF"...HEAD -- $CONTEXT_RELEVANT_PATHS | wc -l | tr -d ' ')
PACK_CHANGED=$(git diff --name-only "$BASE_REF"...HEAD -- .agent-context/ | wc -l | tr -d ' ')

if [ "$CODE_CHANGED" -gt 0 ] && [ "$PACK_CHANGED" -eq 0 ]; then
  echo "ERROR: $CODE_CHANGED context-relevant files changed but .agent-context/ was not updated"
  echo "  base ref: $BASE_REF"
  echo "  checked paths: $CONTEXT_RELEVANT_PATHS"
  echo "  changed context-relevant files:"
  git diff --name-only "$BASE_REF"...HEAD -- $CONTEXT_RELEVANT_PATHS | sed 's/^/    - /'
  echo "  next: update .agent-context/current/ or narrow CONTEXT_RELEVANT_PATHS if these files are outside the pack scope"
  exit 1
fi

echo "OK: freshness check passed ($CODE_CHANGED context-relevant changes, $PACK_CHANGED pack changes)"
if [ "$CODE_CHANGED" -gt 0 ]; then
  echo "  changed context-relevant files:"
  git diff --name-only "$BASE_REF"...HEAD -- $CONTEXT_RELEVANT_PATHS | sed 's/^/    - /'
fi
if [ "$PACK_CHANGED" -gt 0 ]; then
  echo "  changed pack files:"
  git diff --name-only "$BASE_REF"...HEAD -- .agent-context/ | sed 's/^/    - /'
fi
