#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import logging


def print_run_results(run_results):
    """Print the run results stored in the database
       can be used for debugging test failures.  """

    for run_res in run_results:
        logging.debug('{0:15s}  {1}'.format(run_res.checkedFile,
                                            run_res.checkerId))
        logging.debug('{0:15d}  {1}'.format(run_res.reportId,
                                            run_res.suppressed))
        logging.debug(run_res.lastBugPosition)
        logging.debug('-------------------------------------------------')
    logging.debug('got ' + str(len(run_results)) + ' reports')
