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

from ..config_handler import AnalyzerConfigHandler, CheckerState, \
                             get_compiler_warning_name

LOG = get_logger('analyzer.tidy')


class ClangTidyConfigHandler(AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def add_checker(self, checker_name, description='',
                    state=CheckerState.default):
        """
        Add additional checker if the 'take-config-from-directory'
        analyzer configuration option is not set.
        """
        if self.analyzer_config and \
           self.analyzer_config.get('take-config-from-directory') == 'true':
            if get_compiler_warning_name(checker_name) is None:
                return

        super(ClangTidyConfigHandler, self).add_checker(checker_name,
                                                        description, state)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith('W') or \
           checker_name.startswith('clang-diagnostic'):
            self.add_checker(checker_name)

        super(ClangTidyConfigHandler, self).set_checker_enabled(checker_name,
                                                                enabled)
