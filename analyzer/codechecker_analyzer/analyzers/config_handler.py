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
from enum import Enum
from operator import itemgetter
import collections
import platform
import subprocess
import sys

from codechecker_common.logger import get_logger

LOG = get_logger('system')


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
class CheckerState(Enum):
    default = 0
    disabled = 1
    enabled = 2


class AnalyzerConfigHandler(metaclass=ABCMeta):
    """
    Handle the checker configurations and enabled disabled checkers lists.
    """

    def __init__(self):

        self.analyzer_binary = None
        self.analyzer_plugins_dir = None
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
        """ Full path of the analyzer plugins. """
        return []

    def get_version(self, env=None):
        """ Get analyzer version information. """
        version = [self.analyzer_binary, '--version']
        try:
            output = subprocess.check_output(version,
                                             env=env,
                                             universal_newlines=True,
                                             encoding="utf-8",
                                             errors="ignore")
            return output
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(version))
            LOG.warning(oerr)

        return None

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
                            analyzer_context,
                            checkers,
                            cmdline_enable=[],
                            enable_all=False):
        """
        Add checkers and set their "enabled/disabled" status. The following
        inputs are considered in this order:
        - First the default state is taken based on the analyzer tool.
        - Members of "default" profile are enabled.
        - In case of "--enable-all" every checker is enabled except for "alpha"
          and "debug" checker groups. "osx" checker group is also not included
          unless the target platform is Darwin.
        - Command line "--enable/--disable" flags.
          - Their arguments may start with "profile:" or "guideline:" prefix
            which makes the choice explicit.
          - Without prefix it means a profile name, a guideline name or a
            checker group/name in this priority order.

        analyzer_context -- Context object.
        checkers -- [(checker name, description), ...] Checkers to add with
                    their description.
        cmdline_enable -- [(argument, enabled), ...] Arguments of
                          "--enable/--disable" flags and a boolean value
                          whether it is after "--enable" or not.
        enable_all -- Boolean value whether "--enable-all" is given.
        """

        profile_map = analyzer_context.profile_map
        guideline_map = analyzer_context.guideline_map

        if 'profile:list' in map(itemgetter(0), cmdline_enable):
            LOG.error("'list' is a reserved profile keyword. ")
            LOG.error("Please choose another profile name in "
                      "%s/config/checker_profile_map.json and rebuild.",
                      analyzer_context.data_files_dir_path)
            sys.exit(1)

        if 'guideline:list' in map(itemgetter(0), cmdline_enable):
            LOG.error("'list' is a reserved guideline keyword. ")
            LOG.error("Please choose another guideline name in "
                      "%s/config/checker_guideline_map.json and rebuild.",
                      analyzer_context.data_files_dir_path)
            sys.exit(1)

        # Add all checkers marked as default. This means the analyzer should
        # manage whether it is enabled or disabled.
        for checker_name, description in checkers:
            self.add_checker(checker_name, description)

        # Set default enabled or disabled checkers, based on the config file.
        default_profile_checkers = profile_map.by_profile('default')
        if not default_profile_checkers:
            # Check whether a default profile exists.
            LOG.warning("No default profile found!")
        else:
            # Turn default checkers on.
            for checker in default_profile_checkers:
                self.set_checker_enabled(checker)

        # If enable_all is given, almost all checkers should be enabled.
        disabled_groups = ["alpha.", "debug.", "osx.", "abseil-", "android-",
                           "darwin-", "objc-", "cppcoreguidelines-",
                           "fuchsia.", "fuchsia-", "hicpp-", "llvm-",
                           "llvmlibc-", "google-", "zircon-"]
        if enable_all:
            for checker_name, _ in checkers:
                if not any(checker_name.startswith(d_grp) for d_grp in
                           disabled_groups):

                    # There are a few exceptions, though, which still need to
                    # be manually enabled by the user: alpha and debug.
                    self.set_checker_enabled(checker_name)

                if checker_name.startswith("osx.") and \
                        platform.system() == 'Darwin':
                    # OSX checkers are only enable-all'd if we are on OSX.
                    self.set_checker_enabled(checker_name)

        # Set user defined enabled or disabled checkers from the command line.

        # Construct a list of reserved checker names.
        # (It is used to check if a profile name is valid.)
        reserved_names = self.__gen_name_variations()

        for identifier, enabled in cmdline_enable:
            if identifier.startswith('profile:'):
                profile_name = identifier[len('profile:'):]
                if profile_name not in profile_map.available_profiles():
                    LOG.error('No such profile: %s', profile_name)
                    sys.exit(1)
                for checker in profile_map.by_profile(profile_name):
                    self.set_checker_enabled(checker, enabled)
            if identifier.startswith('guideline:'):
                guideline_name = identifier[len('guideline:'):]
                if guideline_name not in guideline_map.available_guidelines():
                    LOG.error('No such guideline: %s', guideline_name)
                    sys.exit(1)
                for checker in guideline_map.by_guideline(guideline_name):
                    self.set_checker_enabled(checker, enabled)
            elif identifier in profile_map.available_profiles():
                if identifier in reserved_names:
                    LOG.warning("Profile name '%s' conflicts with a "
                                "checker(-group) name.", identifier)
                for checker in profile_map.by_profile(identifier):
                    self.set_checker_enabled(checker, enabled)
            elif identifier in guideline_map.available_guidelines():
                if identifier in reserved_names:
                    LOG.warning("Guideline name '%s' conflicts with a "
                                "checker(-group) name.", identifier)
                for checker in guideline_map.by_guideline(identifier):
                    self.set_checker_enabled(checker, enabled)
            else:
                self.set_checker_enabled(identifier, enabled)
