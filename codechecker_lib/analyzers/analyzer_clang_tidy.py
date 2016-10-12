# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""

import re
import subprocess
import shlex

from codechecker_lib import logger

from codechecker_lib.analyzers import analyzer_base

LOG = logger.get_new_logger('CLANG TIDY')


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
                result = subprocess.check_output(command,
                                                 env=env)
            except subprocess.CalledProcessError as cperr:
                LOG.error(cperr)
                return {}

            self.__parse_checkers(result)

        return self.checkers

    def construct_analyzer_cmd(self, res_handler):
        """
        """
        try:
            config = self.config_handler

            analyzer_bin = config.analyzer_binary

            analyzer_cmd = [analyzer_bin]

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

            analyzer_cmd.append("-checks='" + checkers_cmdline.lstrip(',') + "'")

            LOG.debug(config.analyzer_extra_arguments)
            analyzer_cmd.append(config.analyzer_extra_arguments)

            analyzer_cmd.append(self.source_file)

            analyzer_cmd.append("--")

            extra_arguments_before = []
            if len(config.compiler_resource_dirs) > 0:
                for inc_dir in config.compiler_resource_dirs:
                    extra_arguments_before.append('-resource-dir')
                    extra_arguments_before.append(inc_dir)
                    extra_arguments_before.append('-isystem')
                    extra_arguments_before.append(inc_dir)

            if config.compiler_sysroot:
                extra_arguments_before.append('--sysroot')
                extra_arguments_before.append(config.compiler_sysroot)

            for path in config.system_includes:
                extra_arguments_before.append('-isystem')
                extra_arguments_before.append(path)

            for path in config.includes:
                extra_arguments_before.append('-I')
                extra_arguments_before.append(path)

            # Set lang.
            extra_arguments_before.append('-x')
            extra_arguments_before.append(self.buildaction.lang)

            analyzer_cmd.append(' '.join(extra_arguments_before))

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []
