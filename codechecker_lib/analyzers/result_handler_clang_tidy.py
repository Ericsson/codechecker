# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import ntpath

import shared

from codechecker_lib import logger
from codechecker_lib.analyzers import result_handler_base

LOG = logger.get_new_logger('CLANG_TIDY_RESULT_HANDLER')


class CTDBResHandler(result_handler_base.ResultHandler):
    """
    Clang tidy results database handler
    """

    def __init__(self, buildaction, workspace, run_id):
        super(CTDBResHandler, self).__init__(buildaction, workspace)
        self.__connection = connection
        self.__workspace = workspace
        self.__run_id = run_id

    def postprocess_result(self):
        pass

    def handle_results(self):
        pass


class CTQCResHandler(result_handler_base.ResultHandler):
    """
    """

    def postprocess_result(self, result):
        pass

    def handle_results(self):
        pass
