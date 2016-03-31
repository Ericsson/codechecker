#!/usr/bin/env python2

"""
Tests hash clash handling.
"""

import unittest
import os
import random
import string
from uuid import uuid4
from contextlib import contextmanager
from shared.ttypes import BugPathPos, BugPathEvent, Severity
from test_utils.thrift_client_to_db import CCReportHelper


def _generate_content(cols, lines):
    """Generates a random file content string."""

    content = ""
    for _ in xrange(1, lines):
        for _ in xrange(1, cols):
            content += random.choice(string.letters)
        content += '\n'
    return content

class HashClash(unittest.TestCase):
    """Unit test for testing hash clash handling."""

    def _create_run(self, name):
        """Creates a new run using an unique id."""

        return self._report.addCheckerRun(name, name + str(uuid4()), 'v', False)

    def _create_file(self, run_id, name, cols=10, lines=10):
        """Creates a new file with random content."""

        path = name + "_" + str(uuid4())
        need = self._report.needFileContent(run_id, path)
        self.assertTrue(need.needed)

        content = _generate_content(cols, lines)
        success = self._report.addFileContent(need.fileId, content)
        self.assertTrue(success)

        return need.fileId

    def _create_build_action(self, run_id, name):
        """Creates a new build action."""

        return self._report.addBuildAction(run_id, name, name)

    def _create_simple_report(self, file_id, build_action_id, bug_hash, position):
        """Creates a new report with one bug path position and event."""

        bug_path = [BugPathPos(position[0][0], position[0][1],
                               position[1][0], position[1][1], file_id)]
        bug_evt = [BugPathEvent(position[0][0], position[0][1],
                                position[1][0], position[1][1], 'evt', file_id)]
        return self._report.addReport(build_action_id,
                                      file_id,
                                      bug_hash,
                                      'test',
                                      bug_path,
                                      bug_evt,
                                      'test_id',
                                      'test_cat',
                                      'test_type',
                                      Severity.UNSPECIFIED,
                                      False)

    @contextmanager
    def _init_new_test(self, name):
        """Creates a new run, file, and build action.

        Use it in a 'with' statement. At the end of the 'with' statement it
        calls the finish methods for the run and the build action.

        Example:
            with self._init_new_test('test') as ids:
                # do stuff
        """

        run_id = self._create_run(name)
        file_id = self._create_file(run_id, name)
        build_action_id = self._create_build_action(run_id, name)
        yield (run_id, file_id, build_action_id)
        self._report.finishBuildAction(build_action_id, 'OK')
        self._report.finishCheckerRun(run_id)

    def setUp(self):
        self._report = CCReportHelper('localhost',
                                      int(os.environ['CC_TEST_SERVER_PORT']),
                                      '/')

    def test(self):
        """Runs the following tests:

        - Duplicates.
        - Hash clash in same file.
        - Hash clash in different files.
        - Hash clash in different build actions.
        """

        with self._init_new_test('test1') as ids1, \
             self._init_new_test('test2') as ids2:
            _, file_id1, build_action_id1 = ids1
            run_id2, file_id2, build_action_id2 = ids2
            rep_id1 = self._create_simple_report(file_id1,
                                                 build_action_id1,
                                                 'XXX',
                                                 ((1, 1), (1, 2)))
            rep_id2 = self._create_simple_report(file_id1,
                                                 build_action_id1,
                                                 'XXX',
                                                 ((1, 1), (1, 2)))
            # Same file, same hash and position
            self.assertEqual(rep_id1, rep_id2)

            rep_id3 = self._create_simple_report(file_id1,
                                                 build_action_id1,
                                                 'XXX',
                                                 ((2, 1), (2, 2)))
            # Same file, same hash and different position
            self.assertNotEqual(rep_id1, rep_id3)

            rep_id4 = self._create_simple_report(file_id2,
                                                 build_action_id2,
                                                 'XXX',
                                                 ((1, 1), (1, 2)))
            rep_id5 = self._create_simple_report(file_id2,
                                                 build_action_id2,
                                                 'YYY',
                                                 ((1, 1), (1, 2)))
            # Different file, same hash, and position
            self.assertNotEqual(rep_id1, rep_id4)
            # Different file, same hash and different position
            self.assertNotEqual(rep_id3, rep_id4)
            # Same file and position, different hash
            self.assertNotEqual(rep_id4, rep_id5)

            build_action_id2_2 = self._create_build_action(run_id2, 'test2_2')
            try:
                rep_id6 = self._create_simple_report(file_id2,
                                                     build_action_id2_2,
                                                     'XXX',
                                                     ((1, 1), (1, 2)))
                # Same run, file, hash, and position, but different build action
                self.assertEqual(rep_id4, rep_id6)
            finally:
                self._report.finishBuildAction(build_action_id2_2, 'OK')

            rep_id7 = self._create_simple_report(file_id1,
                                                 build_action_id2,
                                                 'XXX',
                                                 ((1, 1), (1, 2)))
            # build_action_id1 and build_action_id2 is in different runs
            self.assertNotEqual(rep_id1, rep_id7)
