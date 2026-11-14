# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Regression tests for Clang help subprocesses."""

import os
import subprocess
import sys
import unittest
from unittest import mock

from codechecker_analyzer.analyzers.clangsa import analyzer


class ClangsaHelpTest(unittest.TestCase):
    """Help queries must not wait for input from the caller."""

    def test_checker_help_does_not_wait_for_stdin(self):
        """Issue #2670: Clang without its analyzer waits for stdin EOF."""
        command = [sys.executable, '-c', 'import sys; sys.stdin.read()']
        check_output = subprocess.check_output
        read_fd, write_fd = os.pipe()

        # Keep the writer open and empty throughout discovery. This simulates
        # inherited stdin even when pytest itself runs with stdin closed.
        with os.fdopen(read_fd, 'rb') as reader, \
                os.fdopen(write_fd, 'wb'):
            def bounded_check_output(cmd, **kwargs):
                # Supply the simulated inherited stream only when the helper
                # has not explicitly redirected stdin or supplied input.
                if 'input' not in kwargs:
                    kwargs.setdefault('stdin', reader)
                # check_output kills and reaps the child on timeout.
                kwargs['timeout'] = 3
                return check_output(cmd, **kwargs)

            with mock.patch.object(analyzer.analyzer_context,
                                   'get_context') as get_context, \
                    mock.patch.object(analyzer.subprocess, 'check_output',
                                      side_effect=bounded_check_output):
                get_context.return_value.get_env_for_bin.return_value = None
                try:
                    checkers = analyzer.parse_clang_help_page(
                        command, 'CHECKERS:')
                except subprocess.TimeoutExpired:
                    self.fail('Checker discovery waited for stdin instead '
                              'of supplying EOF (issue #2670).')

        self.assertEqual(checkers, [])
