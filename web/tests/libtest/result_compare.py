# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Result comparison helper functions for the tests.
"""


def compare_res_with_bug(run_res, bug):
    """
    Compare a run result with a bug to check if they are the same.
    """
    same = run_res.checkedFile.endswith(bug['file']) and \
        run_res.line == bug['line'] and \
        run_res.checkerId == bug['checker'] and \
        run_res.bugHash == bug['hash']
    return same


def find_all(run_results, bugs):
    """
    Returns a list of the not found bugs in it.
    """

    not_found = []
    for bug in bugs:
        found = False
        for run_res in run_results:
            found |= compare_res_with_bug(run_res, bug)
        if not found:
            not_found.append(bug)
    return not_found
