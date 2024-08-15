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
import collections
import platform
import re

from codechecker_analyzer import analyzer_context
from codechecker_common.logger import get_logger

LOG = get_logger('system')


# If the check appears in profiles, and such a profile is enabled explicitly on
# the command-line or implicitly as in case of the default profile, then they
# are considered to have a CheckerState of enabled. Likewise for individually
# enabled checks. If a check is however explicitly disabled on the
# command-line, or belongs to a profile explicitly disabled on the
# command-line, then it is considered to have a CheckerState of disabled.
class CheckerState(Enum):
    DISABLED = 1
    ENABLED = 2


class CheckerType(Enum):
    """
    Checker type.
    """
    ANALYZER = 0  # A checker which is not a compiler warning.
    COMPILER = 1  # A checker which specified as "-W<name>" or "-Wno-<name>".


def get_compiler_warning_name_and_type(checker_name):
    """
    Removes 'W' or 'Wno' from the compiler warning name, if this is a
    compiler warning and returns the name and CheckerType.compiler.
    If it is a clang-diagnostic-<name> warning then it returns the name
    and CheckerType.analyzer.
    Otherwise returns None and CheckerType.analyzer.
    """
    # Checker name is a compiler warning.
    if checker_name.startswith('W'):
        name = checker_name[4:] if \
            checker_name.startswith('Wno-') else checker_name[1:]
        return name, CheckerType.COMPILER
    elif checker_name.startswith('clang-diagnostic-'):
        return checker_name[17:], CheckerType.ANALYZER
    else:
        return None, CheckerType.ANALYZER


class AnalyzerConfigHandler(metaclass=ABCMeta):
    """
    Handle the checker configurations and enabled disabled checkers lists.
    """

    def __init__(self):

        self.analyzer_extra_arguments = []
        self.checker_config = ''
        self.analyzer_config = None
        self.report_hash = None
        self.enable_all = None

        # The key is the checker name, the value is a tuple of CheckerState and
        # checker description.
        self.__available_checkers = collections.OrderedDict()

    def add_checker(self, checker_name, description='',
                    state=CheckerState.DISABLED):
        """
        Add a checker to the available checkers' list.
        """
        self.__available_checkers[checker_name] = (state, description)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Explicitly handle checker state, keep description if already set.
        """
        changed_states = []
        regex = "^" + re.escape(str(checker_name)) + "\\b.*$"

        for ch_name, values in self.__available_checkers.items():
            if re.match(regex, ch_name):
                _, description = values
                state = CheckerState.ENABLED if enabled \
                    else CheckerState.DISABLED
                changed_states.append((ch_name, state, description))

        # Enabled/disable checkers are stored in an ordered dict. When a
        # checker group (e.g. clang-diagnostic) is disabled then all checkers
        # in this group are added to this list in order, including
        # clang-diagnostic itself at the end. Enabling a specific member of a
        # disabled group (e.g. clang-diagnostic-vla) resets the status at an
        # earlier position than the group name, so due to its order the group
        # disable will be stronger. The solution is removing the given checker
        # and inserting it back to the end.
        for ch_name, state, description in changed_states:
            del self.__available_checkers[ch_name]
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
                            checkers,
                            cmdline_enable=None,
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

        checkers -- [(checker name, description), ...] Checkers to add with
                    their description.
        cmdline_enable -- [(argument, enabled), ...] Arguments of
                          "--enable/--disable" flags and a boolean value
                          whether it is after "--enable" or not.
        enable_all -- Boolean value whether "--enable-all" is given.
        """

        if cmdline_enable is None:
            cmdline_enable = []

        checker_labels = analyzer_context.get_context().checker_labels

        # Add all checkers marked as disabled.
        for checker_name, description in checkers:
            self.add_checker(checker_name, description)

        # Set default enabled or disabled checkers, based on the config file.
        default_profile_checkers = \
            checker_labels.checkers_by_labels(['profile:default'])
        if not default_profile_checkers:
            # Check whether a default profile exists.
            LOG.warning("No default profile found!")
        else:
            # Turn default checkers on.
            for checker in default_profile_checkers:
                self.set_checker_enabled(checker)

        self.enable_all = enable_all
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
        profiles = checker_labels.get_description('profile')
        guidelines = checker_labels.occurring_values('guideline')

        for identifier, enabled in cmdline_enable:
            if ':' in identifier:
                for checker in checker_labels.checkers_by_labels([identifier]):
                    self.set_checker_enabled(checker, enabled)
            elif identifier in profiles:
                if identifier in reserved_names:
                    LOG.warning("Profile name '%s' conflicts with a "
                                "checker(-group) name.", identifier)
                for checker in checker_labels.checkers_by_labels(
                        [f'profile:{identifier}']):
                    self.set_checker_enabled(checker, enabled)
            elif identifier in guidelines:
                if identifier in reserved_names:
                    LOG.warning("Guideline name '%s' conflicts with a "
                                "checker(-group) name.", identifier)
                for checker in checker_labels.checkers_by_labels(
                        [f'guideline:{identifier}']):
                    self.set_checker_enabled(checker, enabled)
            else:
                self.set_checker_enabled(identifier, enabled)
