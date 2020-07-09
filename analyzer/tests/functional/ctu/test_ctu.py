#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" CTU function test."""


import glob
import json
import os
import shutil
import unittest

from libtest import env
from libtest.codechecker import call_command

NO_CTU_MESSAGE = "CTU is not supported"
NO_CTU_ON_DEMAND_MESSAGE = "CTU-on-demand is not supported"


def makeSkipUnlessAttributeFound(attribute, message):
    def deco(f):
        def wrapper(self, *args, **kwargs):
            if not getattr(self, attribute):
                self.skipTest(message)
            else:
                f(self, *args, **kwargs)
        return wrapper
    return deco


skipUnlessCTUCapable = makeSkipUnlessAttributeFound(
    'ctu_capable', NO_CTU_MESSAGE)
skipUnlessCTUOnDemandCapable = makeSkipUnlessAttributeFound(
    'ctu_on_demand_capable', NO_CTU_ON_DEMAND_MESSAGE)


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

        self.ctu_on_demand_capable = '--ctu-ast-mode' in output
        print("'analyze' reported CTU-on-demand-compatibility? "
              + str(self.ctu_on_demand_capable))

        # Fix the "template" build JSONs to contain a proper directory
        # so the tests work.
        raw_buildlog = os.path.join(self.test_dir, 'buildlog.json')
        with open(raw_buildlog,
                  encoding="utf-8", errors="ignore") as log_file:
            build_json = json.load(log_file)
            for command in build_json:
                command['directory'] = self.test_dir

        self.__old_pwd = os.getcwd()
        os.chdir(self.test_workspace)
        self.buildlog = os.path.join(self.test_workspace, 'buildlog.json')
        with open(self.buildlog, 'w',
                  encoding="utf-8", errors="ignore") as log_file:
            json.dump(build_json, log_file)

    def tearDown(self):
        """ Tear down workspace."""

        shutil.rmtree(self.report_dir, ignore_errors=True)
        os.chdir(self.__old_pwd)

    @skipUnlessCTUCapable
    def test_ctu_all_ast_dump_based(self):
        """ Test full CTU AST-dump based analysis. """

        self.__test_ctu_all(on_demand=False)

    @skipUnlessCTUCapable
    @skipUnlessCTUOnDemandCapable
    def test_ctu_all_on_demand_parsed(self):
        """ Test full CTU on-demand-parsed ASTs. """

        self.__test_ctu_all(on_demand=True)

    @skipUnlessCTUCapable
    def test_ctu_collect_ast_dump_based(self):
        """ Test CTU collect phase with AST-dump based analysis. """

        self.__test_ctu_collect(on_demand=False)

    @skipUnlessCTUCapable
    @skipUnlessCTUOnDemandCapable
    def test_ctu_collect_on_demand_parsed(self):
        """
        Test CTU collect phase with on-demand-parsed AST based analysis.
        """

        self.__test_ctu_collect(on_demand=True)

    @skipUnlessCTUCapable
    def test_ctu_analyze_ast_dump_based(self):
        """ Test CTU analyze phase with AST-dump based analysis. """

        self.__test_ctu_analyze(on_demand=False)

    @skipUnlessCTUCapable
    @skipUnlessCTUOnDemandCapable
    def test_ctu_analyze_on_demand_parsed(self):
        """
        Test CTU analyze phase with on-demand-parsed AST based analysis.
        """

        self.__test_ctu_analyze(on_demand=True)

    def __test_ctu_all(self, on_demand=False):
        """ Test full CTU. """

        output = self.__do_ctu_all(on_demand=on_demand)
        self.__check_ctu_analyze(output)

    def __test_ctu_collect(self, on_demand=False):
        """ Test CTU collect phase. """

        self.__do_ctu_collect(on_demand=on_demand)
        self.__check_ctu_collect(on_demand=on_demand)

    def __test_ctu_analyze(self, on_demand=False):
        """ Test CTU analyze phase. """

        self.__do_ctu_collect(on_demand=on_demand)
        output = self.__do_ctu_analyze(on_demand=on_demand)
        self.__check_ctu_analyze(output)

    def __do_ctu_all(self, on_demand):
        """ Execute a full CTU run. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-all']
        if on_demand:
            cmd.append('--ctu-ast-mode=parse-on-demand')
        cmd.append(self.buildlog)
        out, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        return out

    def __do_ctu_collect(self, on_demand):
        """ Execute CTU collect phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-collect']
        if on_demand:
            cmd.append('--ctu-ast-mode=parse-on-demand')
        cmd.append(self.buildlog)
        call_command(cmd, cwd=self.test_dir, env=self.env)

    def __check_ctu_collect(self, on_demand):
        """ Check artifacts of CTU collect phase. """

        ctu_dir = os.path.join(self.report_dir, 'ctu-dir')
        self.assertTrue(os.path.isdir(ctu_dir))
        for arch in glob.glob(os.path.join(ctu_dir, '*')):
            old_map_file = os.path.join(ctu_dir, arch, 'externalFnMap.txt')
            new_map_file = os.path.join(ctu_dir, arch, 'externalDefMap.txt')
            self.assertTrue(any(os.path.isfile(mapfile) for mapfile in
                                [old_map_file, new_map_file]))
            if not on_demand:
                ast_dir = os.path.join(ctu_dir, arch, 'ast')
                self.assertTrue(os.path.isdir(ast_dir))

    def __do_ctu_analyze(self, on_demand):
        """ Execute CTU analyze phase. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-analyze']
        if on_demand:
            cmd.append('--ctu-ast-mode=parse-on-demand')
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
        self.assertIn("defect(s) in lib.c", output)
        self.assertIn("no defects in main.c", output)
        self.assertIn("lib.c:3:", output)
        self.assertIn("[core.NullDereference]", output)

    @skipUnlessCTUCapable
    def test_ctu_makefile_generation(self):
        """ Test makefile generation in CTU mode. """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu', '--makefile']
        cmd.append(self.buildlog)
        call_command(cmd, cwd=self.test_dir, env=self.env)

        call_command(["make"], cwd=self.report_dir, env=self.env)

        # Check the output.
        cmd = [self._codechecker_cmd, 'parse', self.report_dir]
        output, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        self.assertIn("defect(s) in lib.c", output)
        self.assertIn("lib.c:3:", output)
        self.assertIn("[core.NullDereference]", output)
