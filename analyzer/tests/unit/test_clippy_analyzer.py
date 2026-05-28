# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test Clippy analyzer helpers.
"""

import os
import tempfile
import unittest
from unittest import mock

from codechecker_analyzer.analyzers import analyzer_base, analyzer_types
from codechecker_analyzer.analyzers.clippy.analyzer import \
    Clippy, create_cargo_build_action, find_cargo_manifest
from codechecker_analyzer.analyzers.config_handler import CheckerState
from codechecker_analyzer.arg import AnalyzerConfigArg
from codechecker_common.checker_labels import CheckerLabels


class Args(dict):
    """
    Test helper which behaves like CodeChecker's argparse namespace.
    """

    def __getattr__(self, attr):
        return self[attr]


class ClippyAnalyzerTest(unittest.TestCase):
    """
    Test Cargo manifest input handling.
    """

    def test_find_cargo_manifest_accepts_manifest_file(self):
        """
        Cargo analysis accepts direct Cargo.toml input.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            with open(manifest, 'w', encoding='utf-8') as cargo_toml:
                cargo_toml.write('[package]\nname = "sample"\n')

            self.assertEqual(find_cargo_manifest(manifest), manifest)

    def test_find_cargo_manifest_rejects_directory(self):
        """
        Cargo analysis does not consume directories implicitly.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            with open(manifest, 'w', encoding='utf-8') as cargo_toml:
                cargo_toml.write('[package]\nname = "sample"\n')

            self.assertIsNone(find_cargo_manifest(tmp_dir))

    def test_compile_command_analyzers_exclude_clippy(self):
        """
        Compile command analysis does not select Clippy by default.
        """
        self.assertNotIn(
            Clippy.ANALYZER_NAME,
            analyzer_types.compile_command_analyzers)

    def test_get_analyzers_for_compile_commands_selects_cargo_analyzers(self):
        """
        Cargo manifest commands select Clippy for status handling.
        """
        analyzers = analyzer_types.get_analyzers_for_compile_commands([{
            'file': '/sample/Cargo.toml',
            'directory': '/sample',
            'command': 'cargo clippy --manifest-path Cargo.toml'
        }])

        self.assertEqual(analyzers, analyzer_types.cargo_manifest_analyzers)

    def test_get_analyzers_for_compile_commands_selects_c_analyzers(self):
        """
        C/C++ compile commands select compile-command analyzers.
        """
        analyzers = analyzer_types.get_analyzers_for_compile_commands([{
            'file': '/sample/main.c',
            'directory': '/sample',
            'command': 'gcc -c main.c'
        }])

        self.assertEqual(analyzers, analyzer_types.compile_command_analyzers)

    def test_construct_analyzer_cmd_orders_cargo_and_clippy_args(self):
        """
        Cargo arguments are placed before Clippy verbatim arguments.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [],
                'ordered_checkers': [],
                'enable_all': False
            }))
            handler.cargo_extra_arguments = ['--workspace', '--all-targets']
            handler.clippy_extra_arguments = [
                '-W', 'clippy::pedantic',
                '-A', 'clippy::too_many_arguments']

            analyzer = Clippy(handler, create_cargo_build_action(manifest))
            analyzer.source_file = manifest

            with mock.patch.object(
                    Clippy, 'analyzer_binary', return_value='cargo'):
                cmd = analyzer.construct_analyzer_cmd(None)

            self.assertEqual(cmd, [
                'cargo',
                'clippy',
                '--message-format=json',
                '--manifest-path',
                manifest,
                '--workspace',
                '--all-targets',
                '--',
                '-W',
                'clippy::pedantic',
                '-A',
                'clippy::too_many_arguments'])

    def test_construct_analyzer_cmd_omits_separator_without_clippy_args(self):
        """
        Cargo command does not contain '--' unless Clippy args are present.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [],
                'ordered_checkers': [],
                'enable_all': False
            }))
            analyzer = Clippy(handler, create_cargo_build_action(manifest))
            analyzer.source_file = manifest

            with mock.patch.object(
                    Clippy, 'analyzer_binary', return_value='cargo'):
                cmd = analyzer.construct_analyzer_cmd(None)

            self.assertNotIn('--', cmd)

    def test_construct_config_handler_loads_argument_files(self):
        """
        Analyzer config files populate Cargo and Clippy argument lists.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cargo_args = os.path.join(tmp_dir, 'cargo-args.txt')
            clippy_args = os.path.join(tmp_dir, 'clippy-args.txt')

            with open(cargo_args, 'w', encoding='utf-8') as args_file:
                args_file.write('--features type-error --all-targets')
            with open(clippy_args, 'w', encoding='utf-8') as args_file:
                args_file.write('-W clippy::pedantic')

            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [
                    AnalyzerConfigArg(
                        'clippy', 'cargo-args-file', cargo_args),
                    AnalyzerConfigArg(
                        'clippy', 'cc-verbatim-args-file', clippy_args),
                    AnalyzerConfigArg(
                        'clang-tidy', 'cc-verbatim-args-file', clippy_args)
                ],
                'ordered_checkers': [],
                'enable_all': False
            }))

            self.assertEqual(handler.cargo_extra_arguments, [
                '--features',
                'type-error',
                '--all-targets'])
            self.assertEqual(handler.clippy_extra_arguments, [
                '-W',
                'clippy::pedantic'])

    def test_construct_result_handler_keeps_checker_states(self):
        """
        Result handler receives group checker state for report filtering.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [],
                'ordered_checkers': [
                    ('checker:clippy', True),
                    ('checker:rustc', False)
                ],
                'enable_all': False
            }))
            analyzer = Clippy(handler, create_cargo_build_action(manifest))

            result_handler = analyzer.construct_result_handler(
                analyzer.buildaction, tmp_dir, None)

            self.assertEqual(
                result_handler.check_states['rustc'][0],
                CheckerState.DISABLED)
            self.assertEqual(
                result_handler.check_states['clippy'][0],
                CheckerState.ENABLED)

    def test_analyze_accepts_nonzero_returncode_with_json_diagnostics(self):
        """
        Cargo build errors are accepted when JSON diagnostics were emitted.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [],
                'ordered_checkers': [],
                'enable_all': False
            }))
            analyzer = Clippy(handler, create_cargo_build_action(manifest))
            result_handler = analyzer.construct_result_handler(
                analyzer.buildaction, tmp_dir, None)
            result_handler.analyzer_returncode = 101
            result_handler.analyzer_stdout = '{"reason":"compiler-message"}'

            with mock.patch.object(
                    analyzer_base.SourceAnalyzer, 'analyze',
                    return_value=result_handler):
                analyzer.analyze([], result_handler)

            self.assertEqual(result_handler.analyzer_returncode, 0)

    def test_analyze_keeps_nonzero_returncode_without_json_diagnostics(self):
        """
        Cargo infrastructure errors remain analyzer failures.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = os.path.join(tmp_dir, 'Cargo.toml')
            handler = Clippy.construct_config_handler(Args({
                'analyzer_config': [],
                'ordered_checkers': [],
                'enable_all': False
            }))
            analyzer = Clippy(handler, create_cargo_build_action(manifest))
            result_handler = analyzer.construct_result_handler(
                analyzer.buildaction, tmp_dir, None)
            result_handler.analyzer_returncode = 101
            result_handler.analyzer_stdout = 'cargo failed before analysis'

            with mock.patch.object(
                    analyzer_base.SourceAnalyzer, 'analyze',
                    return_value=result_handler):
                analyzer.analyze([], result_handler)

            self.assertEqual(result_handler.analyzer_returncode, 101)

    def test_checker_labels_cover_dynamic_diagnostics(self):
        """
        Clippy labels classify dynamic Clippy and rustc checker names.
        """
        labels = CheckerLabels(os.path.join(
            os.environ['REPO_ROOT'], 'config', 'labels'))

        self.assertEqual(
            labels.severity('clippy-bind-instead-of-map', 'clippy'),
            'LOW')
        self.assertEqual(
            labels.severity('rustc-unused-variables', 'clippy'),
            'LOW')
        self.assertEqual(
            labels.severity('rustc-E0308', 'clippy'),
            'CRITICAL')


if __name__ == '__main__':
    unittest.main()
