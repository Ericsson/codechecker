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

from .config_handler import GccConfigHandler
from .result_handler import GccResultHandler

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

    @classmethod
    def get_version(cls, env=None):
        """ Get analyzer version information. """
        return cls.__get_analyzer_version(cls.analyzer_binary(), env)

    def add_checker_config(self, checker_cfg):
        LOG.warning("Checker configuration for Gcc is not implemented yet")

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

        compile_lang = self.buildaction.lang
        if not has_flag('-x', analyzer_cmd):
            analyzer_cmd.extend(['-x', compile_lang])

        analyzer_cmd.append(self.source_file)

        LOG.debug_analyzer("Running analysis command "
                           f"'{shlex.join(analyzer_cmd)}'")

        return analyzer_cmd

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return the list of the supported checkers.
        """
        command = [cls.analyzer_binary(), "--help=warning"]
        checker_list = []

        try:
            output = subprocess.check_output(command)

            # Still contains the help message we need to remove.
            for entry in output.decode().split('\n'):
                warning_name, _, description = entry.strip().partition(' ')
                if warning_name.startswith('-Wanalyzer'):
                    checker_list.append((warning_name, description))
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

        LOG.error("%s not found in path for GCC!", configured_binary)

        # if os.path.isabs(configured_binary):
        #     # Do not autoresolve if the path is an absolute path as there
        #     # is nothing we could auto-resolve that way.
        #     return False

        # cppcheck = get_binary_in_path(['g++-13'],
        #                               r'^cppcheck(-\d+(\.\d+){0,2})?$',
        #                               env)

        # if cppcheck:
        #     LOG.debug("Using '%s' for Cppcheck!", cppcheck)
        # return cppcheck

    @classmethod
    def __get_analyzer_version(cls, analyzer_binary, env):
        """
        Return the analyzer version.
        """
        # --version outputs a lot of garbage as well (like copyright info),
        # this only contains the version info.
        version = [analyzer_binary, '-dumpfullversion']
        try:
            output = subprocess.check_output(version,
                                             env=env,
                                             encoding="utf-8",
                                             errors="ignore")
            return output
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(version))
            LOG.warning(oerr)

        return None

    @classmethod
    def version_compatible(cls, configured_binary, environ):
        """
        Check the version compatibility of the given analyzer binary.
        """
        analyzer_version = \
            cls.__get_analyzer_version(configured_binary, environ)

        # The analyzer version should be above 13.0.0 because the
        # '-fdiagnostics-format=sarif-file' argument was introduced in this
        # release.
        if analyzer_version >= StrictVersion("13.0.0"):
            return True

        # FIXME: Maybe this isn't to place to emit an error, especially when
        # we cycle over multiple binarier to find the correct one.
        LOG.error("GCC binary found is too old at "
                  f"v{analyzer_version.strip()}; minimum version is 13.0.0.")
        return False

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
        context = analyzer_context.get_context()
        handler = GccConfigHandler()

        analyzer_config = defaultdict(list)

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    analyzer_config[cfg.option].append(cfg.value)

        handler.analyzer_config = analyzer_config

        # check_env = context.analyzer_env

        # # Overwrite PATH to contain only the parent of the cppcheck binary.
        # if os.path.isabs(Gcc.analyzer_binary()):
        #     check_env['PATH'] = os.path.dirname(Gcc.analyzer_binary())

        checkers = cls.get_analyzer_checkers()

        # Cppcheck can and will report with checks that have a different
        # name than marked in the --errorlist xml. To be able to suppress
        # these reports, the checkerlist needs to be extended by those found
        # in the label file.
        checker_labels = context.checker_labels
        checkers_from_label = checker_labels.checkers("gcc")
        parsed_set = set([data[0] for data in checkers])
        for checker in set(checkers_from_label):
            if checker not in parsed_set:
                checkers.append((checker, ""))

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
