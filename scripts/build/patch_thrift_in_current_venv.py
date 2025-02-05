#!/usr/bin/env python3
"""
This script applies a patch to the Thrift library used in CodeChecker.

### Purpose:
The Thrift library (used by CodeChecker) includes deprecated Python files in
its implementation.
This script patches those files to ensure compatibility with Python 3.12.

### How It Works:
- It takes the CodeChecker root directory as an argument.
- It determines the Thrift installation path in the virtualenv.
- It applies a predefined Git patch to the relevant files using a relative path.

### When to Remove:
Remove this script when upgrading to a Thrift version that no longer relies on
deprecated Python files, eliminating the need for patching.
"""

import subprocess
import sys
import thrift
from pathlib import Path

THRIFT_PATCH_FILENAME = "thrift_patch_for_3.12.diff"

if len(sys.argv) < 2:
    print("Usage: python script.py <codechecker_root_dir>")
    sys.exit(1)

codechecker_root_dir = Path(sys.argv[1]).resolve()

if not codechecker_root_dir.is_dir():
    print(f"Error: {codechecker_root_dir} is not a valid directory")
    sys.exit(1)

script_dir = Path(__file__).resolve().parent
patch_file = script_dir / THRIFT_PATCH_FILENAME
thrift_lib_dir = Path(thrift.__path__[0]).resolve()

try:
    relative_thrift_lib_dir = thrift_lib_dir.relative_to(codechecker_root_dir)

    subprocess.run(
        ["git", "apply", "--directory", str(relative_thrift_lib_dir), str(patch_file)],
        cwd=codechecker_root_dir,
        check=True,
    )
    print(f"Patch applied successfully to {thrift_lib_dir}")
except ValueError:
    print(f"Error: {thrift_lib_dir} is not inside {codechecker_root_dir}")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"Error applying patch: {e}")
    sys.exit(1)
