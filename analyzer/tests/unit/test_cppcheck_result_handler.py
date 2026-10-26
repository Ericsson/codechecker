# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test the post processing of Cppcheck reports.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from codechecker_report_converter.report import BugPathEvent, File, Range, \
    Report, report_file

from codechecker_analyzer.analyzers.cppcheck.result_handler import \
    CppcheckResultHandler


class BuildAction:
    analyzer_type = 'cppcheck'
    original_command = 'g++ main.cpp'
    source = 'main.cpp'

    def __init__(self, directory):
        self.directory = directory


class CppcheckResultHandlerTest(unittest.TestCase):
    """
    Test which Cppcheck reports are kept by the result handler.
    """

    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.source_file = os.path.join(self.workspace, 'main.cpp')
        with open(self.source_file, 'w', encoding='utf-8') as source:
            source.write('int main() {}\n')

    def tearDown(self):
        shutil.rmtree(self.workspace)

    def __postprocess(self, analyzer_config):
        """
        Run the result handler on reports from a regular checker, an addon and
        an informative diagnostic, and return the checker names it keeps.
        """
        with mock.patch('codechecker_analyzer.analyzers.result_handler_base.'
                        'analyzer_context'):
            handler = CppcheckResultHandler(
                BuildAction(self.workspace), self.workspace)

        handler.analyzer = mock.Mock()
        handler.analyzer.get_analyzer_checkers.return_value = \
            [('cppcheck-uninitvar', '')]
        handler.analyzer.config_handler.analyzer_config = analyzer_config

        source = File(self.source_file)
        reports = [
            Report(source, 1, 1, 'message', checker_name,
                   report_hash='hash', analyzer_name='cppcheck',
                   category='unknown', type='unknown',
                   bug_path_events=[BugPathEvent(
                       'message', source, 1, 1, Range(1, 1, 1, 1))])
            for checker_name in ('uninitvar', 'misra-c2012-8.4',
                                 'normalCheckLevelMaxBranches')]
        report_file.create(
            handler.analyzer_result_file, reports, None,
            handler.analyzer_info)

        handler.postprocess_result(None, None)

        return sorted(
            report.checker_name for report in report_file.get_reports(
                handler.analyzer_result_file))

    def test_addon_reports_are_kept(self):
        """
        Reports of an enabled addon are not dropped, only the informative
        diagnostics are.
        """
        for addon in ('misra.py', '/path/to/misra.json', 'misra'):
            with self.subTest(addon=addon):
                self.assertEqual(
                    self.__postprocess({'addons': [addon]}),
                    ['cppcheck-misra-c2012-8.4', 'cppcheck-uninitvar'])

    def test_addon_reports_are_dropped_without_the_addon(self):
        """
        Without a configured addon only the reports of the checkers Cppcheck
        lists are kept.
        """
        self.assertEqual(
            self.__postprocess({}), ['cppcheck-uninitvar'])
        self.assertEqual(
            self.__postprocess({'addons': ['threadsafety.py']}),
            ['cppcheck-uninitvar'])
