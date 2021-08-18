# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Result handler for Clang Static Analyzer.
"""

import os

from codechecker_common.logger import get_logger
from codechecker_report_hash.hash import HashType, replace_report_hash

from ..result_handler_base import ResultHandler

LOG = get_logger('report')


class ResultHandlerClangSA(ResultHandler):
    """
    Use context free hash if enabled.
    """

    def postprocess_result(self):
        """
        Override the context sensitive issue hash in the plist files to
        context insensitive if it is enabled during analysis.
        """
        if os.path.exists(self.analyzer_result_file):
            if self.report_hash_type in ['context-free', 'context-free-v2']:
                replace_report_hash(
                    self.analyzer_result_file,
                    HashType.CONTEXT_FREE)
            elif self.report_hash_type == 'diagnostic-message':
                replace_report_hash(
                    self.analyzer_result_file,
                    HashType.DIAGNOSTIC_MESSAGE)
