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

# analyze exits 0: clangsa, clang-tidy, cppcheck all succeed.
# gcc has no checkers enabled but is not considered a failure.
CodeChecker analyze "$WORK/compile_commands.json" -o "$WORK/reports"

# parse exits 2: at least one report was emitted (division by zero).
COUNT="$( (CodeChecker parse "$WORK/reports" -e json; rc=$?; [ $rc -eq 2 ] || exit $rc) | jq '.reports | length')"
if [ "$COUNT" -lt 1 ]; then
  echo "ERROR: Expected at least one report, got $COUNT" >&2
  exit 1
fi

echo "OK: found $COUNT report(s)"
