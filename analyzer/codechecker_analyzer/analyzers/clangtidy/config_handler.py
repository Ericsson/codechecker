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
                             get_compiler_warning_name_and_type


def is_compiler_warning(checker_name):
    name, _ = get_compiler_warning_name_and_type(checker_name)
    return name is not None


LOG = get_logger('analyzer.tidy')


class ClangTidyConfigHandler(AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def add_checker(self, checker_name, description='',
                    state=CheckerState.DISABLED):
        """
        Add additional checker if the 'take-config-from-directory'
        analyzer configuration option is not set.
        """
        if self.analyzer_config and \
           self.analyzer_config.get('take-config-from-directory') == 'true':
            if is_compiler_warning(checker_name):
                return

        super().add_checker(checker_name, description, state)
