# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Tests for gerrit output conversion. """

import json
import os
import tempfile
import unittest

from codechecker_report_converter.report import File, Report
from codechecker_report_converter.report.output import gerrit


class TestReportToGerrit(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls._test_files_dir = os.path.join(
            os.path.dirname(__file__), 'test_files')

        cls._src_files = [
            File(os.path.join(cls._test_files_dir, 'main.cpp')),
            File(os.path.join(cls._test_files_dir, 'lib.cpp'))]

    def tearDown(self):
        if "CC_REPO_DIR" in os.environ:
            os.environ.pop("CC_REPO_DIR")

        if "CC_REPORT_URL" in os.environ:
            os.environ.pop("CC_REPORT_URL")

    def test_report_to_gerrit_conversion(self):
        """ Conversion without directory path just the source filename. """
        report = Report(
            self._src_files[0], 3, 3, 'some description', 'my_checker',
            report_hash='dummy_hash',
            severity='LOW')

        os.environ["CC_REPO_DIR"] = self._test_files_dir
        res = gerrit.convert([report])

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "main.cpp": [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] main.cpp:3:3: "
                        "some description [my_checker]\n  sizeof(42);\n",
                    }
                ]
            },
        }
        self.assertEqual(res, expected)

    def test_report_to_gerrit_conversion_abs_filepath(self):
        """ Conversion report with absolute filepath. """
        report = Report(
            self._src_files[0], 3, 3, 'some description', 'my_checker',
            report_hash='dummy_hash',
            severity='LOW')

        res = gerrit.convert([report])

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                self._src_files[0].path: [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] {0}:3:3: some description "
                                   "[my_checker]\n  sizeof(42);\n".format(
                                       self._src_files[0].path),
                    }
                ]
            },
        }
        self.assertEqual(res, expected)

    def test_report_to_gerrit_conversion_report_url(self):
        """ Conversion report with absolute filepath and CC_REPORT_URL env. """
        report = Report(
            self._src_files[0], 3, 3, 'some description', 'my_checker',
            report_hash='dummy_hash',
            severity='LOW')

        os.environ["CC_REPO_DIR"] = self._test_files_dir
        os.environ["CC_REPORT_URL"] = "localhost:8080/index.html"
        res = gerrit.convert([report])

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code. "
            "See: localhost:8080/index.html",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "main.cpp": [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] main.cpp:3:3: "
                        "some description [my_checker]\n  sizeof(42);\n",
                    }
                ]
            },
        }
        self.assertEqual(res, expected)

    def test_report_to_gerrit_conversion_filter_changed_files(self):
        """Conversion report with changed files filter.

        Reports from the lib.cpp file should be not in the converted list.
        """
        report = Report(
            self._src_files[0], 3, 3, 'some description', 'my_checker',
            report_hash='dummy_hash',
            severity='LOW')

        lib_report = Report(
            self._src_files[1], 3, 3, 'some description', 'my_checker',
            report_hash='dummy_hash',
            severity='LOW')

        dummy_changed_files_content = {
            "/COMMIT_MSG": {
                "status": "A",
                "lines_inserted": 1,
                "size_delta": 1,
                "size": 100,
            },
            "main.cpp": {
                "lines_inserted": 1,
                "lines_deleted": 1,
                "size_delta": 1,
                "size": 100,
            }
        }
        fd, changed_files_file = tempfile.mkstemp()
        os.write(fd, json.dumps(dummy_changed_files_content).encode("utf-8"))
        os.close(fd)

        os.environ["CC_CHANGED_FILES"] = changed_files_file

        res = gerrit.convert([report, report, lib_report])
        os.remove(os.environ["CC_CHANGED_FILES"])

        # Remove environment variable not to influence the other tests.
        os.environ.pop("CC_CHANGED_FILES")

        review_comments = res["comments"]

        # Reports were found in two source files.
        self.assertEqual(len(review_comments), 1)

        # Two reports in the main.cpp file.
        self.assertEqual(len(review_comments[report.file.path]), 2)

        self.assertIn(
            "CodeChecker found 3 issue(s) in the code.", res["message"])
        self.assertIn(
            "following reports are introduced in files which are not changed",
            res["message"])
        self.assertIn(lib_report.file.path, res["message"])
