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


def create_analyzer_sa(args=None):
    parser = argparse.ArgumentParser()
    analyze.add_arguments_to_parser(parser)
    cfg_handler = ClangSA.construct_config_handler(
        create_analyze_argparse(args))

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
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
        analyzer command by default.
        """
        analyzer = create_analyzer_sa()
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)
        self.assertNotIn('-analyzer-opt-analyze-headers', cmd)

    def test_analyze_headers_on(self):
        """
        Test that the -analyzer-opt-analyze-headers flag IS present in the
        analyzer command when requested.
        """
        analyzer = create_analyzer_sa(['--analyze-headers'])
        result_handler = create_result_handler(analyzer)
        cmd = analyzer.construct_analyzer_cmd(result_handler)
        self.assertIn('-analyzer-opt-analyze-headers', cmd)
