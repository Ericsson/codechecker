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
import collections
import os
import platform
import sys

from codechecker_common.logger import get_logger

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
        self.analyzer_extra_arguments = []
        self.checker_config = ''
        self.report_hash = None

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
        if not os.path.exists(plugin_dir):
            return []

        analyzer_plugins = [os.path.join(plugin_dir, f)
                            for f in os.listdir(plugin_dir)
                            if os.path.isfile(os.path.join(plugin_dir, f))
                            and f.endswith(".so")]
        return analyzer_plugins

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

    def __gen_name_variations(self):
        """
        Generate all applicable name variations from the given checker list.
        """
        checker_names = (name for name in self.__available_checkers)
        reserved_names = []

        for name in checker_names:
            delim = '.' if '.' in name else '-'
            parts = name.split(delim)
            # Creates a list of variations from a checker name, e.g.
            # ['security', 'security.insecureAPI', 'security.insecureAPI.gets']
            # from 'security.insecureAPI.gets' or
            # ['misc', 'misc-dangling', 'misc-dangling-handle']
            # from 'misc-dangling-handle'.
            v = [delim.join(parts[:(i + 1)]) for i in range(len(parts))]
            reserved_names += v

        return reserved_names

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

        # By default disable all checkers.
        for checker_name, description in checkers:
            self.add_checker(checker_name, False, description)

        # Set default enabled or disabled checkers, based on the config file.
        if checker_config:
            # Check whether a default profile exists.
            if 'default' not in checker_config:
                LOG.warning("No default profile found!")
            else:
                # Turn default checkers on.
                for checker in checker_config['default']:
                    self.set_checker_enabled(checker, True)

        # If enable_all is given, almost all checkers should be enabled.
        if enable_all:
            for checker_name, enabled in checkers:
                if not checker_name.startswith("alpha.") and \
                        not checker_name.startswith("debug.") and \
                        not checker_name.startswith("osx."):
                    # There are a few exceptions, though, which still need to
                    # be manually enabled by the user: alpha and debug.
                    self.set_checker_enabled(checker_name)

                if checker_name.startswith("osx.") and \
                        platform.system() == 'Darwin':
                    # OSX checkers are only enable-all'd if we are on OSX.
                    self.set_checker_enabled(checker_name)

        # Set user defined enabled or disabled checkers from the command line.
        if cmdline_checkers:

            # Construct a list of reserved checker names.
            # (It is used to check if a profile name is valid.)
            reserved_names = self.__gen_name_variations()

            for identifier, enabled in cmdline_checkers:

                # The identifier is a profile name.
                if identifier in available_profiles:
                    profile_name = identifier

                    if profile_name == "list":
                        LOG.error("'list' is a reserved profile keyword. ")
                        LOG.error("Please choose another profile name in "
                                  "'%s'/config/config.json and rebuild.",
                                  package_root)
                        sys.exit(1)

                    if profile_name in reserved_names:
                        LOG.warning("Profile name '%s' conflicts with a "
                                    "checker(-group) name.", profile_name)

                    # Enable or disable all checkers belonging to the profile.
                    for checker in checker_config[profile_name]:
                        self.set_checker_enabled(checker, enabled)

                # The identifier is a checker(-group) name.
                else:
                    checker_name = identifier
                    self.set_checker_enabled(checker_name, enabled)
