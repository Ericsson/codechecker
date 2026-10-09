# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests of the test coverage storage: the API handlers, the run scoping of the
data, the cascades on run deletion and the garbage collection of files.
"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from codechecker_report_converter.report.coverage import FileCoverage

from codechecker_server.api.mass_store_run import MassStoreRun, \
    merge_file_coverage
from codechecker_server.api.report_server import ThriftRequestHandler
from codechecker_server.database import db_cleanup, run_db_model
from codechecker_server.database.run_db_model import \
    Base, File, FileContent, Run

# Not imported by its own name, so pytest does not try to collect it as a
# test class.
CoverageRow = run_db_model.TestCoverage


class TestCoverageTest(unittest.TestCase):
    """ Test the storage and the API of the test coverage data. """

    def setUp(self):
        self.engine = create_engine(
            'sqlite:///:memory:',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool)
        event.listen(self.engine, 'connect',
                     lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

        with self.session_factory() as session:
            for run_id, name in [(1, 'run1'), (2, 'run2')]:
                run = Run(name, '1.0')
                run.id = run_id
                session.add(run)

            for file_id, path in [(1, 'src/a.c'), (2, 'src/b.c')]:
                content_hash = f'hash{file_id}'
                session.add(FileContent(content_hash, b'', None))
                file = File(path, content_hash, None, None)
                file.id = file_id
                session.add(file)
            session.commit()

            session.add_all([
                CoverageRow(1, 1, [1, 2, 3], [4], 2, 1),
                CoverageRow(1, 2, [10], [], 0, 0),
                CoverageRow(2, 1, [1], [2, 3, 4], 2, 0)])
            session.commit()

        self.handler = ThriftRequestHandler.__new__(ThriftRequestHandler)
        self.handler._Session = self.session_factory

        self.require_view = patch.object(
            ThriftRequestHandler, '_ThriftRequestHandler__require_view',
            lambda self: None)
        self.require_view.start()

    def tearDown(self):
        self.require_view.stop()
        self.engine.dispose()

    def test_file_coverages_are_run_scoped(self):
        """ The summary contains one element per run and file. """
        result = self.handler.getFileCoverages([1])
        self.assertEqual(
            [(c.runId, c.fileId, c.filePath, c.linesFound, c.linesHit,
              c.functionsFound, c.functionsHit) for c in result],
            [(1, 1, 'src/a.c', 4, 3, 2, 1),
             (1, 2, 'src/b.c', 1, 1, 0, 0)])

        result = self.handler.getFileCoverages([2])
        self.assertEqual([(c.runId, c.fileId, c.linesHit) for c in result],
                         [(2, 1, 1)])

    def test_file_coverages_of_all_runs(self):
        """ An empty run list means all runs. """
        result = self.handler.getFileCoverages([])
        self.assertEqual([(c.runId, c.fileId) for c in result],
                         [(1, 1), (2, 1), (1, 2)])

    def test_file_line_coverage(self):
        """ The line coverage of a file depends on the run. """
        result = self.handler.getFileLineCoverage(1, 1)
        self.assertEqual(result.coveredLines, [1, 2, 3])
        self.assertEqual(result.uncoveredLines, [4])

        result = self.handler.getFileLineCoverage(2, 1)
        self.assertEqual(result.coveredLines, [1])
        self.assertEqual(result.uncoveredLines, [2, 3, 4])

    def test_file_line_coverage_without_data(self):
        """ Empty lists are returned if there is no coverage data. """
        result = self.handler.getFileLineCoverage(2, 2)
        self.assertEqual(result.coveredLines, [])
        self.assertEqual(result.uncoveredLines, [])

    def test_require_view_permission(self):
        """ The handlers check the product view permission. """
        self.require_view.stop()
        try:
            check = MagicMock(side_effect=PermissionError)
            with patch.object(ThriftRequestHandler,
                              '_ThriftRequestHandler__require_view', check):
                with self.assertRaises(Exception):
                    self.handler.getFileCoverages([])
                with self.assertRaises(Exception):
                    self.handler.getFileLineCoverage(1, 1)
            self.assertEqual(check.call_count, 2)
        finally:
            self.require_view.start()

    def test_run_deletion_removes_coverage(self):
        """ Coverage rows are removed by cascade when a run is deleted. """
        with self.session_factory() as session:
            session.delete(session.get(Run, 1))
            session.commit()

            self.assertEqual(
                [(c.run_id, c.file_id)
                 for c in session.query(CoverageRow)],
                [(2, 1)])

    def test_cleanup_keeps_files_with_coverage(self):
        """
        Files referenced only by coverage data must not be garbage collected,
        but they become unused when the runs referencing them are deleted.
        """
        product = MagicMock()
        product.session_factory = self.session_factory

        db_cleanup.remove_unused_files(product)
        with self.session_factory() as session:
            self.assertEqual(
                sorted(f.id for f in session.query(File)), [1, 2])

            session.delete(session.get(Run, 1))
            session.commit()

        db_cleanup.remove_unused_files(product)
        with self.session_factory() as session:
            self.assertEqual([f.id for f in session.query(File)], [1])

    def __store_coverage(self, run_id, file_coverages):
        """ Store the given coverage of a run like a storage does. """
        # pylint: disable=invalid-name,protected-access
        store = MassStoreRun.__new__(MassStoreRun)
        store._MassStoreRun__file_coverages = file_coverages
        with self.session_factory() as session:
            store._MassStoreRun__store_coverage(session, run_id)
            session.commit()

    def __coverage_of_run(self, run_id):
        return {(c.fileId, c.linesFound, c.linesHit)
                for c in self.handler.getFileCoverages([run_id])}

    def test_store_replaces_coverage_of_run(self):
        """ Storing coverage replaces the coverage of that run only. """
        self.__store_coverage(1, {2: FileCoverage([1, 2], [3], 0, 0)})

        self.assertEqual(self.__coverage_of_run(1), {(2, 3, 2)})
        self.assertEqual(self.__coverage_of_run(2), {(1, 4, 1)})

    def test_store_empty_coverage_clears_run(self):
        """
        A coverage file which matches no uploaded file removes the previous
        coverage of the run.
        """
        self.__store_coverage(1, {})

        self.assertEqual(self.__coverage_of_run(1), set())
        self.assertEqual(self.__coverage_of_run(2), {(1, 4, 1)})

    def test_merge_file_coverage(self):
        """ A line is covered if any report directory covers it. """
        merged = merge_file_coverage(
            FileCoverage([1, 2], [3, 4], 2, 1),
            FileCoverage([3], [1, 5], 3, 2))
        self.assertEqual(merged, FileCoverage([1, 2, 3], [4, 5], 3, 2))


class ParseCoverageFilesTest(unittest.TestCase):
    """ Test the parsing of the coverage files of a storage ZIP. """

    def setUp(self):
        self.report_dir = Path(tempfile.mkdtemp())

        # Only the state used by __parse_coverage_files() is initialized.
        # pylint: disable=invalid-name
        self.store = MassStoreRun.__new__(MassStoreRun)
        self.store._name = 'run'
        self.store._trim_path_prefixes = ['/home/user']
        self.store._MassStoreRun__graceful_cancel_if_requested = \
            lambda: None
        self.store._MassStoreRun__file_coverages = {}
        self.store._MassStoreRun__has_coverage_file = False

    def tearDown(self):
        shutil.rmtree(self.report_dir)

    def __add_report_dir(self, name: str, data, skip: str = ''):
        """ Add a report directory as it is unzipped on the server. """
        report_dir = self.report_dir / name
        report_dir.mkdir()
        with open(report_dir / 'coverage.json', 'w', encoding='utf-8') as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        if skip:
            with open(report_dir / 'skip_file', 'w', encoding='utf-8') as f:
                f.write(skip)

    def __parse(self, file_path_to_id: dict[str, int]):
        # pylint: disable=protected-access
        self.store._MassStoreRun__parse_coverage_files(
            self.report_dir, file_path_to_id)
        return self.store._MassStoreRun__file_coverages

    def test_only_uploaded_files_are_matched(self):
        """
        Coverage is matched to the files of the current storage by their
        trimmed path, other files are skipped.
        """
        self.__add_report_dir('a', {"version": 1, "files": {
            "/home/user/src/a.c": {"covered_lines": [1]},
            "/home/user/src/b.c": {"covered_lines": [2]},
            "/etc/passwd": {"covered_lines": [1]}}})

        result = self.__parse({'src/a.c': 1, 'src/c.c': 3})
        self.assertEqual(result, {1: FileCoverage([1], [], 0, 0)})

    def test_skip_file_is_respected(self):
        """ The skip file of the report directory is applied. """
        self.__add_report_dir('a', {"version": 1, "files": {
            "/home/user/src/a.c": {"covered_lines": [1]},
            "/home/user/src/b.c": {"covered_lines": [2]}}},
            skip='-/home/user/src/b.c\n')

        result = self.__parse({'src/a.c': 1, 'src/b.c': 2})
        self.assertEqual(list(result), [1])

    def test_multiple_report_dirs_are_merged(self):
        """ Coverage of the same file in multiple report dirs is merged. """
        self.__add_report_dir('a', {"version": 1, "files": {
            "/home/user/src/a.c": {"covered_lines": [1],
                                   "uncovered_lines": [2]}}})
        self.__add_report_dir('b', {"version": 1, "files": {
            "/home/user/src/a.c": {"covered_lines": [2],
                                   "uncovered_lines": [3]}}})

        result = self.__parse({'src/a.c': 1})
        self.assertEqual(result, {1: FileCoverage([1, 2], [3], 0, 0)})

    def test_malformed_coverage_file(self):
        """ A malformed coverage file fails the storage with a clear error. """
        for data in ["{not json", {"version": 1, "files": {
                "/home/user/src/a.c": {"covered_lines": [-1]}}}]:
            with self.subTest(data=data):
                self.__add_report_dir('bad', data)
                try:
                    with self.assertRaises(ValueError) as ctx:
                        self.__parse({'src/a.c': 1})
                    self.assertIn("Invalid test coverage file",
                                  str(ctx.exception))
                finally:
                    shutil.rmtree(self.report_dir / 'bad')

    def test_no_coverage(self):
        """ Nothing is collected if there is no coverage file. """
        os.makedirs(self.report_dir / 'a')
        self.assertEqual(self.__parse({'src/a.c': 1}), {})
        self.assertFalse(self.store._MassStoreRun__has_coverage_file)

    def test_nested_coverage_files_are_ignored(self):
        """
        Only the 'coverage.json' next to the 'metadata.json' of a report
        directory is parsed, not the ones in its subdirectories (e.g. in the
        uploaded 'conf' directory).
        """
        self.__add_report_dir('a', {"version": 1, "files": {
            "/home/user/src/a.c": {"covered_lines": [1]}}})
        for name, data in [('a', '{"files": {}}'), ('b', '{not json')]:
            conf_dir = self.report_dir / name / 'conf'
            conf_dir.mkdir(parents=True)
            with open(conf_dir / 'coverage.json', 'w', encoding='utf-8') as f:
                f.write(data)

        result = self.__parse({'src/a.c': 1})
        self.assertEqual(result, {1: FileCoverage([1], [], 0, 0)})

    def test_coverage_file_without_uploaded_files(self):
        """
        A coverage file is detected even if none of its source files were
        uploaded, so the previous coverage of the run is replaced.
        """
        self.__add_report_dir('a', {"version": 1, "files": {
            "/other/src/a.c": {"covered_lines": [1]}}})

        self.assertEqual(self.__parse({'src/a.c': 1}), {})
        self.assertTrue(self.store._MassStoreRun__has_coverage_file)


if __name__ == "__main__":
    unittest.main()
