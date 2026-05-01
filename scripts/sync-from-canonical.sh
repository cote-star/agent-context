#!/bin/sh
# sync-from-canonical.sh — copy canonical agent-context files from team_skills
# into this public repo's tools/, templates/, and docs/.
#
# Usage:
#   scripts/sync-from-canonical.sh [--canonical-path PATH] [--dry-run]
#
# Default canonical path:
#   ~/sandbox/work/cross-team-repos/team_skills/skills/agent-context
#
# See docs/SYNC.md for the three-way sync policy (team_skills canonical →
# agent-chorus/skills + agent-context public).
#
# Files INTENTIONALLY NOT OVERWRITTEN by this script (public-variant maintained
# in-tree, divergence-by-design):
#   - tools/verify_context_pack.py   (public CLI + stdlib-only validation)
#   - templates/manifest.json         (public agent_context_version field)
#   - docs/architecture.md            (public CLI and tier-model wording)
#
# If a future sync needs to pick up changes to the canonical versions of those
# files, the maintainer merges them by hand.

set -eu

CANONICAL="${HOME}/sandbox/work/cross-team-repos/team_skills/skills/agent-context"
DRY_RUN=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --canonical-path)
      CANONICAL="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$CANONICAL" ]; then
  echo "ERROR: canonical path does not exist: $CANONICAL" >&2
  exit 1
fi

copied=0
patched=0
skipped=0
dropped=0

# Helper: copy src -> dest, honoring dry-run.
do_copy() {
  src="$1"
  dst="$2"
  if [ ! -f "$src" ]; then
    echo "  skip (missing): $src"
    skipped=$((skipped + 1))
    return
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  DRY: copy $src -> $dst"
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "  copy: $(basename "$src") -> $dst"
  fi
  copied=$((copied + 1))
}

echo "sync-from-canonical: $CANONICAL -> $REPO_ROOT (dry-run=$DRY_RUN)"
echo

echo "tools/ (verbatim):"
do_copy "$CANONICAL/scripts/check_freshness.sh"   "$REPO_ROOT/tools/check_freshness.sh"
do_copy "$CANONICAL/references/pre-push-hook.sh"  "$REPO_ROOT/tools/pre-push-hook.sh"
echo "  HOLD (public variant maintained here): tools/verify_context_pack.py"

echo
echo "docs/ (verbatim):"
do_copy "$CANONICAL/references/design-principles.md" "$REPO_ROOT/docs/design-principles.md"
do_copy "$CANONICAL/references/ci-adaptation.md"     "$REPO_ROOT/docs/ci-adaptation.md"
echo "  HOLD (public variant describes public CLI/tier model): docs/architecture.md"

echo
echo "templates/ (verbatim):"
do_copy "$CANONICAL/references/templates/00_START_HERE.md"           "$REPO_ROOT/templates/00_START_HERE.md"
do_copy "$CANONICAL/references/templates/10_SYSTEM_OVERVIEW.md"      "$REPO_ROOT/templates/10_SYSTEM_OVERVIEW.md"
do_copy "$CANONICAL/references/templates/20_CODE_MAP.md"             "$REPO_ROOT/templates/20_CODE_MAP.md"
do_copy "$CANONICAL/references/templates/30_BEHAVIORAL_INVARIANTS.md" "$REPO_ROOT/templates/30_BEHAVIORAL_INVARIANTS.md"
do_copy "$CANONICAL/references/templates/40_OPERATIONS_AND_RELEASE.md" "$REPO_ROOT/templates/40_OPERATIONS_AND_RELEASE.md"
do_copy "$CANONICAL/references/templates/acceptance_tests.md"        "$REPO_ROOT/templates/acceptance_tests.md"
do_copy "$CANONICAL/references/templates/search_scope.json"          "$REPO_ROOT/templates/search_scope.json"
do_copy "$CANONICAL/references/templates/routes.json"                "$REPO_ROOT/templates/routes.json"
do_copy "$CANONICAL/references/templates/completeness_contract.json" "$REPO_ROOT/templates/completeness_contract.json"
do_copy "$CANONICAL/references/templates/reporting_rules.json"       "$REPO_ROOT/templates/reporting_rules.json"
echo "  HOLD (public variant uses agent_context_version): templates/manifest.json"

echo
echo "DROPPED (chorus-specific content):"
echo "  - references/getting-started.md"
echo "  - references/ci-example.yml"
dropped=$((dropped + 2))

if [ "$DRY_RUN" -eq 0 ]; then
  echo
  echo "Scanning JSON templates for unreplaced markers..."
  leaks=0
  for f in "$REPO_ROOT/templates"/*.json; do
    [ -f "$f" ] || continue
    # {name}, {domain}, {module} are template placeholders the canonical doc
    # uses that must never leak. REPLACE is the canonical's actual marker — it
    # is expected in templates, so we don't fail on it here.
    if grep -qE '\{name\}|\{domain\}|\{module\}' "$f"; then
      echo "WARN: placeholder leak in $(basename "$f")" >&2
      leaks=$((leaks + 1))
    fi
  done
  if [ "$leaks" -eq 0 ]; then
    echo "OK: JSON template placeholder scan passed."
  fi
fi

echo
echo "Summary: copied=$copied patched=$patched dropped=$dropped held=3 skipped=$skipped"
echo "Review changes with 'git diff', then commit."
