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
            "location": {"file": "main.cpp", "line": 10, "col": 10},
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "main.cpp"}
        metadata = {}

        report_to_convert = Report(main, bugpath, files, metadata)

        got = gerrit.convert([report_to_convert], self.severity_map)
        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "main.cpp": [
                    {
                        "range": {
                            "start_line": 10,
                            "start_character": 10,
                            "end_line": 10,
                            "end_character": 10,
                        },
                        "message": "[LOW] main.cpp:10:10: "
                        "some description [my_checker]\n10",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_abs_filepath(self):
        """Conversion report with absolute filepath"""

        main = {
            "location": {
                "file": "/home/src/lib/main.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "main.cpp"}
        metadata = {}

        report_to_convert = Report(main, bugpath, files, metadata)

        got = gerrit.convert([report_to_convert], self.severity_map)
        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "/home/src/lib/main.cpp": [
                    {
                        "range": {
                            "start_line": 10,
                            "start_character": 10,
                            "end_line": 10,
                            "end_character": 10,
                        },
                        "message": "[LOW] /home/src/lib/main.cpp:10:10: "
                        "some description [my_checker]\n10",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_repo_dir(self):
        """Conversion report with absolute filepath and CC_REPO_DIR env"""

        main = {
            "location": {
                "file": "/home/src/lib/main.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "/home/src/lib/main.cpp"}
        metadata = {}

        report_to_convert = Report(main, bugpath, files, metadata)
        os.environ["CC_REPO_DIR"] = "/home/src/lib"

        got = gerrit.convert([report_to_convert], self.severity_map)
        os.environ.pop("CC_REPO_DIR")

        expected = {
            "tag": "jenkins",
            "message": "CodeChecker found 1 issue(s) in the code.",
            "labels": {"Code-Review": -1, "Verified": -1},
            "comments": {
                "main.cpp": [
                    {
                        "range": {
                            "start_line": 10,
                            "start_character": 10,
                            "end_line": 10,
                            "end_character": 10,
                        },
                        "message": "[LOW] main.cpp:10:10: "
                        "some description [my_checker]\n10",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_report_url(self):
        """Conversion report with absolute filepath and CC_REPORT_URL env"""

        main = {
            "location": {
                "file": "/home/src/lib/main.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        bugpath = {}
        files = {0: "main.cpp"}
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
                "/home/src/lib/main.cpp": [
                    {
                        "range": {
                            "start_line": 10,
                            "start_character": 10,
                            "end_line": 10,
                            "end_character": 10,
                        },
                        "message": "[LOW] /home/src/lib/main.cpp:10:10: "
                        "some description [my_checker]\n10",
                    }
                ]
            },
        }
        self.assertEquals(got, expected)

    def test_report_to_gerrit_conversion_filter_changed_files(self):
        """Conversion report with changed files filter.

        Reports from the other.cpp file should be not in the converted list.
        """

        reports_to_convert = []

        # Empty for all reports.
        bugpath = {}
        metadata = {}

        main = {
            "location": {
                "file": "/home/src/lib/main.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        files = {0: "/home/src/lib/main.cpp"}

        main_report = Report(main, bugpath, files, metadata)
        reports_to_convert.append(main_report)
        reports_to_convert.append(main_report)

        main = {
            "location": {
                "file": "/home/src/lib/lib.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        files = {0: "/home/src/lib/lib.cpp"}

        lib_report = Report(main, bugpath, files, metadata)
        reports_to_convert.append(lib_report)

        main = {
            "location": {
                "file": "/home/src/lib/other.cpp",
                "line": 10,
                "col": 10,
            },
            "description": "some description",
            "check_name": "my_checker",
            "issue_hash_content_of_line_in_context": "dummy_hash",
            "notes": [],
            "macro_expansions": [],
        }
        files = {0: "/home/src/lib/other.cpp"}

        other_report = Report(main, bugpath, files, metadata)
        reports_to_convert.append(other_report)

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
            },
            "lib.cpp": {"lines_inserted": 1, "size_delta": 1, "size": 100},
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
        self.assertEquals(len(review_comments), 2)

        # Two reports in the main.cpp file.
        self.assertEquals(len(review_comments["/home/src/lib/main.cpp"]), 2)

        self.assertEquals(
            "CodeChecker found 3 issue(s) in the code.", got["message"]
        )
        self.assertNotIn("/home/src/lib/other.cpp", review_comments.keys())
