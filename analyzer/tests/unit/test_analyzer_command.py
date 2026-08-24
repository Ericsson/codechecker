# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import argparse
import unittest
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.buildlog import log_parser
from codechecker_analyzer.cli import analyze
from libtest.cmd_line import create_analyze_argparse


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
