# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import re
import shlex
import subprocess

from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.analyze.analyzers import ctu_triple_arch
from libcodechecker.analyze import analyzer_env
from libcodechecker.logger import LoggerFactory
from libcodechecker.util import get_binary_in_path

LOG = LoggerFactory.get_new_logger('CLANGSA')


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
                command.extend(["-load", plugin])
            command.append("-analyzer-checker-help")

            try:
                command = shlex.split(' '.join(command))
                result = subprocess.check_output(command,
                                                 env=env)
                self.__parse_checkers(result)
            except (subprocess.CalledProcessError, OSError):
                return {}

        return self.checkers

    def construct_analyzer_cmd(self, result_handler):
        """
        Called by the analyzer method.
        Construct the analyzer command.
        """
        try:
            # Get an output file from the result handler.
            analyzer_output_file = result_handler.analyzer_result_file

            # Get the checkers list from the config_handler.
            # Checker order matters.
            config = self.config_handler

            analyzer_cmd = [config.analyzer_binary]

            if len(config.compiler_resource_dir) > 0:
                analyzer_cmd.extend(['-resource-dir',
                                     config.compiler_resource_dir,
                                     '-isystem',
                                     config.compiler_resource_dir])

            # Do not warn about the unused gcc/g++ arguments.
            analyzer_cmd.append('-Qunused-arguments')

            analyzer_cmd.append('--analyze')

            # Turn off clang hardcoded checkers list.
            analyzer_cmd.append('--analyzer-no-default-checks')

            for plugin in config.analyzer_plugins:
                analyzer_cmd.extend(["-Xclang", "-plugin",
                                     "-Xclang", "checkercfg",
                                     "-Xclang", "-load",
                                     "-Xclang", plugin])

            analyzer_mode = 'plist-multi-file'
            analyzer_cmd.extend(['-Xclang',
                                 '-analyzer-opt-analyze-headers',
                                 '-Xclang',
                                 '-analyzer-output=' + analyzer_mode])

            analyzer_cmd.extend(['-o', analyzer_output_file])

            # Config handler stores which checkers are enabled or disabled.
            for checker_name, value in config.checks().items():
                enabled, _ = value
                if enabled:
                    analyzer_cmd.extend(['-Xclang',
                                         '-analyzer-checker=' + checker_name])
                else:
                    analyzer_cmd.extend(['-Xclang',
                                         '-analyzer-disable-checker',
                                         '-Xclang', checker_name])

            if config.ctu_dir:
                analyzer_cmd.extend(['-Xclang', '-analyzer-config',
                                     '-Xclang',
                                     'xtu-dir=' + self.get_xtu_dir(),
                                     ])
                if config.ctu_has_analyzer_display_ctu_progress:
                    analyzer_cmd.extend(['-Xclang',
                                         '-analyzer-display-ctu-progress'])
                if config.ctu_in_memory:
                    analyzer_cmd.extend(['-Xclang', '-analyzer-config',
                                         '-Xclang',
                                         'xtu-reparse=' +
                                         os.path.abspath(config.log_file[0])])

            # Set language.
            analyzer_cmd.extend(['-x', self.buildaction.lang])

            analyzer_cmd.append(config.analyzer_extra_arguments)

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.extend(self.buildaction.compiler_includes)

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def get_xtu_dir(self):
        """
        Returns the path of the xtu directory (containing the triple).
        """
        config = self.config_handler
        env = analyzer_env.get_check_env(config.path_env_extra,
                                         config.ld_lib_path_extra)
        triple_arch = ctu_triple_arch.get_triple_arch(self.buildaction,
                                                      self.source_file,
                                                      config, env)
        xtu_dir = os.path.join(config.ctu_dir, triple_arch)
        return xtu_dir

    def get_analyzer_mentioned_files(self, output):
        """
        Parse ClangSA's output to generate a list of files that were mentioned
        in the standard output or standard error.
        """

        regex_for_ctu_ast_load = re.compile(
            "ANALYZE \(CTU loaded AST for source file\): (.*)")

        paths = []

        xtu_ast_dir = os.path.join(self.get_xtu_dir(), "ast")

        for line in output.splitlines():
            match = re.match(regex_for_ctu_ast_load, line)
            if match:
                path = match.group(1)
                if xtu_ast_dir in path:
                    paths.append(path[len(xtu_ast_dir):])

        return set(paths)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug(configured_binary + " not found in path for ClangSA!")

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        # clang, clang-5.0, clang++, clang++-5.1, ...
        clang = get_binary_in_path(['clang', 'clang++'],
                                   r'^clang(\+\+)?(-\d+(\.\d+){0,2})?$',
                                   env)

        if clang:
            LOG.debug("Using '" + clang + "' for ClangSA!")
        return clang
