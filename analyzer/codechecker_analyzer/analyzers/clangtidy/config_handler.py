# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Config handler for Clang Tidy analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.tidy')


def is_warning(checker_name):
    """
    Predicate function used to determine whether the checker name signifies a
    warning.
    """
    return checker_name.startswith("W")


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer. Compiler warnings are
    handled as checkers.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

    def initialize_checkers(self,
                            available_profiles,
                            package_root,
                            checkers,
                            checker_config=None,
                            cmdline_checkers=None,
                            enable_all=False):
        """
        Extend the available checkers with warnings.
        """

        if cmdline_checkers is None:
            cmdline_checkers = []

        for checker_name, _ in cmdline_checkers:
            if is_warning(checker_name):
                self.checker_handler().register_checker(checker_name)

        super(ClangTidyConfigHandler, self).initialize_checkers(
                available_profiles,
                package_root,
                checkers,
                checker_config,
                cmdline_checkers,
                enable_all)
