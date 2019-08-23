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

import shlex
import sys
import subprocess

from collections import namedtuple, OrderedDict

from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.tidy')


ClangTidyChecker = namedtuple('ClangTidyChecker', ['enabled', 'description'])


def parse_checkers(tidy_output):
    """
    Parse clang tidy checkers list.
    Skip clang static analyzer checkers.
    Store them to checkers.
    """
    checkers = []

    for line in tidy_output.splitlines():
        line = line.strip()
        if not line or line.startswith('Enabled checks:') or \
           line.startswith('clang-analyzer-'):
            continue
        checkers.append((line, ''))

    return checkers


class ClangTidyConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Clang-tidy analyzer.
    """

    def __init__(self):
        super(ClangTidyConfigHandler, self).__init__()

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__checkers = OrderedDict()

    def get_analyzer_checkers(self, environ):
        """
        Return the list of the supported checkers.
        """
        analyzer_binary = self.analyzer_binary

        command = [analyzer_binary, "-list-checks", "-checks=*"]

        try:
            result = subprocess.check_output(command, env=environ,
                                             universal_newlines=True)
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    def add_checker(self, checker_name, enabled, description):
        """
        Add additional checker.
        Tuple of (checker_name, True or False).
        """
        self.__checkers[checker_name] = \
            ClangTidyChecker(enabled=enabled,
                             description=description)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        if checker_name.startswith("Wno-") or checker_name.startswith("W"):
            self.add_checker(checker_name, enabled, None)
            return

        for ch_name, _ in self.__checkers.items():
            if ch_name.startswith(checker_name) or \
               ch_name.endswith(checker_name):
                self.__checkers[ch_name] = \
                    self.__checkers[ch_name]._replace(enabled=enabled)

    def set_default_checkers(self, checker_config):
        """
        Set default enabled or disabled checkers, based on the config file.
        """
        if not checker_config:
            return

        # Check whether a default profile exists.
        profiles = checker_config.values()
        all_profile_names = (
            profile for check_list in profiles for profile in check_list)
        if 'default' not in all_profile_names:
            LOG.warning("No default profile found!")
        else:
            # Turn default checkers on.
            for checker_name, profile_list in checker_config.items():
                if 'default' in profile_list:
                    self.set_checker_enabled(checker_name)

    def set_user_defined_checkers(self, cmdline_checkers, checker_config,
                                  available_profiles, package_root):
        """
        Set user defined enabled or disabled checkers from the command line.
        """
        if not cmdline_checkers or not checker_config:
            return

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

                profile_checkers = (name for name, profile_list
                                    in checker_config.items()
                                    if profile_name in profile_list)
                for checker_name in profile_checkers:
                    self.set_checker_enabled(checker_name, enabled)

            # The identifier is a checker(-group) name.
            else:
                checker_name = identifier
                self.set_checker_enabled(checker_name, enabled)

    @property
    def checkers(self):
        """
        Return the checkers.
        """
        return self.__checkers

    def __gen_name_variations(self):
        """
        Generate all applicable name variations from the given checker list.
        """
        checker_names = (name for name in self.__checkers)
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
        # By default add and disable all checkers.
        for checker_name, description in checkers:
            self.add_checker(checker_name, False, description)

        # Set default enabled or disabled checkers, based on the config file.
        self.set_default_checkers(checker_config)

        # Enable all checkers.
        if enable_all:
            for checker_name, _ in checkers:
                self.set_checker_enabled(checker_name)

        # Set user defined enabled or disabled checkers from the command line.
        self.set_user_defined_checkers(cmdline_checkers, checker_config,
                                       available_profiles, package_root)
