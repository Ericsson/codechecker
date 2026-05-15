#!/usr/bin/env bash
# Smoke test: run CodeChecker analyze + parse on a trivial source file.
set -euo pipefail

WORK="${RUNNER_TEMP:-/tmp}/analyze-test"
mkdir -p "$WORK"

cat > "$WORK/main.c" <<'EOF'
int main() { int i = 1 / 0; return i; }
EOF

cat > "$WORK/compile_commands.json" <<EOF
[{"directory": "$WORK", "command": "gcc -c $WORK/main.c", "file": "$WORK/main.c"}]
EOF

CodeChecker analyze "$WORK/compile_commands.json" -o "$WORK/reports"

COUNT="$(CodeChecker parse "$WORK/reports" -e json | jq '.reports | length')"
if [ "$COUNT" -lt 1 ]; then
  echo "ERROR: Expected at least one report, got $COUNT" >&2
  exit 1
fi

echo "OK: found $COUNT report(s)"
