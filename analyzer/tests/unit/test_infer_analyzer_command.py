# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from codechecker_analyzer.analyzers.infer.analyzer import Infer
from codechecker_analyzer.analyzers.infer.config_handler import \
    InferConfigHandler
from codechecker_analyzer.buildlog import log_parser


class InferAnalyzerCommandTest(unittest.TestCase):
    def test_infer_runs_with_a_single_job(self):
        """
        Regression test for
        https://github.com/Ericsson/codechecker/issues/5110

        CodeChecker already runs one analyzer process per --jobs slot, but
        Infer starts its own pool of sub-processes by default, so the load
        exceeded --jobs. The command must pin Infer to a single job.
        """
        action = {
            'file': 'main.c',
            'command': 'gcc -o main main.c',
            'directory': '/'}
        build_action = log_parser.parse_options(action)

        with tempfile.TemporaryDirectory() as workspace, \
                mock.patch.object(Infer, 'analyzer_binary',
                                  return_value='infer'):
            analyzer = Infer(InferConfigHandler(), build_action)
            result_handler = SimpleNamespace(
                workspace=workspace,
                buildaction_hash='hash')

            cmd = analyzer.construct_analyzer_cmd(result_handler)

        self.assertIn('--jobs', cmd)
        self.assertEqual(cmd[cmd.index('--jobs') + 1], '1')
        # The option belongs to infer, before the '--' build command.
        self.assertLess(cmd.index('--jobs'), cmd.index('--'))
