# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Clang Static Analyzer related functions.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import re
import shlex
import subprocess

from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze import host_check
from libcodechecker.analyze.analyzers import analyzer_base
from libcodechecker.analyze.analyzers import config_handler_clangsa
from libcodechecker.analyze.analyzers import ctu_triple_arch
from libcodechecker.analyze.analyzers.result_handler_clangsa import \
    ResultHandlerClangSA
from libcodechecker.analyze.analyzer_env import \
    extend_analyzer_cmd_with_resource_dir
from libcodechecker.logger import get_logger
from libcodechecker.util import get_binary_in_path, replace_env_var

LOG = get_logger('analyzer')


def parse_checkers(clangsa_output):
    """
    Parse clang static analyzer checkers list output.
    Return a list of (checker name, description) tuples.
    """

    # Checker name and description in one line.
    pattern = re.compile(
        r'^\s\s(?P<checker_name>\S*)\s*(?P<description>.*)')
    checkers_list = []
    checker_name = None
    for line in clangsa_output.splitlines():
        if line.startswith('CHECKERS:') or line == '':
            continue
        elif checker_name and not re.match(r'^\s\s\S', line):
            # Collect description for the checker name.
            checkers_list.append((checker_name, line.strip()))
            checker_name = None
        elif re.match(r'^\s\s\S+$', line.rstrip()):
            # Only checker name is in the line.
            checker_name = line.strip()
        else:
            # Checker name and description is in one line.
            match = pattern.match(line.rstrip())
            if match:
                current = match.groupdict()
                checkers_list.append((current['checker_name'],
                                      current['description']))
    return checkers_list


class ClangSA(analyzer_base.SourceAnalyzer):
    """
    Constructs clang static analyzer commands.
    """
    ANALYZER_NAME = 'clangsa'

    def __init__(self, config_handler, buildaction):
        super(ClangSA, self).__init__(config_handler, buildaction)
        self.__disable_ctu = False
        self.__checker_configs = []

    def is_ctu_available(self):
        """
        Check if ctu is available for the analyzer.
        If the ctu_dir is set in the config, the analyzer is capable to
        run ctu analysis.
        """
        return bool(self.config_handler.ctu_dir)

    def is_ctu_enabled(self):
        """
        Check if ctu is enabled for the analyzer.
        """
        return not self.__disable_ctu

    def disable_ctu(self):
        """
        Disable ctu even if ctu is available.
        By default it is enabled if available.
        """
        self.__disable_ctu = True

    def enable_ctu(self):
        self.__disable_ctu = False

    def add_checker_config(self, checker_cfg):
        """
        Add configuration options to specific checkers.
        checker_cfg should be a list of arguments in case of
        Clang Static Analyzer like this:
        ['-Xclang', '-analyzer-config', '-Xclang', 'checker_option=some_value']
        """

        self.__checker_configs.append(checker_cfg)

    @classmethod
    def get_analyzer_checkers(cls, config_handler, env):
        """
        Return the list of the supported checkers.
        """
        analyzer_binary = config_handler.analyzer_binary

        command = [analyzer_binary, "-cc1"]
        for plugin in config_handler.analyzer_plugins:
            command.extend(["-load", plugin])
        command.append("-analyzer-checker-help")

        try:
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(command,
                                             env=env)
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
            return []

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

            analyzer_cmd = [config.analyzer_binary, '--analyze',
                            # Do not warn about the unused gcc/g++ arguments.
                            '-Qunused-arguments',
                            # Turn off clang hardcoded checkers list.
                            '--analyzer-no-default-checks']

            for plugin in config.analyzer_plugins:
                analyzer_cmd.extend(["-Xclang", "-plugin",
                                     "-Xclang", "checkercfg",
                                     "-Xclang", "-load",
                                     "-Xclang", plugin])

            analyzer_mode = 'plist-multi-file'
            analyzer_cmd.extend(['-Xclang',
                                 '-analyzer-opt-analyze-headers',
                                 '-Xclang',
                                 '-analyzer-output=' + analyzer_mode,
                                 '-o', analyzer_output_file])

            # Checker configuration arguments needs to be set before
            # the checkers.
            if self.__checker_configs:
                for cfg in self.__checker_configs:
                    analyzer_cmd.extend(cfg)

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

            # Get analyzer notes as events from clang.
            analyzer_cmd.extend(['-Xclang',
                                 '-analyzer-config',
                                 '-Xclang', 'notes-as-events=true'])

            if config.ctu_dir and not self.__disable_ctu:
                analyzer_cmd.extend(
                    ['-Xclang', '-analyzer-config', '-Xclang',
                     'experimental-enable-naive-ctu-analysis=true',
                     '-Xclang', '-analyzer-config', '-Xclang',
                     'ctu-dir=' + self.get_ctu_dir()])
                if config.ctu_has_analyzer_display_ctu_progress:
                    analyzer_cmd.extend(['-Xclang',
                                         '-analyzer-display-ctu-progress'])

            # Set language.
            analyzer_cmd.extend(['-x', self.buildaction.lang])
            if self.buildaction.target != "":
                analyzer_cmd.append("--target=" + self.buildaction.target)

            analyzer_cmd.append(config.analyzer_extra_arguments)

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            extend_analyzer_cmd_with_resource_dir(analyzer_cmd,
                                                  config.compiler_resource_dir)

            analyzer_cmd.extend(self.buildaction.compiler_includes)

            if not next((x for x in analyzer_cmd if x.startswith('-std=') or
                        x.startswith('--std')),
                        False):
                analyzer_cmd.append(self.buildaction.compiler_standard)

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def get_ctu_dir(self):
        """
        Returns the path of the ctu directory (containing the triple).
        """
        config = self.config_handler
        env = analyzer_env.get_check_env(config.path_env_extra,
                                         config.ld_lib_path_extra)
        triple_arch = ctu_triple_arch.get_triple_arch(self.buildaction,
                                                      self.source_file,
                                                      config, env)
        ctu_dir = os.path.join(config.ctu_dir, triple_arch)
        return ctu_dir

    def get_analyzer_mentioned_files(self, output):
        """
        Parse ClangSA's output to generate a list of files that were mentioned
        in the standard output or standard error.
        """

        if not output:
            return set()

        regex_for_ctu_ast_load = re.compile(
            r"ANALYZE \(CTU loaded AST for source file\): (.*)")

        paths = set()

        ctu_ast_dir = os.path.join(self.get_ctu_dir(), "ast")

        for line in output.splitlines():
            match = re.match(regex_for_ctu_ast_load, line)
            if match:
                path = match.group(1)
                if ctu_ast_dir in path:
                    paths.add(path[len(ctu_ast_dir):])

        return paths

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

    def construct_result_handler(self, buildaction, report_output,
                                 severity_map, skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = ResultHandlerClangSA(buildaction, report_output)

        res_handler.report_hash = self.config_handler.report_hash
        res_handler.severity_map = severity_map
        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args, context):
        handler = config_handler_clangsa.ClangSAConfigHandler()
        handler.analyzer_plugins_dir = context.checker_plugin
        handler.analyzer_binary = context.analyzer_binaries.get(
            cls.ANALYZER_NAME)
        handler.compiler_resource_dir = \
            host_check.get_resource_dir(handler.analyzer_binary, context)

        handler.report_hash = args.report_hash \
            if 'report_hash' in args else None

        check_env = analyzer_env.get_check_env(context.path_env_extra,
                                               context.ld_lib_path_extra)

        if 'ctu_phases' in args:
            handler.ctu_dir = os.path.join(args.output_path,
                                           args.ctu_dir)

            handler.ctu_has_analyzer_display_ctu_progress = \
                host_check.has_analyzer_feature(
                    context.analyzer_binaries.get(cls.ANALYZER_NAME),
                    '-analyzer-display-ctu-progress',
                    check_env)
            handler.log_file = args.logfile
            handler.path_env_extra = context.path_env_extra
            handler.ld_lib_path_extra = context.ld_lib_path_extra

        try:
            with open(args.clangsa_args_cfg_file, 'rb') as sa_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)',
                           replace_env_var(args.clangsa_args_cfg_file),
                           sa_cfg.read().strip())
        except IOError as ioerr:
            LOG.debug_analyzer(ioerr)
        except AttributeError as aerr:
            # No clangsa arguments file was given in the command line.
            LOG.debug_analyzer(aerr)

        checkers = ClangSA.get_analyzer_checkers(handler, check_env)

        # Read clang-sa checkers from the config file.
        clang_sa_checkers = context.checker_config.get(cls.ANALYZER_NAME +
                                                       '_checkers')

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for ' + cls.ANALYZER_NAME)
            cmdline_checkers = None

        handler.initialize_checkers(
            context.available_profiles,
            context.package_root,
            checkers,
            clang_sa_checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
