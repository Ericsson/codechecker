#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Testing deletion of multiple runs.
"""


import os
import unittest
import itertools
import subprocess
from datetime import datetime

from libtest import env


def run_cmd(cmd):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.communicate()
    return proc.returncode


class TestCmdLineDeletion(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        self._cc_port = env.import_test_cfg(test_workspace)[
            'codechecker_cfg']['viewer_port']

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

    def test_multiple_deletion(self):
        """
        Test deletion of multiple runs.
        In the beginning five runs are placed in the database. This test checks
        if more runs can be deleted at once by --all-after-run and
        --all-before-time command line functions. Deleting a run by name should
        also work.
        """

        def all_exists(runs):
            run_names = map(lambda run: run.name, self._cc_client.getRunData())
            print run_names
            return set(runs) <= set(run_names)

        def none_exists(runs):
            run_names = map(lambda run: run.name, self._cc_client.getRunData())
            return not bool(set(runs).intersection(run_names))

        test_workspace = os.environ['TEST_WORKSPACE']

        project_name = self._testproject_data['name']
        run2_name = project_name + '_' + str(2)

        # Get all 5 runs.

        self.assertTrue(all_exists(
            [project_name + '_' + str(i) for i in range(0, 5)]))

        # Remove runs after run 2 by run name.

        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--all-after-run', run2_name,
                   '-p', str(self._cc_port)]
        run_cmd(del_cmd)

        run_names = map(lambda run: run.name, self._cc_client.getRunData())
        self.assertTrue(all_exists(
            [project_name + '_' + str(i) for i in range(0, 3)]))
        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(3, 5)]))

        # Remove runs before run 2 by run date.

        run2 = next(itertools.ifilter(
            lambda run: run.name == run2_name, self._cc_client.getRunData()),
            None)
        date_run2 = datetime.strptime(run2.runDate, '%Y-%m-%d %H:%M:%S.%f')
        date_run2 = \
            str(date_run2.year) + ':' + \
            str(date_run2.month) + ':' + \
            str(date_run2.day) + ':' + \
            str(date_run2.hour) + ':' + \
            str(date_run2.minute) + ':' + \
            str(date_run2.second)

        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--all-before-time', date_run2,
                   '-p', str(self._cc_port)]
        run_cmd(del_cmd)

        self.assertTrue(all_exists(
            [project_name + '_' + str(2)]))
        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(0, 5) if i != 2]))

        # Remove run by run name.

        del_cmd = [self._codechecker_cmd,
                   'cmd', 'del',
                   '--name', run2_name,
                   '-p', str(self._cc_port)]
        run_cmd(del_cmd)

        self.assertTrue(none_exists(
            [project_name + '_' + str(i) for i in range(0, 5)]))
