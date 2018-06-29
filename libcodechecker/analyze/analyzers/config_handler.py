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

        self.__analyzer_binary = None
        self.__analyzer_plugins_dir = None
        self.__compiler_resource_dir = ''
        self.__analyzer_extra_arguments = ''

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__available_checkers = collections.OrderedDict()

    @property
    def analyzer_plugins_dir(self):
        """
        Get directory from where shared objects with checkers should be loaded.
        """
        return self.__analyzer_plugins_dir

    @analyzer_plugins_dir.setter
    def analyzer_plugins_dir(self, value):
        """
        Set the directory where shared objects with checkers can be found.
        """
        self.__analyzer_plugins_dir = value

    @property
    def analyzer_plugins(self):
        """
        Full path of the analyzer plugins.
        """
        plugin_dir = self.__analyzer_plugins_dir
        analyzer_plugins = [os.path.join(plugin_dir, f)
                            for f in os.listdir(plugin_dir)
                            if os.path.isfile(os.path.join(plugin_dir, f))]
        return analyzer_plugins

    @property
    def analyzer_binary(self):
        return self.__analyzer_binary

    @analyzer_binary.setter
    def analyzer_binary(self, value):
        self.__analyzer_binary = value

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

    def enable_checker(self, checker_name, description=None):
        """
        Enable checker, keep description if already set.
        """
        for ch_name, values in self.__available_checkers.items():
            if ch_name.startswith(checker_name):
                _, description = values
                self.__available_checkers[ch_name] = (True, description)
            # FIXME use regex to match checker names.
            if ch_name.endswith(checker_name):
                _, description = values
                self.__available_checkers[ch_name] = (True, description)

    def disable_checker(self, checker_name, description=None):
        """
        Disable checker, keep description if already set.
        """
        for ch_name, values in self.__available_checkers.items():
            if ch_name.startswith(checker_name):
                _, description = values
                self.__available_checkers[ch_name] = (False, description)

    def checks(self):
        """
        Return the checkers.
        """
        return self.__available_checkers

    @property
    def compiler_resource_dir(self):
        """
        Get compiler resource directories.
        """
        return self.__compiler_resource_dir

    @compiler_resource_dir.setter
    def compiler_resource_dir(self, resource_dir):
        """
        Set compiler resource directories.
        """
        self.__compiler_resource_dir = resource_dir

    @property
    def analyzer_extra_arguments(self):
        """
        Extra arguments forwarded to the analyzer without modification.
        """
        return self.__analyzer_extra_arguments

    @analyzer_extra_arguments.setter
    def analyzer_extra_arguments(self, value):
        """
        Extra arguments forwarded to the analyzer without modification.
        """
        self.__analyzer_extra_arguments = value
