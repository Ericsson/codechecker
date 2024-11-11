# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Shim to inject a CodeChecker package into the current interpreter."""
import os
import pathlib
import sys
from typing import Optional

from .util import find_if


def codechecker_src_root() -> Optional[pathlib.Path]:
    """
    Returns the root directory for the CodeChecker source package parent to
    the label tooling.
    """
    try:
        this_file = pathlib.Path(__file__).resolve(strict=True)
        labels_idx = find_if(this_file.parents,
                             lambda p: p.stem == "labels")
        if not labels_idx:
            return None

        if this_file.parents[labels_idx + 1].stem == "scripts":
            return this_file.parents[labels_idx + 2]

        return None
    except Exception:
        import traceback
        traceback.print_exc()

        return None


def inject_codechecker_to_interpreter():
    """
    Adds the built CodeChecker package relative to the root of the working
    copy to the current interpreter to be able to load code from the main
    distribution.
    """
    src_root = codechecker_src_root()
    if not src_root:
        raise NotADirectoryError("Can not find CodeChecker source root!")

    codechecker_package = src_root / "build" / "CodeChecker"
    python_package_dir = codechecker_package / "lib" / "python3"
    if python_package_dir not in sys.path:
        # Leave position 0, the current directory of the interpreter, intact.
        sys.path.insert(1, str(python_package_dir))

    # Make sure the injected environment has access to CodeChecker's logging
    # configuration. We do not use it directly in this tool, but packages
    # imported from "over there" can end up having issues without this.
    os.environ.update({"CC_DATA_FILES_DIR": str(codechecker_package)})


inject_codechecker_to_interpreter()
