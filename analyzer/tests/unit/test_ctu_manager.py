# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for the CTU collect phase helpers."""


import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from codechecker_analyzer.analyzers.clangsa import ctu_manager


class CtuCollectFailureTest(unittest.TestCase):
    """The CTU collect steps report their failures to the caller."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.action = SimpleNamespace(directory=self.tmp_dir.name)
        self.config = SimpleNamespace(ctu_dir=self.tmp_dir.name,
                                      ctu_on_demand=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def __map_functions(self, script):
        cmd = ['sh', '-c', script]
        with mock.patch.object(ctu_manager, 'get_extdef_mapping_cmd',
                               return_value=cmd):
            return ctu_manager.map_functions('x86_64', self.action, 'main.c',
                                             self.config, 'unused',
                                             'tmpExternalFnMaps')

    def test_map_functions_failure_is_returned(self):
        failure = self.__map_functions('echo out; echo crashed >&2; exit 3')

        self.assertIsNotNone(failure)
        self.assertEqual(failure['step'], 'extdef_mapping')
        self.assertEqual(failure['returncode'], 3)
        self.assertEqual(failure['cmd'][0], 'sh')
        self.assertIn('out', failure['stdout'])
        self.assertIn('crashed', failure['stderr'])

    def test_map_functions_success_returns_none(self):
        failure = self.__map_functions('echo "c:@F@main /src/main.c"')

        self.assertIsNone(failure)
        fnmap_dir = os.path.join(self.tmp_dir.name, 'x86_64',
                                 'tmpExternalFnMaps')
        self.assertEqual(len(os.listdir(fnmap_dir)), 1)

    def test_generate_ast_failure_is_returned(self):
        cmd = ['sh', '-c', 'echo crashed >&2; exit 254']
        ast_dir = os.path.join(self.tmp_dir.name, 'ast')
        with mock.patch.object(ctu_manager, 'generate_ast_cmd',
                               return_value=(cmd, ast_dir)):
            failure = ctu_manager.generate_ast('x86_64', self.action,
                                               'main.c', self.config)

        self.assertIsNotNone(failure)
        self.assertEqual(failure['step'], 'ast_dump')
        self.assertEqual(failure['returncode'], 254)
        self.assertIn('crashed', failure['stderr'])
