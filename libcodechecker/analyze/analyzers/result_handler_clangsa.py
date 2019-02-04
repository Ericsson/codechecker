# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Result handler for Clang Static Analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from libcodechecker import report
from libcodechecker.analyze.analyzers.result_handler_base \
    import ResultHandler
from libcodechecker.logger import get_logger

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
        if self.report_hash_type == 'context-free':
            report.use_context_free_hashes(self.analyzer_result_file)
