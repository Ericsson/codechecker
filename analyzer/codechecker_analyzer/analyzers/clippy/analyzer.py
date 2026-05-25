# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional

from semver.version import Version

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.buildlog.build_action import BuildAction
from codechecker_common import util
from codechecker_common.logger import get_logger

from .. import analyzer_base

from .config_handler import ClippyConfigHandler
from .result_handler import ClippyResultHandler


LOG = get_logger('analyzer.clippy')


def create_cargo_build_action(manifest_path: str) -> BuildAction:
    """
    Create a synthetic build action for Cargo-based Rust analysis.
    """
    manifest_path = os.path.abspath(manifest_path)
    project_dir = os.path.dirname(manifest_path)
    command = f'cargo clippy --message-format=json --manifest-path ' \
              f'{manifest_path}'

    return BuildAction(
        analyzer_options=[],
        compiler_includes=[],
        compiler_standard=None,
        analyzer_type='',
        original_command=command,
        directory=project_dir,
        output='',
        lang='rust',
        target='cargo',
        source=manifest_path,
        arch='',
        action_type=BuildAction.COMPILE)


class Clippy(analyzer_base.SourceAnalyzer):
    """
    Construct Cargo Clippy analyzer commands.
    """

    ANALYZER_NAME = 'clippy'

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context().analyzer_binaries[
            cls.ANALYZER_NAME]

    def add_checker_config(self, _):
        LOG.error('Checker configuration for Clippy is not implemented yet')

    def get_analyzer_mentioned_files(self, output):
        return set()

    def construct_analyzer_cmd(self, result_handler):
        config = self.config_handler

        analyzer_cmd = [
            Clippy.analyzer_binary(),
            'clippy',
            '--message-format=json',
            '--manifest-path',
            self.source_file,
        ]

        analyzer_cmd.extend(config.cargo_extra_arguments)

        if config.clippy_extra_arguments:
            analyzer_cmd.append('--')
            analyzer_cmd.extend(config.clippy_extra_arguments)

        LOG.debug_analyzer("Running analysis command '%s'",
                           ' '.join(analyzer_cmd))
        return analyzer_cmd

    def analyze(self, analyzer_cmd, res_handler, proc_callback=None, env=None):
        result_handler = super().analyze(analyzer_cmd, res_handler,
                                         proc_callback, env)

        # Compilation can fail even if Cargo emits valid diagnostics.
        # In that case, keep the diagnostics and treat analysis as successful.
        if result_handler.analyzer_returncode != 0 and \
                self.__has_compiler_message(result_handler.analyzer_stdout):

            LOG.debug(
                'Cargo exited with %d, but emitted parseable diagnostics. '
                'Treating Clippy analysis as successful.',
                result_handler.analyzer_returncode,
            )
            result_handler.analyzer_returncode = 0

        return result_handler

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return representative Clippy and rustc checker groups.

        Clippy's complete lint list is toolchain-dependent and large. This
        integration exposes stable groups and records the exact emitted
        diagnostic code on each report.
        """
        return [
            ('clippy', 'Clippy lint diagnostics'),
            ('rustc', 'Rust compiler diagnostics')
        ]

    @classmethod
    def get_analyzer_config(cls) -> List[analyzer_base.AnalyzerConfig]:
        return [
            analyzer_base.AnalyzerConfig(
                'cargo-args-file',
                'A file path containing flags that are forwarded to cargo '
                'clippy before "--". E.g.: cargo-args-file=<filepath>',
                util.ExistingPath,
            ),
            analyzer_base.AnalyzerConfig(
                'cc-verbatim-args-file',
                'A file path containing flags forwarded verbatim to '
                'Clippy after "--". E.g.: cc-verbatim-args-file=<filepath>',
                util.ExistingPath,
            ),
        ]

    def post_analyze(self, result_handler: ClippyResultHandler):
        """
        Run immediately after the analysis.
        """

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        return shutil.which(configured_binary, path=environ.get('PATH'))

    @classmethod
    def get_binary_version(cls) -> Optional[Version]:
        if not cls.analyzer_binary():
            return None

        environ = analyzer_context.get_context().get_env_for_bin(
            cls.analyzer_binary())

        try:
            output = subprocess.check_output(
                [cls.analyzer_binary(), 'clippy', '--version'],
                env=environ,
                encoding='utf-8',
                errors='ignore',
            )
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning(
                'Failed to get analyzer version: %s clippy --version',
                cls.analyzer_binary()
            )
            LOG.warning(oerr)
            return None

        version_match = re.search(r'(\d+\.\d+\.\d+)', output)
        if version_match:
            return Version.parse(version_match.group(1))

        return None

    @classmethod
    def is_binary_version_incompatible(cls):
        if cls.get_binary_version() is None:
            return 'Cargo Clippy is unavailable or has an unsupported version.'

        return None

    def construct_result_handler(
        self,
        buildaction,
        report_output,
        skiplist_handler
    ):
        res_handler = ClippyResultHandler(
            buildaction, report_output, self.config_handler.report_hash
        )
        res_handler.skiplist_handler = skiplist_handler
        res_handler.check_states = self.config_handler.checks()
        return res_handler

    @classmethod
    def construct_config_handler(cls, args):
        handler = ClippyConfigHandler()

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer != cls.ANALYZER_NAME:
                    continue

                try:
                    if cfg.option == 'cargo-args-file':
                        handler.cargo_extra_arguments = \
                            util.load_args_from_file(cfg.value)
                    elif cfg.option == 'cc-verbatim-args-file':
                        handler.clippy_extra_arguments = \
                            util.load_args_from_file(cfg.value)
                except FileNotFoundError:
                    LOG.error('File not found: %s', cfg.value)
                    sys.exit(1)

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug('No checkers were defined in the command line for %s',
                      cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            cls.get_analyzer_checkers(), cmdline_checkers,
            'enable_all' in args and args.enable_all
        )

        return handler

    def __has_compiler_message(self, stdout: str) -> bool:
        return '"reason":"compiler-message"' in stdout or \
            '"reason": "compiler-message"' in stdout


def find_cargo_manifest(path: str) -> Optional[str]:
    """
    Return the input path if it is a direct Cargo manifest.
    """
    if os.path.isfile(path) and os.path.basename(path) == 'Cargo.toml':
        return path

    return None
