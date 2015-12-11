# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
result handlers for the clang static analyzer
"""

from codechecker_lib.analyzers import result_handler_store_db
from codechecker_lib.analyzers import result_handler_printout


class DBResHandler(result_handler_store_db.ResultHandlerStoreToDB):
    """
    stores the results to a database
    """

    def postprocess_result(self):
        """
        no postprocessing required for clang static analyzer
        """
        pass


class QCResHandler(result_handler_printout.ResultHandlerPrintOut):
    """
    prints the results to the standard output
    """

    def postprocess_result(self):
        """
        no postprocessing required for clang static analyzer
        """
        pass
