#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing North America Market Brief kit into: $HERMES_HOME"
mkdir -p "$HERMES_HOME/skills" "$HERMES_HOME/scripts"
cp -R "$ROOT/skills/"* "$HERMES_HOME/skills/"
cp "$ROOT/scripts/"*.py "$HERMES_HOME/scripts/"
chmod +x "$HERMES_HOME/scripts/"*.py

echo "Installed skills:"
find "$ROOT/skills" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; | sort

echo
cat <<'MSG'
Next step: create a Hermes cron job using cron-templates/north-america-market-brief.json.
Recommended smoke test:
  ./verify.sh
MSG
