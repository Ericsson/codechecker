# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import re
import shlex
import subprocess

from codechecker_lib import logger

from codechecker_lib.analyzers import analyzer_base

LOG = logger.get_new_logger('CLANGSA')


class ClangSA(analyzer_base.SourceAnalyzer):
    """
    Constructs clang static analyzer commands.
    """

    def __parse_checkers(self, clangsa_output):
        """
        Parse clang static analyzer checkers, store them to checkers.
        """

        # Checker name and description in one line.
        pattern = re.compile(
            r'^\s\s(?P<checker_name>\S*)\s*(?P<description>.*)')

        checker_name = None
        for line in clangsa_output.splitlines():
            if re.match(r'^CHECKERS:', line) or line == '':
                continue
            elif checker_name and not re.match(r'^\s\s\S', line):
                # Collect description for the checker name.
                self.checkers.append((checker_name, line.strip()))
                checker_name = None
            elif re.match(r'^\s\s\S+$', line.rstrip()):
                # Only checker name is in the line.
                checker_name = line.strip()
            else:
                # Checker name and description is in one line.
                match = pattern.match(line.rstrip())
                if match:
                    current = match.groupdict()
                    self.checkers.append((current['checker_name'],
                                          current['description']))

    def get_analyzer_checkers(self, config_handler, env):
        """
        Return the list of the supported checkers.
        """
        if not self.checkers:
            analyzer_binary = config_handler.analyzer_binary

            command = [analyzer_binary, "-cc1"]
            for plugin in config_handler.analyzer_plugins:
                command.append("-load")
                command.append(plugin)
            command.append("-analyzer-checker-help")

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
        Called by the analyzer method.
        Construct the analyzer command.
        """
        try:
            # Get an output file from the result handler.
            analyzer_output_file = res_handler.get_analyzer_result_file()

            analyzer_mode = 'plist-multi-file'

            # Get the checkers list from the config_handler.
            # Checker order matters.
            config = self.config_handler

            analyzer_bin = config.analyzer_binary

            analyzer_cmd = [analyzer_bin]

            if len(config.compiler_resource_dirs) > 0:
                for inc_dir in config.compiler_resource_dirs:
                    analyzer_cmd.append('-resource-dir')
                    analyzer_cmd.append(inc_dir)
                    analyzer_cmd.append('-isystem')
                    analyzer_cmd.append(inc_dir)

            # Compiling is enough.
            analyzer_cmd.append('-c')

            analyzer_cmd.append('--analyze')

            # Turn off clang hardcoded checkers list.
            analyzer_cmd.append('--analyzer-no-default-checks')

            for plugin in config.analyzer_plugins:
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append("-plugin")
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append("checkercfg")
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append("-load")
                analyzer_cmd.append("-Xclang")
                analyzer_cmd.append(plugin)

            analyzer_cmd.append('-Xclang')
            analyzer_cmd.append('-analyzer-opt-analyze-headers')
            analyzer_cmd.append('-Xclang')
            analyzer_cmd.append('-analyzer-output=' + analyzer_mode)

            if config.compiler_sysroot:
                analyzer_cmd.append('--sysroot')
                analyzer_cmd.append(config.compiler_sysroot)

            for path in config.system_includes:
                analyzer_cmd.append('-isystem')
                analyzer_cmd.append(path)

            for path in config.includes:
                analyzer_cmd.append('-I')
                analyzer_cmd.append(path)

            analyzer_cmd.append('-o')
            analyzer_cmd.append(analyzer_output_file)

            # Config handler stores which checkers are enabled or disabled.
            for checker_name, value in config.checks().items():
                enabled, description = value
                if enabled:
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append('-analyzer-checker=' + checker_name)
                else:
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append('-analyzer-disable-checker')
                    analyzer_cmd.append('-Xclang')
                    analyzer_cmd.append(checker_name)

            # Set lang.
            analyzer_cmd.append('-x')
            analyzer_cmd.append(self.buildaction.lang)

            analyzer_cmd.append(config.analyzer_extra_arguments)

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []
