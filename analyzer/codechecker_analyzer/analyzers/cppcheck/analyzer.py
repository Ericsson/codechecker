# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import re
import shlex

from codechecker_common.logger import get_logger

from codechecker_analyzer import host_check
from codechecker_analyzer.env import extend, get_binary_in_path, \
    replace_env_var

from .. import analyzer_base

from .config_handler import CppcheckConfigHandler
from .result_handler import ResultHandlerCppcheck

LOG = get_logger('analyzer.cppcheck')


class Cppcheck(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    ANALYZER_NAME = 'cppcheck'

    def add_checker_config(self, checker_cfg):
        LOG.error("Not implemented yet")

    def get_analyzer_mentioned_files(self, output):
        """
        Return a collection of files that were mentioned by the analyzer in
        its standard outputs, which should be analyzer_stdout or
        analyzer_stderr from a result handler.
        """
        pass

    def construct_analyzer_cmd(self, result_handler):
        """
        Construct analyzer command for cppcheck.
        """
        try:
            config = self.config_handler

            analyzer_cmd = [config.analyzer_binary]

            # Enable or disable checkers.
            enabled_severity_levels = set()
            suppressed_checkers = set()
            for checker_name, value in config.checkers.items():
                if not value.enabled:
                    suppressed_checkers.add(checker_name)
                elif value.severity and value.severity != 'error':
                    enabled_severity_levels.add(value.severity)

            if enabled_severity_levels:
                analyzer_cmd.append('--enable=' +
                                    ','.join(enabled_severity_levels))

            for checker_name in suppressed_checkers:
                analyzer_cmd.append('--suppress=' + checker_name)

            # Add extra arguments.
            analyzer_cmd.extend(config.analyzer_extra_arguments)

            # Add compiler includes.
            compile_lang = self.buildaction.lang
            for include in self.buildaction.compiler_includes[compile_lang]:
                analyzer_cmd.append('-I' if include == '-isystem' else include)

            analyzer_cmd.append('--plist-output=' + result_handler.workspace)
            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def post_analyze(self, result_handler):
        """
        Renames the generated plist file with a unique name.
        """
        file_name = os.path.splitext(os.path.basename(self.source_file))[0]
        output_file = os.path.join(result_handler.workspace,
                                   file_name + '.plist')
        if os.path.exists(output_file):
            output = os.path.join(result_handler.workspace,
                                  result_handler.analyzer_result_file)

            os.rename(output_file, output)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug("%s not found in path for Cppcheck!", configured_binary)

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        cppcheck = get_binary_in_path(['cppcheck'],
                                      r'^cppcheck(-\d+(\.\d+){0,2})?$',
                                      env)

        if cppcheck:
            LOG.debug("Using '%s' for Cppcheck!", cppcheck)
        return cppcheck

    def construct_result_handler(self, buildaction, report_output,
                                 severity_map, skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = ResultHandlerCppcheck(buildaction, report_output,
                                            self.config_handler.report_hash)

        res_handler.severity_map = severity_map
        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args, context):
        handler = CppcheckConfigHandler()
        handler.analyzer_binary = context.analyzer_binaries.get(
            cls.ANALYZER_NAME)

        check_env = extend(context.path_env_extra,
                           context.ld_lib_path_extra)

        # Overwrite PATH to contain only the parent of the clang binary.
        if os.path.isabs(handler.analyzer_binary):
            check_env['PATH'] = os.path.dirname(handler.analyzer_binary)
        cppcheck_bin = cls.resolve_missing_binary('cppcheck', check_env)

        handler.compiler_resource_dir = \
            host_check.get_resource_dir(cppcheck_bin, context)

        try:
            with open(args.cppcheck_args_cfg_file, 'rb') as cppcheck_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)', replace_env_var,
                           cppcheck_cfg.read().strip())
                handler.analyzer_extra_arguments = \
                    shlex.split(handler.analyzer_extra_arguments)
        except IOError as ioerr:
            LOG.debug_analyzer(ioerr)
        except AttributeError as aerr:
            # No Cppcheck arguments file was given in the command line.
            LOG.debug_analyzer(aerr)

        checkers = handler.get_analyzer_checkers(check_env)

        # Read cppcheck checkers from the config file.
        cppcheck_checkers = context.checker_config.get(cls.ANALYZER_NAME +
                                                       '_checkers')

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for %s',
                               cls.ANALYZER_NAME)
            cmdline_checkers = None

        handler.initialize_checkers(
            context.available_profiles,
            context.package_root,
            checkers,
            cppcheck_checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
