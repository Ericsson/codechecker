#!/bin/bash

# Pin LLVM to 14 to match Linux/macOS CI.
choco install llvm --version=14.0.6 -y
choco install cppcheck -y

echo "C:\Program Files\LLVM\bin" >> "$GITHUB_PATH"
echo "C:\Program Files\Cppcheck" >> "$GITHUB_PATH"
