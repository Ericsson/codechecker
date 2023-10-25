# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""
from collections import defaultdict
# TODO distutils will be removed in python3.12
from distutils.version import StrictVersion
import os
import pickle
import shlex
import subprocess

from codechecker_common.logger import get_logger

from codechecker_analyzer import analyzer_context

from .. import analyzer_base
from ..flag import has_flag
from ..config_handler import CheckerState

from .config_handler import GccConfigHandler
from .result_handler import GccResultHandler, \
    actual_name_to_codechecker_name, codechecker_name_to_actual_name_disabled

LOG = get_logger('analyzer.gcc')


class Gcc(analyzer_base.SourceAnalyzer):
    """
    Constructs the Gcc analyzer commands.
    """

    ANALYZER_NAME = 'gcc'

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    def add_checker_config(self, checker_cfg):
        # TODO
        pass

    @classmethod
    def get_analyzer_mentioned_files(self, output):
        """
        This is mostly used for CTU, which is absent in GCC.
        """
        pass

    def construct_analyzer_cmd(self, result_handler):
        """
        Construct analyzer command for gcc.
        """
        # TODO: This is not a try-catch block, like the other analyzers. Why
        # should it? Should the others be? When can list creating list to have
        # unforeseen exceptions where a general catch is justified?
        config = self.config_handler

        # We don't want GCC do start linking, but -fsyntax-only stops the
        # compilation process too early for proper diagnostics generation.
        analyzer_cmd = [Gcc.analyzer_binary(), '-fanalyzer', '-c',
                        '-o/dev/null']

        # Add extra arguments.
        analyzer_cmd.extend(config.analyzer_extra_arguments)

        analyzer_cmd.extend(self.buildaction.analyzer_options)

        analyzer_cmd.append('-fdiagnostics-format=sarif-file')

        for checker_name, value in config.checks().items():
            if value[0] == CheckerState.disabled:
                # TODO python3.9 removeprefix method would be nicer
                # than startswith and a hardcoded slicing
                analyzer_cmd.append(
                    codechecker_name_to_actual_name_disabled(checker_name))

        compile_lang = self.buildaction.lang
        if not has_flag('-x', analyzer_cmd):
            analyzer_cmd.extend(['-x', compile_lang])

        analyzer_cmd.append(self.source_file)

        LOG.debug_analyzer("Running analysis command "
                           f"'{shlex.join(analyzer_cmd)}'")

        return analyzer_cmd

    @classmethod
    def get_analyzer_checkers(self):
        """
        Return the list of the supported checkers.
        """
        command = [self.analyzer_binary(), "--help=warning"]
        checker_list = []

        try:
            output = subprocess.check_output(command)

            # Still contains the help message we need to remove.
            for entry in output.decode().split('\n'):
                warning_name, _, description = entry.strip().partition(' ')
                # GCC Static Analyzer names start with -Wanalyzer.
                if warning_name.startswith('-Wanalyzer'):
                    # Rename the checkers interally (similarly to how we
                    # support cppcheck)
                    renamed_checker_name = \
                        actual_name_to_codechecker_name(warning_name)
                    checker_list.append(
                        (renamed_checker_name, description.strip()))
            return checker_list
        except (subprocess.CalledProcessError) as e:
            LOG.error(e.stderr)
        except (OSError) as e:
            LOG.error(e.errno)
        return []

    @classmethod
    def get_analyzer_config(cls):
        """
        Config options for gcc.
        """
        # TODO
        return []

    @classmethod
    def get_checker_config(cls):
        """
        TODO add config options for gcc checkers.
        """
        # TODO
        return []

    def analyze(self, analyzer_cmd, res_handler, proc_callback=None):
        env = None

        original_env_file = os.environ.get(
            'CODECHECKER_ORIGINAL_BUILD_ENV')
        if original_env_file:
            with open(original_env_file, 'rb') as env_file:
                env = pickle.load(env_file, encoding='utf-8')

        return super().analyze(analyzer_cmd, res_handler, proc_callback, env)

    def post_analyze(self, result_handler: GccResultHandler):
        """
        Post process the reuslts after the analysis.
        Will copy the sarif files created by gcc into the root of the reports
        folder.
        Renames the source plist files to *.plist.bak because
        The report parsing of the Parse command is done recursively.

        """
        pass

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """
        # TODO
        pass

    @classmethod
    def get_binary_version(self, environ, details=False) -> str:
        """
        Return the analyzer version.
        """
        if details:
            version = [self.analyzer_binary(), '--version']
        else:
            version = [self.analyzer_binary(), '-dumpfullversion']
        try:
            output = subprocess.check_output(version,
                                             env=environ,
                                             encoding="utf-8",
                                             errors="ignore")
            return output.strip()
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(version))
            LOG.warning(oerr)

        return None

    @classmethod
    def is_binary_version_incompatible(cls, environ):
        """
        Check the version compatibility of the given analyzer binary.
        """
        analyzer_version = cls.get_binary_version(environ)

        # The analyzer version should be above 13.0.0 because the
        # '-fdiagnostics-format=sarif-file' argument was introduced in this
        # release.
        if analyzer_version >= StrictVersion("13.0.0"):
            return None

        return f"GCC binary found is too old at v{analyzer_version.strip()}; "\
               "minimum version is 13.0.0."

    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = GccResultHandler(buildaction, report_output,
                                       self.config_handler.report_hash)

        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args):
        handler = GccConfigHandler()

        analyzer_config = defaultdict(list)

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    analyzer_config[cfg.option].append(cfg.value)

        handler.analyzer_config = analyzer_config

        checkers = cls.get_analyzer_checkers()

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for %s',
                               cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
