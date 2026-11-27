# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Tests for the GCC result handler helpers.
"""
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from codechecker_analyzer.analyzers.gcc.result_handler import \
    GccResultHandler, strip_sarif_preamble


class GccSarifPreambleTest(unittest.TestCase):
    """
    cc1 may print text diagnostics before the SARIF document on stderr.
    """

    SARIF = '{"version": "2.1.0", "runs": []}\n'

    def test_text_before_sarif_is_dropped(self):
        stderr = "cc1: warning: command-line option '-Waliasing' is valid " \
                 "for Fortran but not for C\n" + self.SARIF
        self.assertEqual(
            json.loads(strip_sarif_preamble(stderr)),
            {"version": "2.1.0", "runs": []})

    def test_plain_sarif_is_unchanged(self):
        self.assertEqual(strip_sarif_preamble(self.SARIF), self.SARIF)


class GccPostprocessPreambleTest(unittest.TestCase):
    """
    The full postprocess_result path must still find the reports when cc1
    printed a text warning before the SARIF document.
    """

    SARIF_DIR = os.path.join(
        os.environ.get('REPO_ROOT', ''), 'tools', 'report-converter',
        'tests', 'unit', 'analyzers', 'gcc_output_test_files')

    def setUp(self):
        self.workspace = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_reports_found_after_text_preamble(self):
        with open(os.path.join(self.SARIF_DIR, 'double_free.cpp.sarif'),
                  encoding='utf-8') as f:
            sarif = f.read()
        stderr = "cc1: warning: command-line option '-Waliasing' is valid " \
                 "for Fortran but not for C\n" + sarif

        action = SimpleNamespace(
            source='double_free.cpp', directory=self.SARIF_DIR,
            original_command='gcc -c double_free.cpp', analyzer_type='gcc')
        context = SimpleNamespace(checker_labels=None)
        with mock.patch('codechecker_analyzer.analyzers.'
                        'result_handler_base.analyzer_context.get_context',
                        return_value=context):
            handler = GccResultHandler(action, self.workspace)
        handler.analyzer_stderr = stderr
        handler.analyzer_returncode = 0

        captured = []

        def fake_create(_file, reports, *_args, **_kwargs):
            captured.extend(reports)

        with mock.patch('codechecker_analyzer.analyzers.gcc.'
                        'result_handler.report_file.create', fake_create), \
                mock.patch('codechecker_analyzer.analyzers.gcc.'
                           'result_handler.error_file.update'):
            handler.postprocess_result(None, None)

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].checker_name, 'gcc-analyzer-double-free')
