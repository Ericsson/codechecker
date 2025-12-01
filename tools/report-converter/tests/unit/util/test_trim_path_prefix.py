# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test cases to trim a path by using prefixes. """


import unittest

from codechecker_report_converter.util import trim_path_prefixes
from codechecker_report_converter.report import (
    BugPathEvent,
    File,
    MacroExpansion,
    Report,
)


class TrimPathPrefixTestCase(unittest.TestCase):
    """
    Test cases to trim a path by using prefixes.
    """

    def test_no_prefix(self):
        test_path = '/a/b/c'
        self.assertEqual(test_path, trim_path_prefixes(test_path, None))
        self.assertEqual(test_path, trim_path_prefixes(test_path, []))
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['x']))

    def test_only_root_matches(self):
        test_path = '/a/b/c'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/']))
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/x']))

    def test_one_matches(self):
        test_path = '/a/b/c'
        self.assertEqual('b/c', trim_path_prefixes(test_path, ['/a']))
        self.assertEqual('c', trim_path_prefixes(test_path, ['/a/b']))

    def test_longest_matches(self):
        test_path = '/a/b/c'
        self.assertEqual('b/c', trim_path_prefixes(test_path, ['/a']))
        self.assertEqual('c', trim_path_prefixes(test_path, ['/a', '/a/b']))

    def test_file_path(self):
        test_path = '/a/b/c/foo.txt'
        self.assertEqual('foo.txt', trim_path_prefixes(test_path, ['/a/b/c']))

    def test_prefix_in_dir_name(self):
        test_path = '/a/b/common/foo.txt'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/a/b/c']))
        self.assertEqual('foo.txt',
                         trim_path_prefixes(test_path, ['/a/b/common']))

    def test_prefix_in_filename(self):
        test_path = '/a/b/common.txt'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/a/b/c']))
        self.assertEqual(test_path,
                         trim_path_prefixes(test_path, ['/a/b/common']))
        self.assertEqual('common.txt',
                         trim_path_prefixes(test_path, ['/a/b/']))

    def test_prefix_blob(self):
        test_path = '/a/b/common.txt'
        self.assertEqual('common.txt', trim_path_prefixes(test_path, ['/*/b']))
        self.assertEqual('common.txt', trim_path_prefixes(test_path, ['/a/*']))
        self.assertEqual('common.txt',
                         trim_path_prefixes(test_path, ['/*/']))
        self.assertEqual('common.txt',
                         trim_path_prefixes(test_path, ['/a/?/']))

        self.assertEqual('my_proj/x.cpp',
                         trim_path_prefixes('/home/jsmith/my_proj/x.cpp',
                                            ['/home/jsmith/']))

    def test_remove_only_root_prefix(self):
        """Test removing only the root '/' prefix from paths."""

        test_paths = ["/a/b/c", "/foo.txt", "/dir/subdir/file.cpp", "/"]

        expected_paths = ["/a/b/c", "/foo.txt", "/dir/subdir/file.cpp", "/"]

        for test_path, expected in zip(test_paths, expected_paths):
            self.assertEqual(
                expected,
                trim_path_prefixes(test_path, ["/"]),
                f"Failed to handle root prefix in {test_path}",
            )

    def test_trim_path_in_message(self):
        """
        Test trimming path prefixes in report messages and bug path events.
        """

        test_file = File("/path/to/workspace/src/example.cpp")

        test_cases = [
            # Simple message with one path
            {
                "name": "simple_message",
                "message": ("Error in file "
                            "/path/to/workspace/src/example.cpp:10:20"),
                "bug_path_events": [
                    BugPathEvent(
                        "Found issue at "
                        "/path/to/workspace/include/header.h:5:10",
                        File("/path/to/workspace/include/header.h"),
                        5,
                        10,
                    )
                ],
                "expected_message": "Error in file src/example.cpp:10:20",
                "expected_bug_path_messages": [
                    "Found issue at include/header.h:5:10"
                ],
            },
            # Complex message with multiple paths
            {
                "name": "complex_message",
                "message": (
                    "Multiple errors: "
                    "/path/to/workspace/src/example.cpp:10:20 and "
                    "/path/to/workspace/include/header.h:5:10"
                ),
                "bug_path_events": [],
                "expected_message": (
                    "Multiple errors: src/example.cpp:10:20 and "
                    "include/header.h:5:10"
                ),
                "expected_bug_path_messages": [],
            },
        ]

        for case in test_cases:
            report = Report(
                file=test_file,
                line=10,
                column=20,
                message=case["message"],
                checker_name="test-checker",
                severity="HIGH",
            )

            for event in case["bug_path_events"]:
                report.bug_path_events.append(event)

            report.trim_path_prefixes(["/path/to/workspace"])

            self.assertEqual(
                case["expected_message"],
                report.message,
                f"Failed to trim message in {case['name']} case",
            )

            for i, expected_msg in enumerate(
                case["expected_bug_path_messages"]
            ):
                # Note: Bug path events are 1-indexed in the report
                self.assertEqual(
                    expected_msg,
                    report.bug_path_events[i + 1].message,
                    "Failed to trim bug path event message "
                    "in {case['name']} case",
                )

    def test_trim_path_in_complex_message(self):

        test_file = File("/path/to/workspace/src/example.cpp")

        message = (
            "Multiple errors: "
            "/path/to/workspace/src/example.cpp:10:20 and "
            "/path/to/workspace/include/header.h:5:10"
        )

        report = Report(
            file=test_file,
            line=10,
            column=20,
            message=message,
            checker_name="test-checker",
            severity="HIGH",
        )

        report.trim_path_prefixes(["/path/to/workspace"])

        expected = (
            "Multiple errors: src/example.cpp:10:20 and "
            "include/header.h:5:10"
        )
        self.assertEqual(expected, report.message)

    def test_trim_path_in_macro_expansions(self):
        """
        Test trimming path prefixes in macro expansions with various scenarios.
        """

        test_file = File("/path/to/workspace/src/example.cpp")

        test_cases = [
            # Single macro with simple path
            {
                "name": "single_macro",
                "files": [File("/path/to/workspace/include/macro.h")],
                "messages": [
                    "Macro expanded from "
                    "/path/to/workspace/include/macro.h:5:10"
                ],
                "names": ["TEST_MACRO"],
                "lines": [5],
                "columns": [10],
                "expected_messages": [
                    "Macro expanded from include/macro.h:5:10"
                ],
                "expected_paths": ["include/macro.h"],
            },
            # Multiple macros
            {
                "name": "multiple_macros",
                "files": [
                    File("/path/to/workspace/include/macro1.h"),
                    File("/path/to/workspace/include/macro2.h"),
                ],
                "messages": [
                    "First macro from "
                    "/path/to/workspace/include/macro1.h:5:10",
                    "Second macro from "
                    "/path/to/workspace/include/macro2.h:15:20",
                ],
                "names": ["MACRO1", "MACRO2"],
                "lines": [5, 15],
                "columns": [10, 20],
                "expected_messages": [
                    "First macro from include/macro1.h:5:10",
                    "Second macro from include/macro2.h:15:20",
                ],
                "expected_paths": ["include/macro1.h", "include/macro2.h"],
            },
            # Macro with multiple path references
            {
                "name": "multiple_paths",
                "files": [File("/path/to/workspace/include/macro.h")],
                "messages": [
                    "Macro expanded from "
                    "/path/to/workspace/include/macro.h:5:10 "
                    "includes /path/to/workspace/include/header.h:3:4"
                ],
                "names": ["TEST_MACRO"],
                "lines": [5],
                "columns": [10],
                "expected_messages": [
                    "Macro expanded from include/macro.h:5:10 "
                    "includes include/header.h:3:4"
                ],
                "expected_paths": ["include/macro.h"],
            },
        ]

        for case in test_cases:
            macros = []
            for i in range(len(case["files"])):
                macros.append(
                    MacroExpansion(
                        message=case["messages"][i],
                        name=case["names"][i],
                        file=case["files"][i],
                        line=case["lines"][i],
                        column=case["columns"][i],
                    )
                )

            report = Report(
                file=test_file,
                line=10,
                column=20,
                message=f"Error in macro expansion - {case['name']}",
                checker_name="test-checker",
                severity="HIGH",
                macro_expansions=macros,
            )

            report.trim_path_prefixes(["/path/to/workspace"])

            for i, (expected_msg, expected_path) in enumerate(
                zip(case["expected_messages"], case["expected_paths"])
            ):
                self.assertEqual(
                    expected_msg,
                    report.macro_expansions[i].message,
                    f"Failed to trim message in {case['name']} case",
                )
                self.assertEqual(
                    expected_path,
                    report.macro_expansions[i].file.path,
                    f"Failed to trim file path in {case['name']} case",
                )

    def test_macro_expansion_edge_cases(self):
        """Test trimming path prefixes in macro expansions with edge cases."""

        test_file = File("/path/to/workspace/src/example.cpp")

        edge_cases = [
            (File(""), "Empty file path"),
            (File("/"), "Root path only"),
            (File("/path/to/workspace/"), "Directory path ending with slash"),
            (File("relative/path.h"), "Relative path"),
        ]

        for file, desc in edge_cases:
            macro = MacroExpansion(
                message=f"Macro with {desc}: {file.path}",
                name="TEST_MACRO",
                file=file,
                line=1,
                column=1,
            )

            report = Report(
                file=test_file,
                line=10,
                column=20,
                message=f"Error in macro expansion - {desc}",
                checker_name="test-checker",
                severity="HIGH",
                macro_expansions=[macro],
            )

            report.trim_path_prefixes(["/path/to/workspace"])

            if desc in ["Empty file path", "Root path only"]:
                self.assertEqual(
                    file.path, report.macro_expansions[0].file.path
                )
            elif desc == "Directory path ending with slash":
                self.assertEqual("", report.macro_expansions[0].file.path)
            else:
                # Relative path unchanged
                self.assertEqual(
                    file.path, report.macro_expansions[0].file.path
                )
