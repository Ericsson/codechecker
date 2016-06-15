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
        print('''Bugfile: {0} \nStartline: {1} Endline: {2}\nStartcol: {3} Endcol: {4} \nMsg: {5} \nCheckedfile: {6}\nCheckerid: {7}\nReportid: {8}\nSuppressed: {9}\n--'''.format(
                                            run_res.lastBugPosition.filePath,
                                            run_res.lastBugPosition.startLine,
                                            run_res.lastBugPosition.endLine,
                                            run_res.lastBugPosition.startCol,
                                            run_res.lastBugPosition.endCol,
                                            run_res.lastBugPosition.msg,
                                            run_res.checkedFile,
                                            run_res.checkerId,
                                            run_res.reportId,
                                            run_res.suppressed))
    print('Got ' + str(len(run_results)) + ' reports')
    print('---------------------------------------------------------')
