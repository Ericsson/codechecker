# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for gerrit output conversion."""


import os
import unittest
import tempfile
import json

from codechecker_common.output import gerrit
from codechecker_common.report import Report


class TestReportToGerrit(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.severity_map = {"my_checker": "LOW"}

    def test_report_to_gerrit_conversion(self):
        """Conversion without directory path just the source filename."""

        main = {
            "location": {"file": 0, "line": 3, "col": 3},
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "test_files/main.cpp"}
        metadata = {}

        report_to_convert = Report(main, bugpath, files, metadata)

        got = gerrit.convert([report_to_convert], self.severity_map)
        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "test_files/main.cpp": [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] test_files/main.cpp:3:3: "
                        "some description [my_checker]\n  sizeof(42);\n",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_abs_filepath(self):
        """Conversion report with absolute filepath"""

        main = {
            "location": {
                "file": 0,
                "line": 3,
                "col": 3,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }

        bugpath = {}
        metadata = {}

        file_path = os.path.abspath("test_files/main.cpp")
        files = {0: file_path}

        report_to_convert = Report(main, bugpath, files, metadata)

        got = gerrit.convert([report_to_convert], self.severity_map)
        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                file_path: [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] {0}:3:3: some description "
                                   "[my_checker]\n  sizeof(42);\n".format(
                                       file_path),
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_repo_dir(self):
        """Conversion report with absolute filepath and CC_REPO_DIR env"""

        main = {
            "location": {
                "file": 0,
                "line": 3,
                "col": 3,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        metadata = {}

        file_path = os.path.abspath("test_files/main.cpp")
        files = {0: file_path}

        report_to_convert = Report(main, bugpath, files, metadata)
        os.environ["CC_REPO_DIR"] = os.path.dirname(os.path.realpath(__file__))

        got = gerrit.convert([report_to_convert], self.severity_map)
        os.environ.pop("CC_REPO_DIR")

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "test_files/main.cpp": [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] test_files/main.cpp:3:3: "
                                   "some description [my_checker]\n"
                                   "  sizeof(42);\n".format(
                                       file_path),
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_report_url(self):
        """Conversion report with absolute filepath and CC_REPORT_URL env"""

        main = {
            "location": {
                "file": 0,
                "line": 3,
                "col": 3,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "test_files/main.cpp"}
        metadata = {}

        report_to_convert = Report(main, bugpath, files, metadata)
        os.environ["CC_REPORT_URL"] = "localhost:8080/index.html"
        got = gerrit.convert([report_to_convert], self.severity_map)

        # Remove environment variable not to influence the other tests.
        os.environ.pop("CC_REPORT_URL")

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code. "
            "See: 'localhost:8080/index.html'",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "test_files/main.cpp": [
                    {
                        "range": {
                            "start_line": 3,
                            "start_character": 3,
                            "end_line": 3,
                            "end_character": 3,
                        },
                        "message": "[LOW] test_files/main.cpp:3:3: "
                        "some description [my_checker]\n  sizeof(42);\n",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_filter_changed_files(self):
        """Conversion report with changed files filter.

        Reports from the lib.cpp file should be not in the converted list.
        """

        reports_to_convert = []

        # Empty for all reports.
        bugpath = {}
        metadata = {}

        main = {
            "location": {
                "file": 0,
                "line": 3,
                "col": 3,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }

        main_file_path = os.path.abspath("test_files/main.cpp")
        files = {0: main_file_path}

        main_report = Report(main, bugpath, files, metadata)
        reports_to_convert.append(main_report)
        reports_to_convert.append(main_report)

        main = {
            "location": {
                "file": 0,
                "line": 3,
                "col": 3,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }

        lib_file_path = os.path.abspath("test_files/lib.cpp")
        files = {0: lib_file_path}

        lib_report = Report(main, bugpath, files, metadata)
        reports_to_convert.append(lib_report)

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

        got = gerrit.convert(reports_to_convert, self.severity_map)
        os.remove(os.environ["CC_CHANGED_FILES"])

        # Remove environment variable not to influence the other tests.
        os.environ.pop("CC_CHANGED_FILES")

        review_comments = got["comments"]

        # Reports were found in two source files.
        self.assertEquals(len(review_comments), 1)

        # Two reports in the main.cpp file.
        self.assertEquals(len(review_comments[main_file_path]), 2)

        self.assertIn(
            "CodeChecker found 3 issue(s) in the code.", got["message"])
        self.assertIn(
            "following reports are introduced in files which are not changed",
            got["message"])
        self.assertIn(lib_file_path, got["message"])
