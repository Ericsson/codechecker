#!/bin/bash
set -euo pipefail

# Force LLVM 14 to match Linux/macOS CI.
choco install llvm --version=14.0.6 --allow-downgrade -y
choco install cppcheck -y

echo "C:\Program Files\LLVM\bin" >> "$GITHUB_PATH"
echo "C:\Program Files\Cppcheck" >> "$GITHUB_PATH"

