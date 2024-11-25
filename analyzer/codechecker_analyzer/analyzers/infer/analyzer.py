# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Module for Facebook Infer analyzer related methods
"""
from collections import defaultdict
# TODO distutils will be removed in python3.12
import shlex
import subprocess
import json
from pathlib import Path

from codechecker_common.logger import get_logger

from codechecker_analyzer import analyzer_context

from .. import analyzer_base
from ..config_handler import CheckerState

from .config_handler import InferConfigHandler
from .result_handler import InferResultHandler
from codechecker_analyzer.buildlog.log_parser import IGNORED_OPTIONS_GCC

LOG = get_logger('analyzer.infer')


class Infer(analyzer_base.SourceAnalyzer):
    """
    Constructs the Infer analyzer commands.
    """

    ANALYZER_NAME = 'infer'

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    def add_checker_config(self, checker_cfg):
        # TODO
        pass

    def get_analyzer_mentioned_files(self, output):
        """
        This is mostly used for CTU.
        """
        return set()

    def construct_analyzer_cmd(self, result_handler):
        """
        Construct analyzer command for Infer.
        """
        # TODO: This is not a try-catch block, like the other analyzers. Why
        # should it? Should the others be? When can list creating list to have
        # unforeseen exceptions where a general catch is justified?
        config = self.config_handler

        analyzer_cmd = [Infer.analyzer_binary(), 'run', '--keep-going',
                        '--project-root', '/']

        for checker_name, value in config.checks().items():
            filtered_name = checker_name.replace("infer-", "")
            filtered_name = filtered_name.replace("-", "_")
            filtered_name = filtered_name.upper()

            if value[0] == CheckerState.DISABLED:
                analyzer_cmd.extend(['--disable-issue-type', filtered_name])
            else:
                analyzer_cmd.extend(['--enable-issue-type', filtered_name])

        output_dir = Path(result_handler.workspace, "infer",
                          result_handler.buildaction_hash)
        output_dir.mkdir(exist_ok=True, parents=True)
        analyzer_cmd.extend(['-o', str(output_dir)])
        analyzer_cmd.append('--')

        cmd_filtered = []
        for cmd in shlex.split(self.buildaction.original_command):
            if IGNORED_OPTIONS_GCC.match(cmd) and \
                    self.buildaction.lang in ['c', 'c++']:
                continue
            cmd_filtered.append(cmd)

        if self.buildaction.lang == 'c++':
            cmd_filtered.append('-stdlib=libc++')

        analyzer_cmd.extend(cmd_filtered)
        LOG.debug_analyzer("Running analysis command "
                           f"'{shlex.join(analyzer_cmd)}'")

        return analyzer_cmd

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return the list of the supported checkers.
        """
        command = [cls.analyzer_binary(), "help", "--list-issue-types"]
        desc = json.load(
            open(Path(__file__).parent / "descriptions.json",
                 "r", encoding="utf-8"))
        checker_list = []
        try:
            env = analyzer_context.get_context().get_env_for_bin(
                cls.analyzer_binary())
            env.update(TZ='UTC')
            output = subprocess.check_output(command,
                                             stderr=subprocess.DEVNULL,
                                             env=env)
            for entry in output.decode().split('\n'):
                data = entry.strip().split(":")
                if len(data) < 7:
                    continue

                entry_id = data[0].lower()
                if entry_id in desc:
                    description = desc[entry_id]
                else:
                    checker = data[6] if len(data) == 7 else data[5]
                    description = f"used by '{checker}' checker"

                entry_id = entry_id.replace("_", "-")
                checker_list.append((f"infer-{entry_id}",
                                     description))
            return checker_list
        except (subprocess.CalledProcessError) as e:
            LOG.error(e.stderr)
        except (OSError) as e:
            LOG.error(e.errno)
        return []

    @classmethod
    def get_analyzer_config(cls):
        """
        Config options for infer.
        """
        return []

    @classmethod
    def get_checker_config(cls):
        """
        Config options for infer checkers.
        """
        return []

    def analyze(self, analyzer_cmd, res_handler, proc_callback=None, env=None):

        env = analyzer_context.get_context().get_env_for_bin(
            analyzer_cmd[0])
        env.update(TZ='UTC')

        result_handler = super().analyze(
            analyzer_cmd, res_handler, proc_callback, env)

        if result_handler.analyzer_returncode != 0:
            LOG.error(result_handler.analyzer_stderr)

        return result_handler

    def post_analyze(self, result_handler: InferResultHandler):
        """
        Post process the results after the analysis.
        """

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

    @classmethod
    def get_binary_version(cls, details=False) -> str:
        """
        Return the analyzer version.
        """
        # No need to LOG here, we will emit a warning later anyway.
        if not cls.analyzer_binary():
            return None
        version = [cls.analyzer_binary(), '--version']
        environ = analyzer_context.get_context().get_env_for_bin(
            cls.analyzer_binary())
        environ.update(TZ='UTC')
        try:
            output = subprocess.check_output(version,
                                             env=environ,
                                             encoding="utf-8",
                                             errors="ignore")
            output = output.split('\n', maxsplit=1)[0]
            return output.strip().split(" ")[-1][1:]
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(version))
            LOG.warning(oerr)
        return None

    @classmethod
    def is_binary_version_incompatible(cls):
        """
        Check the version compatibility of the given analyzer binary.
        """
        return None

    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = InferResultHandler(buildaction, report_output,
                                         self.config_handler.report_hash)

        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args):
        handler = InferConfigHandler()

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
