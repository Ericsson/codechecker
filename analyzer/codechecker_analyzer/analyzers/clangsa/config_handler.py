# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Clang Static analyzer configuration handler.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import platform
import re
import sys
import subprocess

from collections import namedtuple, OrderedDict

from codechecker_common.logger import get_logger
from .ctu_autodetection import CTUAutodetection

from . import clang_options
from . import version

from .. import config_handler

LOG = get_logger('analyzer.clangsa')


ClangSAChecker = namedtuple('ClangSAChecker', ['enabled', 'description'])


def parse_checkers(clangsa_output):
    """ Parse clang static analyzer checkers list output.

    The given clangsa otput contains checker name and description pairs, which
    however can extend over multiple lines. This is why we need stateful
    parsing when iterating over lines.

    Return a list of (checker name, description) tuples.
    """
    # Checker name and description in one line.
    checker_entry_pattern = re.compile(
        r'^\s\s(?P<checker_name>\S*)\s*(?P<description>.*)')

    indented_pattern = re.compile(r'^\s\s\S')

    checkers_list = []
    checker_name = None
    for line in clangsa_output.splitlines():
        if line.startswith('CHECKERS:') or line == '':
            continue
        elif checker_name and not indented_pattern.match(line):
            # Collect description for the checker name.
            checkers_list.append((checker_name, line.strip()))
            checker_name = None
        elif re.match(r'^\s\s\S+$', line.rstrip()):
            # Only checker name is in the line.
            checker_name = line.strip()
        else:
            # Checker name and description is in one line.
            match = checker_entry_pattern.match(line.rstrip())
            if match:
                current = match.groupdict()
                checkers_list.append((current['checker_name'],
                                      current['description']))
    return checkers_list


class ClangSAConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for the clang static analyzer.
    """

    def __init__(self, environ):
        super(ClangSAConfigHandler, self).__init__()
        self.__checker_configs = []
        self.ctu_dir = ''
        self.log_file = ''
        self.path_env_extra = ''
        self.ld_lib_path_extra = ''
        self.enable_z3 = False
        self.enable_z3_refutation = False
        self.environ = environ
        self.analyzer_plugins_dir = None

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__checkers = OrderedDict()

    @property
    def analyzer_plugins(self):
        """
        Full path of the analyzer plugins.
        """
        plugin_dir = self.analyzer_plugins_dir
        if not os.path.exists(plugin_dir):
            return []

        return [os.path.join(plugin_dir, f)
                for f in os.listdir(plugin_dir)
                if os.path.isfile(os.path.join(plugin_dir, f)) and
                f.endswith(".so")]

    def get_analyzer_checkers(self, environ):
        """
        Return the list of the supported checkers.
        """
        analyzer_binary = self.analyzer_binary

        try:
            analyzer_version = subprocess.check_output(
                [analyzer_binary, '--version'],
                env=environ)

        except subprocess.CalledProcessError as cerr:
            LOG.error('Failed to get and parse clang version: %s',
                      analyzer_binary)
            LOG.error(cerr)
            return []

        version_parser = version.ClangVersionInfoParser()
        version_info = version_parser.parse(analyzer_version)

        command = [analyzer_binary, "-cc1"]

        checkers_list_args = clang_options.get_analyzer_checkers_cmd(
            version_info,
            environ,
            self.analyzer_plugins,
            alpha=True)
        command.extend(checkers_list_args)

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
        self.__checkers[checker_name] = ClangSAChecker(enabled=enabled,
                                                       description=description)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
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

    def add_checker_config(self, config):
        """
        Add a (checker_name, key, value) tuple to the list.
        """
        self.__checker_configs.append(config)

    @property
    def ctu_capability(self):
        return CTUAutodetection(self.analyzer_binary, self.environ)

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

        # If enable_all is given, almost all checkers should be enabled.
        if enable_all:
            for checker_name, _ in checkers:
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
        self.set_user_defined_checkers(cmdline_checkers, checker_config,
                                       available_profiles, package_root)
