#!/usr/bin/env bash
# Verify that CodeChecker data files are installed in the expected location.
set -euo pipefail

DATA_DIR="$(python -c "import sysconfig; print(sysconfig.get_path('data'))")"
CFG_DIR="$DATA_DIR/share/codechecker/config"

if [ ! -d "$CFG_DIR" ]; then
  echo "ERROR: Config dir missing: $CFG_DIR" >&2
  exit 1
fi

if [ ! -f "$CFG_DIR/package_layout.json" ]; then
  echo "ERROR: package_layout.json missing in $CFG_DIR" >&2
  exit 1
fi

echo "OK: data files verified in $CFG_DIR"
