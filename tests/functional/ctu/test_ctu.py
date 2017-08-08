#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" CTU function test."""
import glob
import json
import os
import shutil
import subprocess
import unittest

from libtest import env

NO_CTU_MESSAGE = 'CTU is not supported'


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
        raw_buildlog = os.path.join(self.test_dir, 'buildlog.json')
        with open(raw_buildlog) as log_file:
            build_json = json.load(log_file)
            for command in build_json:
                command['directory'] = self.test_dir
        self.ctu_capable = self.__is_ctu_capable()
        os.chdir(self.test_workspace)
        self.buildlog = os.path.join(self.test_workspace, 'buildlog.json')
        with open(self.buildlog, 'w') as log_file:
            json.dump(build_json, log_file)

    def tearDown(self):
        """ Tear down workspace."""

        shutil.rmtree(self.report_dir, ignore_errors=True)

    def test_help(self):
        """ Test if help is given on CTU detected. """

        cmd = [self._codechecker_cmd, 'analyze', '-h']
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         cwd=self.test_dir, env=self.env)
        ctu_in_output_idx = output.find('--ctu-')
        if self.ctu_capable:
            self.assertGreater(ctu_in_output_idx, -1)
        else:
            self.assertEqual(ctu_in_output_idx, -1)

    def test_ctu_all_no_reparse(self):
        """ Test full CTU without reparse. """

        self.__test_ctu_all(False)

    def test_ctu_collect_no_reparse(self):
        """ Test CTU collect phase without reparse. """

        self.__test_ctu_collect(False)

    def test_ctu_analyze_no_reparse(self):
        """ Test CTU analyze phase without reparse. """

        self.__test_ctu_analyze(False)

    def test_ctu_all_reparse(self):
        """ Test full CTU with reparse. """

        self.__test_ctu_all(True)

    def test_ctu_collect_reparse(self):
        """ Test CTU collect phase with reparse. """

        self.__test_ctu_collect(True)

    def test_ctu_analyze_reparse(self):
        """ Test CTU analyze phase with reparse. """

        self.__test_ctu_analyze(True)

    def __test_ctu_all(self, reparse):
        """ Test full CTU. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        output = self.__do_ctu_all(reparse)
        self.__check_ctu_analyze(output)

    def __test_ctu_collect(self, reparse):
        """ Test CTU collect phase. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        self.__do_ctu_collect(reparse)
        self.__check_ctu_collect(reparse)

    def __test_ctu_analyze(self, reparse):
        """ Test CTU analyze phase. """

        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        self.__do_ctu_collect(reparse)
        output = self.__do_ctu_analyze(reparse)
        self.__check_ctu_analyze(output)

    def __do_ctu_all(self, reparse):
        """ Execute a full CTU run. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-all']
        if reparse:
            cmd.append('--ctu-on-the-fly')
        cmd.append(self.buildlog)
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         cwd=self.test_dir, env=self.env)
        return output

    def __do_ctu_collect(self, reparse):
        """ Execute CTU collect phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-collect']
        if reparse:
            cmd.append('--ctu-on-the-fly')
        cmd.append(self.buildlog)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                cwd=self.test_dir, env=self.env)

    def __check_ctu_collect(self, reparse):
        """ Check artifacts of CTU collect phase. """

        ctu_dir = os.path.join(self.report_dir, 'ctu-dir')
        self.assertTrue(os.path.isdir(ctu_dir))
        for arch in glob.glob(os.path.join(ctu_dir, '*')):
            fn_map_file = os.path.join(ctu_dir, arch, 'externalFnMap.txt')
            self.assertTrue(os.path.isfile(fn_map_file))
            if not reparse:
                ast_dir = os.path.join(ctu_dir, arch, 'ast')
                self.assertTrue(os.path.isdir(ast_dir))

    def __do_ctu_analyze(self, reparse):
        """ Execute CTU analyze phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-analyze']
        if reparse:
            cmd.append('--ctu-on-the-fly')
        cmd.append(self.buildlog)
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         cwd=self.test_dir, env=self.env)
        return output

    def __check_ctu_analyze(self, output):
        """ Check artifacts of CTU analyze phase. """

        self.assertEqual(output.find('Failed to analyze'), -1)
        self.assertGreater(output.find('analyzed lib.c successfully'), -1)
        self.assertGreater(output.find('analyzed main.c successfully'), -1)

        cmd = [self._codechecker_cmd, 'parse', self.report_dir]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         cwd=self.test_dir, env=self.env)
        self.assertGreater(output.find('no defects while analyzing lib.c'), -1)
        self.assertGreater(output.find('defect(s) while analyzing main.c'), -1)
        self.assertGreater(output.find('lib.c:3:'), -1)
        self.assertGreater(output.find('[core.NullDereference]'), -1)

    def __is_ctu_capable(self):
        """ Detects CTU capability in current env. """

        ctu_capable = True
        try:
            subprocess.check_output(['clang-func-mapping', '-version'],
                                    stderr=subprocess.STDOUT,
                                    cwd=self.test_dir)
        except (OSError, subprocess.CalledProcessError):
            ctu_capable = False
        return ctu_capable
