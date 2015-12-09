# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Module to construct the proper result handler
"""

from codechecker_lib import logger

from codechecker_lib.analyzers import analyzer_types
from codechecker_lib.analyzers import result_handler_clangsa
from codechecker_lib.analyzers import result_handler_clang_tidy

LOG = logger.get_new_logger('RESULT_HANDLER')

def construct_result_handler(args,
                             buildaction,
                             run_id,
                             report_output,
                             severity_map,
                             skiplist_handler,
                             store_to_db=False):
    """
    construct a result handler
    """

    if store_to_db:
        # create a result handler which stores the results into a database
        if buildaction.analyzer_type == analyzer_types.CLANG_SA:
            csa_res_handler = result_handler_clangsa.DBResHandler(buildaction,
                                                                  report_output,
                                                                  run_id)

            csa_res_handler.severity_map = severity_map
            csa_res_handler.skiplist_handler = skiplist_handler
            return csa_res_handler

        elif buildaction.analyzer_type == analyzer_types.CLANG_TIDY:
            # TODO clang tidy db store result handler
            return None

        else:
            LOG.error('Not supported analyzer type')
            return None
    else:
        if buildaction.analyzer_type == analyzer_types.CLANG_SA:
            csa_res_handler = result_handler_clangsa.QCResHandler(buildaction,
                                                                  report_output)
            csa_res_handler.print_steps = args.print_steps
            return csa_res_handler

        elif buildaction.analyzer_type == analyzer_types.CLANG_TIDY:
            # TODO create non database tidy result handlers
            return None
        else:
            LOG.error('Not supported analyzer type')
            return None
