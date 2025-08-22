#!/bin/bash

# CodeChecker Automatic Rebuild Script
# This script rebuilds the CodeChecker package with API build first

set -e  # Exit on any error

echo "Starting CodeChecker Thrift rebuild process..."

# Step 1: Build the API
echo "Step 1: Building API..."
cd "$HOME/codechecker/web/api"
make build

# Step 2: Execute the main rebuild process
echo "Step 2: Executing main rebuild..."
cd "$HOME/codechecker"

# Deactivation of virtual enviroment
echo "Deactivating current environment..."
if command -v deactivate &> /dev/null; then
    deactivate 2>/dev/null || true
fi

# Resetting the package-lock.json just in case.
echo "Resetting package-lock.json..."
git checkout master -- "$HOME/codechecker/web/server/vue-cli/package-lock.json"
git reset HEAD "$HOME/codechecker/web/server/vue-cli/package-lock.json"

# cleaning.
echo "Cleaning previous builds..."
make clean
make clean_venv_dev

#Creating new virtual enviroment.
echo "Creating new virtual environment..."
make venv_dev

echo "Building package..."
make package

# Again just in case.
echo "Activating virtual environment and setting PATH..."
source "$HOME/codechecker/venv_dev/bin/activate"
export PATH="$HOME/codechecker/build/CodeChecker/bin:$PATH"

echo "CodeChecker rebuild completed successfully!"
echo "Virtual environment is activated and PATH is set."
echo "You can now use CodeChecker commands."
