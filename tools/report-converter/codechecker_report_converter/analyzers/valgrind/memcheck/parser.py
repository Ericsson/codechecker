# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

from ..parser import ValgrindParser


class Parser(ValgrindParser):
    """Parser for Valgrind Memcheck outputs."""

    checker_name_prefix = "Memcheck"
