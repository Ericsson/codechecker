# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

import os
import re
import shlex
import subprocess

from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.logger import LoggerFactory
from libcodechecker.util import get_binary_in_path

LOG = LoggerFactory.get_new_logger('CLANG TIDY')


class ClangTidy(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    def __parse_checkers(self, tidy_output):
        """
        Parse clang tidy checkers list.
        Skip clang static analyzer checkers.
        Store them to checkers.
        """
        for line in tidy_output.splitlines():
            line = line.strip()
            if re.match(r'^Enabled checks:', line) or line == '':
                continue
            elif line.startswith('clang-analyzer-'):
                continue
            else:
                match = re.match(r'^\S+$', line)
                if match:
                    self.checkers.append((match.group(0), ''))

    def get_analyzer_checkers(self, config_handler, env):
        """
        Return the list of the supported checkers.
        """
        if not self.checkers:
            analyzer_binary = config_handler.analyzer_binary

            command = [analyzer_binary, "-list-checks", "-checks='*'", "-",
                       "--"]

            try:
                command = shlex.split(' '.join(command))
                result = subprocess.check_output(command, env=env)
                self.__parse_checkers(result)
            except (subprocess.CalledProcessError, OSError):
                return {}

        return self.checkers

    def construct_analyzer_cmd(self, res_handler):
        """
        """
        try:
            config = self.config_handler

            analyzer_cmd = [config.analyzer_binary]

            # Disable all checkers by default.
            # The latest clang-tidy (3.9) release enables clang static analyzer
            # checkers by default. They must be disabled explicitly.
            checkers_cmdline = '-*,-clang-analyzer-*'

            # Config handler stores which checkers are enabled or disabled.
            for checker_name, value in config.checks().items():
                enabled, _ = value
                if enabled:
                    checkers_cmdline += ',' + checker_name
                else:
                    checkers_cmdline += ',-' + checker_name

            analyzer_cmd.append("-checks='" + checkers_cmdline.lstrip(',') +
                                "'")

            LOG.debug(config.analyzer_extra_arguments)
            analyzer_cmd.append(config.analyzer_extra_arguments)

            analyzer_cmd.append(self.source_file)

            analyzer_cmd.append("--")

            # Options before the analyzer options.
            if len(config.compiler_resource_dir) > 0:
                analyzer_cmd.extend(['-resource-dir',
                                     config.compiler_resource_dir,
                                     '-isystem',
                                     config.compiler_resource_dir])

            if config.compiler_sysroot:
                analyzer_cmd.extend(['--sysroot', config.compiler_sysroot])

            for path in config.system_includes:
                analyzer_cmd.extend(['-isystem', path])

            for path in config.includes:
                analyzer_cmd.extend(['-I', path])

            # Set language.
            analyzer_cmd.extend(['-x', self.buildaction.lang])

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.extend(self.buildaction.compiler_includes)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def get_analyzer_mentioned_files(self, output):
        """
        Parse Clang-Tidy's output to generate a list of files that were
        mentioned in the standard output or standard error.
        """

        # A line mentioning a file in Clang-Tidy's output looks like this:
        # /home/.../.cpp:L:C: warning: foobar.
        regex = re.compile(
            # File path followed by a ':'.
            '^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            '(?P<line>\d+?):'
            # Column number followed by a ':' and a space.
            '(?P<column>\d+?):\ ')

        paths = []

        for line in output.splitlines():
            match = re.match(regex, line)
            if match:
                paths.append(match.group('path'))

        return set(paths)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug(configured_binary + " not found in path for ClangTidy!")

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        # clang-tidy, clang-tidy-5.0, ...
        clangtidy = get_binary_in_path(['clang-tidy'],
                                       r'^clang-tidy(-\d+(\.\d+){0,2})?$',
                                       env)

        if clangtidy:
            LOG.debug("Using '" + clangtidy + "' for Clang-tidy!")
        return clangtidy
