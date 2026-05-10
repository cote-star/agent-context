#!/usr/bin/env bash
# Render the HTML deck to a 21-page 1280x720 PDF.
#
# Usage:
#   ./render-pdf.sh
#   ./render-pdf.sh cursor-meetup-may-2026-v2.html cursor-meetup-may-2026-v2.pdf
#
# Picks the first available headless browser. Run from inside talk/.
# Requires Chrome / Chromium / Microsoft Edge installed locally.

set -euo pipefail
cd "$(dirname "$0")"

IN="$(pwd)/${1:-cursor-meetup-may-2026.html}"
OUT="$(pwd)/${2:-cursor-meetup-may-2026.pdf}"
PROFILE_DIR="${TMPDIR:-/tmp}/agent-context-chrome-pdf"

CANDIDATES=(
  "google-chrome"
  "google-chrome-stable"
  "chromium"
  "chromium-browser"
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  "/Applications/Chromium.app/Contents/MacOS/Chromium"
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
)

BIN=""
for c in "${CANDIDATES[@]}"; do
  if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then
    BIN="$c"; break
  fi
done

if [ -z "$BIN" ]; then
  echo "❌ No Chrome/Chromium/Edge found. Install Chrome and re-run, or:"
  echo "   1. open cursor-meetup-may-2026.html in your browser"
  echo "   2. press P (deck shortcut) or Cmd/Ctrl+P"
  echo "   3. Destination = Save as PDF · Layout = Landscape ·"
  echo "      Margins = None · Background graphics = ON · Pages = All"
  exit 1
fi

echo "→ Rendering with: $BIN"
"$BIN" \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --disable-dev-shm-usage \
  --user-data-dir="$PROFILE_DIR" \
  --hide-scrollbars \
  --no-pdf-header-footer \
  --print-to-pdf-no-header \
  --print-to-pdf="$OUT" \
  --virtual-time-budget=4000 \
  "file://$IN" &
PID=$!

for _ in {1..40}; do
  if [ -s "$OUT" ]; then
    break
  fi
  if ! kill -0 "$PID" >/dev/null 2>&1; then
    wait "$PID"
    break
  fi
  sleep 0.25
done

if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID" >/dev/null 2>&1 || true
  wait "$PID" >/dev/null 2>&1 || true
fi

if [ -f "$OUT" ]; then
  echo "✓ Wrote $OUT"
  ls -lh "$OUT"
else
  echo "❌ PDF was not produced. Check Chrome version supports --print-to-pdf."
  exit 1
fi
