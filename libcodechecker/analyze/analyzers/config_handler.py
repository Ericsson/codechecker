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

from abc import ABCMeta, abstractmethod
import collections
import os

from libcodechecker.logger import get_logger

LOG = get_logger('system')


class AnalyzerConfigHandler(object):
    """
    Handle the checker configurations and enabled disabled checkers lists.
    """
    __metaclass__ = ABCMeta

    def __init__(self):

        self.analyzer_binary = None
        self.analyzer_plugins_dir = None
        self.compiler_resource_dir = ''
        self.analyzer_extra_arguments = ''
        self.checker_config = ''

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__available_checkers = collections.OrderedDict()

    @property
    def analyzer_plugins(self):
        """
        Full path of the analyzer plugins.
        """
        plugin_dir = self.analyzer_plugins_dir
        analyzer_plugins = [os.path.join(plugin_dir, f)
                            for f in os.listdir(plugin_dir)
                            if os.path.isfile(os.path.join(plugin_dir, f))]
        return analyzer_plugins

    @abstractmethod
    def get_checker_configs(self):
        """
        Return a list of (checker_name, key, key_valye) tuples.
        """
        pass

    def add_checker(self, checker_name, enabled, description):
        """
        Add additional checker.
        Tuple of (checker_name, True or False).
        """
        self.__available_checkers[checker_name] = (enabled, description)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        for ch_name, values in self.__available_checkers.items():
            if ch_name.startswith(checker_name) or \
               ch_name.endswith(checker_name):
                _, description = values
                self.__available_checkers[ch_name] = (enabled, description)

    def checks(self):
        """
        Return the checkers.
        """
        return self.__available_checkers
