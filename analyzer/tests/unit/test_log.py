# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Tests for compilation database output initialization."""

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codechecker_analyzer.cli import log


class LogTest(unittest.TestCase):
    """Check output preparation before the build command is executed."""

    def test_output_paths(self):
        """Create missing parents and support existing and relative paths."""
        with tempfile.TemporaryDirectory() as workspace:
            for filename in ('build/codechecker/compile_commands.json',
                             'compile_commands.json'):
                for relative in (False, True):
                    with self.subTest(filename=filename, relative=relative):
                        # Give each case its own initially empty directory.
                        with tempfile.TemporaryDirectory(
                                dir=workspace) as root:
                            output = Path(root, filename)
                            original_cwd = os.getcwd()
                            try:
                                os.chdir(root)
                                args = argparse.Namespace(
                                    logfile=filename if relative else
                                    str(output), command='build command')
                                with patch.object(
                                    log.build_manager,
                                    'perform_build_command'
                                ) as perform_build:
                                    log.main(args)
                                    perform_build.assert_called_once_with(
                                        os.path.realpath(output),
                                        'build command', False, silent=False,
                                        verbose=None,
                                        use_absolute_ldpreload_path=False)
                                self.assertEqual(
                                    json.loads(output.read_text(
                                        encoding='utf-8')), [])
                            finally:
                                os.chdir(original_cwd)

    def test_overwrite_output(self):
        """Replace an existing compilation database before starting a build."""
        with tempfile.TemporaryDirectory() as workspace:
            output = Path(workspace, 'compile_commands.json')
            output.write_text('[{"file": "old.c"}]', encoding='utf-8')

            def check_output(*_args, **_kwargs):
                self.assertEqual(json.loads(output.read_text(
                    encoding='utf-8')), [])

            with patch.object(log.build_manager, 'perform_build_command',
                              side_effect=check_output) as perform_build:
                log.main(argparse.Namespace(logfile=str(output), command=''))
                perform_build.assert_called_once()

    def test_parent_is_file(self):
        """An invalid parent must fail without starting the build."""
        with tempfile.TemporaryDirectory() as workspace:
            parent = Path(workspace, 'build')
            parent.write_text('keep this file', encoding='utf-8')
            with patch.object(log.build_manager,
                              'perform_build_command') as perform_build:
                with self.assertRaises(OSError):
                    log.main(argparse.Namespace(
                        logfile=str(parent / 'compile_commands.json'),
                        command='build command'))
                perform_build.assert_not_called()
            self.assertEqual(parent.read_text(encoding='utf-8'),
                             'keep this file')
