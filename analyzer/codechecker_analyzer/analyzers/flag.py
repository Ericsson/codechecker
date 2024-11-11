# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


def has_flag(flag, cmd):
    """Return true if a cmd contains a flag or false if not."""
    return bool(next((x for x in cmd if x.startswith(flag)), False))


def prepend_all(flag, params):
    """
    Returns a list where all elements of "params" is prepended with the given
    flag. For example in case "flag" is -f and "params" is ['a', 'b', 'c'] the
    result is ['-f', 'a', '-f', 'b', '-f', 'c'].
    """
    result = []
    for param in params:
        result.append(flag)
        result.append(param)
    return result
