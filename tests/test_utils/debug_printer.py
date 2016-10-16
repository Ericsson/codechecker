#
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
        print(('''Bugfile: {0} \nStartline: {1} \nCheckedfile: {2}\n''' +
               '''Checkerid: {3}\nBugHash: {4}\nSuppressed: {5}\n--''').format(
                  run_res.lastBugPosition.filePath,
                  run_res.lastBugPosition.startLine,
                  run_res.checkedFile,
                  run_res.checkerId,
                  run_res.bugHash,
                  run_res.suppressed))
    print('Got ' + str(len(run_results)) + ' reports')
    print('---------------------------------------------------------')
