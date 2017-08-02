# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------


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
