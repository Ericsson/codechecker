#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Entry point for the $COMMAND$ command.
"""


from importlib.util import spec_from_file_location
import os

THIS_PATH = os.path.dirname(os.path.abspath(__file__))
CC = os.path.join(THIS_PATH, "CodeChecker")

# Load CodeChecker from the current folder (the wrapper script (without .py))
CodeChecker = spec_from_file_location('CodeChecker', CC).loader.load_module()

# Execute CC's main script with the current subcommand.
CodeChecker.main("$COMMAND$")
