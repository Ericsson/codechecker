# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Static analyzer configuration handler.
"""


from abc import ABCMeta
import collections
import platform
import re
import sys

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def find_first(predicate, iterable, default=None):
    """
    Finds the first occurence matching predicate insided an iterable.
    Returns default if no items match.
    """
    return next(iter(filter(predicate, iterable)), default)


# The baseline handling of checks in every analyzer is to let the analysis
# engine decide which checks are worthwhile run. Checks handled this way
# (implicitly by the analyzer) are considered to have a CheckerState of
# default. If the check however appears in profiles, and such a profile is
# enabled explicitly on the command-line or implicitly as in case of the
# default profile, then they are considered to have a CheckerState of enabled.
# Likewise for individually enabled checks. If a check is however explicitly
# disabled on the command-line, or belongs to a profile explicitly disabled
# on the command-line, then it is considered to have a CheckerState of
# disabled.
# TODO: Use enum when upgrading to Python3.
class CheckerState(object):
    default = 0
    disabled = 1
    enabled = 2
    STATES = {'default', 'disabled', 'enabled'}
    NAMES = {0: 'default', 1: 'disabled', 2: 'enabled'}


class AnalyzerConfigHandler(object, metaclass=ABCMeta):
    """
    Handle the checker configurations and enabled disabled checkers lists.
    """

    def __init__(self):

        self.analyzer_binary = None
        self.analyzer_plugins_dir = None
        self.analyzer_extra_arguments = []
        self.checker_config = ''
        self.report_hash = None
        self.version_info = None

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__available_checkers = collections.OrderedDict()

    @property
    def analyzer_plugins(self):
        """ Full path of the analyzer plugins. """
        return []

    def get_version(self, env=None):
        """ Get analyzer version information. """
        return self.version_info.cmd_output

    def __get_matching_checker_config(self, profile_configs):
        """
        Return the profile to checkers mapping for the current analyzer
        version.
        """
        analyzer_version = self.version_info.cmd_output
        matching_config = find_first(
            lambda x: re.search(x["version_regex"], analyzer_version),
            profile_configs
        )

        return matching_config['profiles'] if matching_config else None

    def add_checker(self, checker_name, description='',
                    state=CheckerState.default):
        """
        Add additional checker. If no state argument is given, the actual usage
        of the checker is handled by the analyzer.
        """
        self.__available_checkers[checker_name] = (state, description)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Explicitly handle checker state, keep description if already set.
        """
        for ch_name, values in self.__available_checkers.items():
            if ch_name.startswith(checker_name) or \
               ch_name.endswith(checker_name):
                _, description = values
                state = CheckerState.enabled if enabled \
                    else CheckerState.disabled
                self.__available_checkers[ch_name] = (state, description)

    def any_checker_enabled(self):
        """ Returns true if at least one checker is enabled.  """

        for _, checker_state in self.__available_checkers.items():
            if checker_state[0] == CheckerState.enabled:
                return True
        return False

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
                            builtin_checker_profile_cfg=None,
                            cmdline_checkers=None,
                            enable_all=False):
        """Initializes which checkers should be enabled during the analysis.

        Enables checkers based on the configuration from the config files
        checker profiles or user config from the command line.
        Calls sys.exit(1) in case of the 'list' profile name was set.

        Args:
            available_profiles (Dict[str, str]): profile name and description
            package_root (str): root path to the CodeChecker package
            checkers (Sequence[Tuple[str, str]): (checker, description) list
            builtin_checker_profile_cfg (Sequence[Dict]):
                list of the available checker configs for an analyzer
                (for every analyzer version)
            cmdline_checkers (Sequence[Tuple[str, bool]): list of checker name
                and if the checker was enabled in the command line
            enable_all (bool): all the checker should be enabled

        Returns:
             bool: False if there was some problem
                   during initialization.
        """
        no_init_problem = True

        checker_config = None
        # Filter out the profiles which should be valid for the given version
        if builtin_checker_profile_cfg:
            checker_config = \
                self.__get_matching_checker_config(builtin_checker_profile_cfg)

            if checker_config is None:
                LOG.warning("No matching checker profile was found "
                            "for the configured analyzer version.\n"
                            "Please check the profile configuration in "
                            "<package-root>/config/config.json")
                no_init_problem = False

        # Add all checkers marked as default. This means the analyzer should
        # manage whether it is enabled or disabled.
        for checker_name, description in checkers:
            self.add_checker(checker_name, description)

        # Set default enabled or disabled checkers, based on the config file.
        if checker_config:
            # Check whether a default profile exists.
            if 'default' not in checker_config:
                LOG.warning("No default profile found!")
                no_init_problem = False
            else:
                # Turn default checkers on.
                for checker in checker_config['default']:
                    self.set_checker_enabled(checker)

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

                    if checker_config:
                        # Enable or disable all checkers
                        # belonging to the profile.
                        for checker in checker_config[profile_name]:
                            self.set_checker_enabled(checker, enabled)

                # The identifier is a checker(-group) name.
                else:
                    checker_name = identifier
                    self.set_checker_enabled(checker_name, enabled)

        return no_init_problem
