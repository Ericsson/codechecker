# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Static analyzer configuration handler.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from abc import ABCMeta

from codechecker_common.logger import get_logger

LOG = get_logger('system')


class AnalyzerConfigHandler(object):
    """
    Handle the checker configurations and enabled disabled checkers lists.
    """
    __metaclass__ = ABCMeta

    def __init__(self):

        self.analyzer_binary = None
        self.compiler_resource_dir = ''
        self.analyzer_extra_arguments = []
        self.checker_config = ''
        self.report_hash = None

    def get_analyzer_checkers(self, environ):
        """
        Return the checkers available in the analyzer.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def initialize_checkers(self,
                            available_profiles,
                            package_root,
                            checkers,
                            checker_config=None,
                            cmdline_checkers=None,
                            enable_all=False):
        """
        Initializes the checker list for the specified config handler based on
        given checker profiles, commandline arguments and the
        analyzer-retrieved checker list.
        """
        raise NotImplementedError("Subclasses should implement this!")
