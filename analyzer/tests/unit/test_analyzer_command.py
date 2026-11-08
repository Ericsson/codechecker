# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import argparse
import json
import os
import shlex
import shutil
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest import mock

from codechecker_analyzer import analysis_manager
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.buildlog import log_parser
from codechecker_analyzer.cli import analyze
from libtest.cmd_line import create_analyze_argparse
from tu_collector import tu_collector


def create_analyzer_sa(args=None, command="g++ -o main main.cpp"):
    parser = argparse.ArgumentParser()
    analyze.add_arguments_to_parser(parser)
    cfg_handler = ClangSA.construct_config_handler(
        create_analyze_argparse(args))

    action = {
        'file': 'main.cpp',
        'command': command,
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    return ClangSA(cfg_handler, build_action)


def create_result_handler(analyzer):
    """
    Create result handler for construct_analyzer_cmd call.
    """

    build_action = analyzer.buildaction

    rh = analyzer.construct_result_handler(
        build_action,
        build_action.directory,
        None)

    rh.analyzed_source_file = build_action.source

    return rh


class AnalyzerCommandClangSATest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('gcc') and shutil.which('clang'),
                         'GCC and Clang are required')
    def test_reproducer_filters_gcc_only_flag_for_clang_dependencies(self):
        """Issue #3161: use transformed Clang options to collect headers."""
        with tempfile.TemporaryDirectory() as build_dir:
            source = os.path.join(build_dir, 'source.c')
            include_dir = os.path.join(build_dir, 'include')
            os.mkdir(include_dir)
            clang_header = os.path.join(include_dir, 'clang_only.h')
            with open(source, 'w', encoding='utf-8') as output:
                output.write('#if defined(__GNUC__) && !defined(__clang__)\n'
                             '#include "gcc_only.h"\n'
                             '#endif\n'
                             '#ifdef __clang__\n'
                             '#include "clang_only.h"\n'
                             '#endif\n')
            with open(os.path.join(include_dir, 'gcc_only.h'), 'w',
                      encoding='utf-8') as output:
                output.write('/* GCC-only header. */\n')
            with open(clang_header, 'w', encoding='utf-8') as output:
                output.write('/* Clang-only header. */\n')

            gcc_command = (f"{shlex.quote(shutil.which('gcc'))} "
                           '-fno-var-tracking-assignments '
                           '-DTEST_DEFINE=1 -Iinclude -std=gnu11 '
                           '-c source.c')
            entry = {'file': 'source.c', 'command': gcc_command,
                     'directory': build_dir}
            with mock.patch.object(log_parser.ImplicitCompilerInfo, 'set'):
                action = log_parser.parse_options(entry)
            self.assertEqual(action.original_command, gcc_command)
            self.assertNotIn('-fno-var-tracking-assignments',
                             action.analyzer_options)

            clang = shutil.which('clang')
            analyzer = mock.Mock(spec=ClangSA)
            analyzer.config_handler = SimpleNamespace(
                analyzer_extra_arguments=[],
                add_gcc_include_dirs_with_isystem=False)
            analyzer.get_analyzer_mentioned_files.return_value = set()
            result = SimpleNamespace(
                buildaction=action, analyzer_stdout='', analyzer_stderr='',
                analyzer_cmd=[clang], analyzer_returncode=1,
                workspace=build_dir)
            archive_path = os.path.join(build_dir, 'reproducer.zip')
            check_output = tu_collector.subprocess.check_output
            scanned_commands = []

            def bounded_check_output(command, **kwargs):
                scanned_commands.append(command)
                kwargs['timeout'] = 10
                return check_output(command, **kwargs)

            with mock.patch.object(ClangSA, 'analyzer_binary',
                                   return_value=clang), \
                    mock.patch.object(tu_collector.subprocess, 'check_output',
                                      side_effect=bounded_check_output):
                analysis_manager.handle_reproducer(
                    analyzer, result, archive_path, {})

            with zipfile.ZipFile(archive_path) as archive:
                archived_files = archive.namelist()
                self.assertEqual(archive.read('build-action').decode(),
                                 gcc_command)
                stored_command = json.loads(archive.read(
                    'compilation_database.json'))[0]['command']

            self.assertEqual(stored_command, gcc_command)
            self.assertIn(os.path.join('sources-root',
                                       clang_header.lstrip(os.sep)),
                          archived_files)
            self.assertNotIn('no-sources', archived_files)
            self.assertEqual(len(scanned_commands), 1)
            self.assertEqual(scanned_commands[0][0], clang)
            self.assertNotIn('-fno-var-tracking-assignments',
                             scanned_commands[0])

    def test_isystem_idirafter(self):
        """
        Test that the implicit include paths are added to the analyzer command
        with -idirafter.
        """
        analyzer = create_analyzer_sa(['--add-gcc-include-dirs-with-isystem'])

        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)
        self.assertIn('-isystem', cmd)

        analyzer = create_analyzer_sa()

        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)
        self.assertIn('-idirafter', cmd)

    def test_no_analyze_headers(self):
        """
        Test that the -analyzer-opt-analyze-headers flag is NOT present in the
        analyzer command.
        """
        analyzer = create_analyzer_sa()
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)
        self.assertNotIn('-analyzer-opt-analyze-headers', cmd)

    def test_no_duplicate_target_flag(self):
        """
        Regression test for
        https://github.com/Ericsson/codechecker/issues/1158

        When the original build command already specifies a target with
        the double-dash spelling (--target=...), an implicit fallback
        target (from querying the compiler's own default) must not also
        be appended - the analyzer command should contain the user's
        target flag exactly once, not a wrong/default one alongside it.
        """
        analyzer = create_analyzer_sa(
            command="g++ --target=aarch64-linux-gnu -o main main.cpp")
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)

        target_flags = [
            x for x in cmd if x.startswith(('-target', '--target'))]
        self.assertEqual(target_flags, ['--target=aarch64-linux-gnu'])

    def test_implicit_target_flag_still_added_when_missing(self):
        """
        Sanity check accompanying the regression test above: when the
        original build command has no target flag at all, the implicit
        default target should still be added exactly once.
        """
        analyzer = create_analyzer_sa(command="g++ -o main main.cpp")
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)

        target_flags = [
            x for x in cmd if x.startswith(('-target', '--target'))]
        self.assertEqual(len(target_flags), 1)

    def test_no_duplicate_std_flag_double_dash(self):
        """
        Regression test for
        https://github.com/Ericsson/codechecker/issues/4926

        When the original build command already specifies a standard
        version with the double-dash spelling (--std=...), the implicit
        default standard must not also be appended - the analyzer command
        should contain the user's flag exactly once, with no implicit
        '-std=...' added alongside it.
        """
        analyzer = create_analyzer_sa(
            command="g++ --std=c++23 -o main main.cpp")
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)

        std_flags = [x for x in cmd if x.startswith(('-std=', '--std='))]
        self.assertEqual(std_flags, ['--std=c++23'])

    def test_implicit_std_flag_still_added_when_missing(self):
        """
        Sanity check accompanying the regression test above: when the
        original build command has no standard-version flag at all, the
        implicit default standard should still be added exactly once.
        """
        analyzer = create_analyzer_sa(command="g++ -o main main.cpp")
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)

        std_flags = [x for x in cmd if x.startswith(('-std=', '--std='))]
        self.assertEqual(len(std_flags), 1)
