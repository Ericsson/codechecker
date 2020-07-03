# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Config handler for Clang Tidy analyzer.
"""


from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.tidy')


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith('W') or \
           checker_name.startswith('clang-diagnostic'):
            self.add_checker(checker_name)

        super(ClangTidyConfigHandler, self).set_checker_enabled(checker_name,
                                                                enabled)
