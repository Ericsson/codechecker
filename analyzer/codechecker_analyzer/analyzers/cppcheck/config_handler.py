# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Config handler for Cppcheck analyzer.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import shlex
import subprocess
import xml.etree.ElementTree as ET

from collections import namedtuple, OrderedDict

from codechecker_common.logger import get_logger

from .. import config_handler

LOG = get_logger('analyzer.cppcheck')


CppcheckChecker = namedtuple('CppcheckChecker', ['enabled',
                                                 'description',
                                                 'severity'])


def parse_checkers(cppcheck_output):
    """
    Parse cppcheck checkers list.
    """
    checkers = []

    tree = ET.ElementTree(ET.fromstring(cppcheck_output))
    root = tree.getroot()
    errors = root.find('errors')
    for error in errors.findall('error'):
        name = error.attrib.get('id')
        msg = error.attrib.get('msg')
        severity = error.attrib.get('severity')

        checkers.append((name, msg, severity))

    return checkers


class CppcheckConfigHandler(config_handler.AnalyzerConfigHandler):
    """
    Configuration handler for Cppcheck analyzer.
    """

    def __init__(self):
        super(CppcheckConfigHandler, self).__init__()

        # The key is the checker name, the value is a tuple.
        # False if disabled (should be by default).
        # True if checker is enabled.
        # (False/True, 'checker_description')
        self.__checkers = OrderedDict()

    def get_analyzer_checkers(self, env):
        """
        Return the list of the supported checkers.
        """
        command = [self.analyzer_binary, "--errorlist"]

        try:
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(command, env=env)
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    def add_checker(self, checker_name, enabled, description, severity):
        """
        Add additional checker.
        Tuple of (checker_name, True or False).
        """
        self.__checkers[checker_name] = \
            CppcheckChecker(enabled=enabled,
                            description=description,
                            severity=severity)

    def set_checker_enabled(self, checker_name, enabled=True):
        """
        Enable checker, keep description if already set.
        """
        for ch_name, _ in self.__checkers.items():
            if ch_name.startswith(checker_name) or \
               ch_name.endswith(checker_name):
                self.__checkers[ch_name] = \
                    self.__checkers[ch_name]._replace(enabled=enabled)

    @property
    def checkers(self):
        """
        Return the checkers.
        """
        return self.__checkers

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
        # By default disable all checkers except errors.
        for checker_name, description, severity in checkers:
            enabled = True if severity == 'error' else False
            self.add_checker(checker_name, enabled, description, severity)

        # Set user defined enabled or disabled checkers from the command line.
        if cmdline_checkers:
            for checker_name, enabled in cmdline_checkers:
                self.set_checker_enabled(checker_name, enabled)
