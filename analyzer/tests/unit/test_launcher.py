# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Regression tests for the package launcher."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from . import REPO_ROOT


class LauncherTest(unittest.TestCase):
    """Run the real launcher in isolated package layouts."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix='cc-launcher-')
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.launcher = self.root / 'bin' / 'CodeChecker'
        self.launcher.parent.mkdir()
        shutil.copy2(Path(REPO_ROOT) / 'bin' / 'CodeChecker', self.launcher)
        self.cli = (self.root / 'lib' / 'python3' /
                    'codechecker_common' / 'cli.py')

    def run_launcher(self, *args):
        """Use the current interpreter and capture both output streams."""
        return subprocess.run(
            [sys.executable, str(self.launcher), *args], cwd=self.root,
            capture_output=True, text=True, check=False)

    def test_unbuilt_checkout(self):
        """Missing package files produce actionable stderr."""
        result = self.run_launcher('--help')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('CodeChecker package entry point is missing:',
                      result.stderr)
        self.assertIn('make package', result.stderr)
        self.assertIn('make dev_package', result.stderr)
        self.assertIn('build/CodeChecker/bin/CodeChecker', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn("can't open file", result.stderr)
        self.assertNotIn('No such file or directory', result.stderr)

    def test_packaged_cli(self):
        """Copied and symlink layouts preserve argument forwarding."""
        self.cli.parent.mkdir(parents=True)
        source = self.root / 'cli.py'
        source.write_text('import sys\nprint(sys.argv[1:])\n',
                          encoding='utf-8')
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                if symlink:
                    self.cli.symlink_to(source)
                else:
                    shutil.copy2(source, self.cli)
                result = self.run_launcher('version', 'argument with spaces')
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout,
                                 "['version', 'argument with spaces']\n")
                self.assertEqual(result.stderr, '')
                self.cli.unlink()

    def test_unrelated_python_failure(self):
        """An existing CLI's Python errors and exit status remain visible."""
        self.cli.parent.mkdir(parents=True)
        self.cli.write_text("raise RuntimeError('unrelated failure')\n",
                            encoding='utf-8')
        result = self.run_launcher()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Traceback', result.stderr)
        self.assertIn('RuntimeError: unrelated failure', result.stderr)
        self.assertNotIn('make package', result.stderr)

    def test_existing_build(self):
        """The updated launcher runs the existing package without edits."""
        package = Path(REPO_ROOT) / 'build' / 'CodeChecker'
        if not (package / 'lib' / 'python3' /
                'codechecker_common' / 'cli.py').is_file():
            self.skipTest('No existing package available')
        os.symlink(package / 'lib', self.root / 'lib',
                   target_is_directory=True)
        os.symlink(package / 'config', self.root / 'config',
                   target_is_directory=True)
        result = self.run_launcher('version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Base package version', result.stdout + result.stderr)
