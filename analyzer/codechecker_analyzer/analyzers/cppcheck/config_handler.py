# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Config handler for Cppcheck analyzer.
"""
from .. import config_handler
from ..config_handler import CheckerState


class CppcheckConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Cppcheck analyzer.
    """
    def initialize_checkers(self,
                            analyzer_context,
                            checkers,
                            cmdline_enable=None,
                            enable_all=False):
        if not cmdline_enable:
            cmdline_enable = list()
        """
        Set all the default checkers to disabled. This will ensure that
        --enable=all will not run with all the possible checkers
        """
        super().initialize_checkers(
                            analyzer_context,
                            checkers,
                            cmdline_enable,
                            enable_all)

        # Set all the checkers with default CheckerState checkers to
        # disabled. This will ensure that --enable=all will not run with
        # all the possible checkers. All the checkers that are in the default
        # profile (or configured othewise, eg.: from the cli) should be
        # already enabled at this point.
        for checker_name, data in self.checks().items():
            if data[0] == CheckerState.default:
                self.set_checker_enabled(checker_name, enabled=False)
