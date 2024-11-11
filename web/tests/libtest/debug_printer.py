# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper functions for tests.
"""


def print_run_results(run_results):
    """Print the run results stored in the database
       can be used for debugging test failures.  """

    print('---------------------------------------------------------')
    for run_res in run_results:
        print(('''Checkedfile: {0}\nCheckerid: {1}\nBugHash: {2}\n''' +
               '''--''').format(
            run_res.checkedFile,
            run_res.checkerId,
            run_res.bugHash))
    print('Got ' + str(len(run_results)) + ' reports')
    print('---------------------------------------------------------')
