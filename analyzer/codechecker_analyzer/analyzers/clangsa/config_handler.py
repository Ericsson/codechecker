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
import re
import subprocess

from codechecker_common.logger import get_logger
from .ctu_autodetection import CTUAutodetection

from . import clang_options
from . import version

from .. import config_handler

LOG = get_logger('analyzer.clangsa')


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

    def add_checker_config(self, config):
        """
        Add a (checker_name, key, value) tuple to the list.
        """
        self.__checker_configs.append(config)

    @property
    def ctu_capability(self):
        return CTUAutodetection(self.analyzer_binary, self.environ)
