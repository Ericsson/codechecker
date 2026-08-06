#!/bin/bash

set -e  # Exit on any error

echo "Starting CodeChecker Thrift rebuild process..."

# Resolve the repository root from the script's location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# check if which enviroment to create is passed as an argument.
if [[ "$1" == "venv" || "$1" == "venv_dev" ]]; then
    ENV_TYPE="$1"
else
    echo "Error: You must specify 'venv' or 'venv_dev' as the first argument."
    echo "Usage: $0 <venv|venv_dev>"
    exit 1
fi

# Step 1: Build the API
echo "Step 1: Building API..."
cd "$REPO_ROOT/web/api"
make build

# Step 2: Execute the main rebuild process
echo "Step 2: Executing main rebuild..."
cd "$REPO_ROOT"

# Deactivation of virtual enviroment
echo "Deactivating current environment..."
if command -v deactivate &> /dev/null; then
    deactivate 2>/dev/null || true
fi

# Resetting the package-lock.json just in case
echo "Resetting package-lock.json..."
git checkout master -- "$REPO_ROOT/web/server/vue-cli/package-lock.json"
git reset HEAD "$REPO_ROOT/web/server/vue-cli/package-lock.json"

# Cleaning
echo "Cleaning previous builds..."
make clean
make "clean_${ENV_TYPE}"

# Creating new virtual environment
echo "Creating new virtual environment ($ENV_TYPE)..."
make "$ENV_TYPE"

# Again just in case
echo "Activating virtual environment and setting PATH..."
source "$REPO_ROOT/${ENV_TYPE}/bin/activate"
export PATH="$REPO_ROOT/build/CodeChecker/bin:$PATH"

echo "CodeChecker rebuild completed successfully!"
echo "You can now use CodeChecker commands."
