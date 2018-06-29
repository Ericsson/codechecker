#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
""" CTU function test."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import glob
import json
import os
import shutil
import unittest

from libtest import env
from libtest.codechecker import call_command

NO_CTU_MESSAGE = "CTU is not supported"


class TestCtu(unittest.TestCase):
    """ Test CTU functionality. """

    def setUp(self):
        """ Set up workspace."""

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.env = env.codechecker_env()
        self.report_dir = os.path.join(self.test_workspace, 'reports')
        os.makedirs(self.report_dir)
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')

        # Get if clang is CTU-capable or not.
        cmd = [self._codechecker_cmd, 'analyze', '-h']
        output, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        self.ctu_capable = '--ctu-' in output
        print("'analyze' reported CTU-compatibility? " + str(self.ctu_capable))

        # Fix the "template" build JSONs to contain a proper directory
        # so the tests work.
        raw_buildlog = os.path.join(self.test_dir, 'buildlog.json')
        with open(raw_buildlog) as log_file:
            build_json = json.load(log_file)
            for command in build_json:
                command['directory'] = self.test_dir

        self.__old_pwd = os.getcwd()
        os.chdir(self.test_workspace)
        self.buildlog = os.path.join(self.test_workspace, 'buildlog.json')
        with open(self.buildlog, 'w') as log_file:
            json.dump(build_json, log_file)

    def tearDown(self):
        """ Tear down workspace."""

        shutil.rmtree(self.report_dir, ignore_errors=True)
        os.chdir(self.__old_pwd)

    def test_ctu_all_no_reparse(self):
        """ Test full CTU without reparse. """

        self.__test_ctu_all()

    def test_ctu_collect_no_reparse(self):
        """ Test CTU collect phase without reparse. """

        self.__test_ctu_collect()

    def test_ctu_analyze_no_reparse(self):
        """ Test CTU analyze phase without reparse. """

        self.__test_ctu_analyze()

    def __test_ctu_all(self):
        """ Test full CTU. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        output = self.__do_ctu_all()
        self.__check_ctu_analyze(output)

    def __test_ctu_collect(self):
        """ Test CTU collect phase. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        self.__do_ctu_collect()
        self.__check_ctu_collect()

    def __test_ctu_analyze(self):
        """ Test CTU analyze phase. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        self.__do_ctu_collect()
        output = self.__do_ctu_analyze()
        self.__check_ctu_analyze(output)

    def __do_ctu_all(self):
        """ Execute a full CTU run. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-all']
        cmd.append(self.buildlog)
        out, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        return out

    def __do_ctu_collect(self):
        """ Execute CTU collect phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-collect']
        cmd.append(self.buildlog)
        call_command(cmd, cwd=self.test_dir, env=self.env)

    def __check_ctu_collect(self):
        """ Check artifacts of CTU collect phase. """

        ctu_dir = os.path.join(self.report_dir, 'ctu-dir')
        self.assertTrue(os.path.isdir(ctu_dir))
        for arch in glob.glob(os.path.join(ctu_dir, '*')):
            fn_map_file = os.path.join(ctu_dir, arch, 'externalFnMap.txt')
            self.assertTrue(os.path.isfile(fn_map_file))

    def __do_ctu_analyze(self):
        """ Execute CTU analyze phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-analyze']
        cmd.append(self.buildlog)
        out, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        return out

    def __check_ctu_analyze(self, output):
        """ Check artifacts of CTU analyze phase. """

        self.assertNotIn("Failed to analyze", output)
        self.assertIn("analyzed lib.c successfully", output)
        self.assertIn("analyzed main.c successfully", output)

        cmd = [self._codechecker_cmd, 'parse', self.report_dir]
        output, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        self.assertIn("no defects while analyzing lib.c", output)
        self.assertIn("defect(s) while analyzing main.c", output)
        self.assertIn("lib.c:3:", output)
        self.assertIn("[core.NullDereference]", output)
