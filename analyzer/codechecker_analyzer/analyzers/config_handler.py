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


class CheckerHandling(object):
    """
    The possible states of a checker from perspective of handling it inside
    CodeChecker. The Checker can either be implicitly handled, and be in the
    AUTO state, or explicitly managed. Explicit handling could result in the
    checker being either ENABLED or DISABLED state.

    TODO: This should be implemented as an enum in Python 3.
    """

    AUTO, ENABLED, DISABLED = range(0, 3)

    def __init__(self):
        self.__value = CheckerHandling.AUTO

    def is_enabled(self):
        return self.__value == CheckerHandling.ENABLED

    def set_enabled(self):
        self.__value = CheckerHandling.ENABLED
        return self

    def is_disabled(self):
        return self.__value == CheckerHandling.DISABLED

    def set_disabled(self):
        self.__value = CheckerHandling.DISABLED
        return self

    def is_auto(self):
        return self.__value == CheckerHandling.AUTO

    def set_auto(self):
        self.__value = CheckerHandling.AUTO
        return self

    def __str__(self):
        return ['automatic', 'enabled', 'disabled'][self.__value]


class Checker(object):
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class CheckerHandler(object):
    """
    CheckerHandler class is used to store available checkers, every one of
    which can have a state of being explicitly enabled, explicitly disabled or
    implicitly handled.
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        # The key is the checker name, the value is a Checker.
        self.__checkers = collections.OrderedDict()

    def register_checker(self, name, description=None, state=None):
        """
        Make a checker available. By default the checkers handling is set to
        implicit. If there exists a checker that is already available this
        method does not no modifications.

        Arguments:
        name -- name of the checker. type: string
        description -- description of the checker. type: string
        state -- handling status of the checker. type: CheckerHandling
        """

        # Checker is added with implicit handling by default.
        if state is None:
            state = CheckerHandling().set_auto()

        if name not in self.__checkers:
            self.__checkers[name] = (state, Checker(name, description))

    def _set_handling_for_matching(self, target_name, handling):
        """
        Set the handling of checkers those name either starts or ends with
        target_name to the category specified by handling.
        """

        for checker_entry in self.__checkers.items():
            checker_name, checker = checker_entry
            if checker_name.startswith(target_name) or \
               checker_name.endswith(target_name):
                self.__checkers[checker_name] = (handling, checker)

    def enable_matching_checkers(self, target_name):
        """
        Explicitly enable checkers those name either starts or ends with
        target_name.
        """

        self._set_handling_for_matching(target_name,
                                        CheckerHandling().set_enabled())

    def disable_matching_checkers(self, target_name):
        """
        Explicitly disable checkers those name either starts or ends with
        target_name.
        """

        self._set_handling_for_matching(target_name,
                                        CheckerHandling().set_disabled())

    def automate_matching_checkers(self, target_name):
        """
        Make the handling of checkers those name either starts or ends with
        target_name implicit.
        """

        self._set_handling_for_matching(target_name,
                                        CheckerHandling().set_auto())

    def checkers(self):
        """
        Returns a collections of tuples keyed by checker names. Every tuple has
        the enabled state of type CheckerHandling as the first element, and the
        checker object of type Checker as the second.
        """
        return self.__checkers


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

        self.__available_checkers = CheckerHandler()

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

    def checker_handler(self):
        """
        Return the configuration for checkers.
        """
        return self.__available_checkers

    def __gen_name_variations(self):
        """
        Generate all applicable name variations from the given checker list.
        """
        checker_names = self.checker_handler().checkers().keys()
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

        handler = self.checker_handler()

        # By default all checkers are in the AUTO state. This means that the
        # analysis framework should decide to whether use the checker or not.
        for checker_name, description in checkers:
            handler.register_checker(checker_name, description)

        # Set default enabled or disabled checkers, based on the config file.
        if checker_config:
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
                        handler.enable_matching_checkers(checker_name)

        # If enable_all is given, almost all checkers should be enabled.
        if enable_all:
            for checker_name, _ in checkers:
                if not checker_name.startswith("alpha.") and \
                        not checker_name.startswith("debug.") and \
                        not checker_name.startswith("osx."):
                    # There are a few exceptions, though, which still need to
                    # be manually enabled by the user: alpha and debug.
                    handler.enable_matching_checkers(checker_name)

                if checker_name.startswith("osx.") and \
                        platform.system() == 'Darwin':
                    # OSX checkers are only enable-all'd if we are on OSX.
                    handler.enable_matching_checkers(checker_name)

        # Set user defined enabled or disabled checkers from the command line.
        if cmdline_checkers:

            # Construct a list of reserved checker names.
            # (It is used to check if a profile name is valid.)
            reserved_names = self.__gen_name_variations()

            for identifier, state in cmdline_checkers:

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
                        if state:
                            handler.enable_matching_checkers(checker_name)
                        else:
                            handler.disable_matching_checkers(checker_name)

                # The identifier is a checker(-group) name.
                else:
                    checker_name = identifier
                    if state:
                        handler.enable_matching_checkers(checker_name)
                    else:
                        handler.disable_matching_checkers(checker_name)
