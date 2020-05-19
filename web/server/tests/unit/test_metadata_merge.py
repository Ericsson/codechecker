# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Unit tests for the metadata merge. """

import json
import os
from tempfile import mkdtemp
import shutil
import unittest

from codechecker_client.metadata import metadata_v1_to_v2, merge_metadata_json


class MetadataMergeTest(unittest.TestCase):
    """ Test for merging multiple metadata.json file. """

    def test_metadata_v1_to_v2(self):
        """ Test to convert v1 version format metadata to v2 format. """
        metadata = {
            "action_num": 1,
            "checkers": {
                "clang-tidy": ["a"],
                "clangsa": {"b": False}
            },
            "command": ["CodeChecker", "analyze"],
            "failed": {},
            "output_path": "/path/to/reports",
            "result_source_files": {
                "/path/to/reports/main.cpp_cd.plist": "/path/to/main.cpp",
                "/path/to/reports/main.cpp_ed.plist": "/path/to/main.cpp"
            },
            "skipped": 1,
            "successful": {
                "clang-tidy": 1,
                "clangsa": 1
            },
            "timestamps": {
                "begin": 1571728770,
                "end": 1571728771
            },
            "versions": {
                "clang": "clang version 5.0.1",
                "clang-tidy": "LLVM version 5.0.1",
                "codechecker": "6.5.1 (fd2df38)"
            },
            "working_directory": "/path/to/workspace"
        }

        expected = {
            "version": 2,
            "tools": [{
                "name": "codechecker",
                "version": "6.5.1 (fd2df38)",
                "command": ["CodeChecker", "analyze"],
                "output_path": "/path/to/reports",
                "skipped": 1,
                "timestamps": {
                    "begin": 1571728770,
                    "end": 1571728771
                },
                "working_directory": "/path/to/workspace",
                "analyzers": {
                    "clang-tidy": {
                        "checkers": {"a": True},
                        "analyzer_statistics": {}
                    },
                    "clangsa": {
                        "checkers": {"b": False},
                        "analyzer_statistics": {}
                    }
                },
                "result_source_files": {
                    "/path/to/reports/main.cpp_cd.plist": "/path/to/main.cpp",
                    "/path/to/reports/main.cpp_ed.plist": "/path/to/main.cpp"
                },
            }]
        }

        res = metadata_v1_to_v2(metadata)
        self.assertEqual(res, expected)

    def test_merge_metadata(self):
        """ Test merging multiple metadata files. """
        metadata_v1 = {
            "action_num": 1,
            "checkers": {
                "clang-tidy": ["a"],
                "clangsa": {"b": False}
            },
            "command": ["CodeChecker", "analyze"],
            "failed": {},
            "output_path": "/path/to/reports",
            "result_source_files": {
                "/path/to/reports/main.cpp_cd.plist": "/path/to/main.cpp",
                "/path/to/reports/main.cpp_ed.plist": "/path/to/main.cpp"
            },
            "skipped": 1,
            "successful": {
                "clang-tidy": 1,
                "clangsa": 1
            },
            "timestamps": {
                "begin": 1571728770,
                "end": 1571728771
            },
            "versions": {
                "clang": "clang version 5.0.1",
                "clang-tidy": "LLVM version 5.0.1",
                "codechecker": "6.5.1 (fd2df38)"
            },
            "working_directory": "/path/to/workspace"
        }

        metadata_v2 = {
            "version": 2,
            'num_of_report_dir': 1,
            "tools": [{
                "name": "cppcheck",
                "analyzer_statistics": {
                    "failed": 0,
                    "failed_sources": [],
                    "successful": 1,
                    "version": "Cppcheck 1.87"
                },
                "command": ["cppcheck", "/path/to/main.cpp"],
                "timestamps": {
                    "begin": 1571297867,
                    "end": 1571297868
                }
            }]
        }

        metadata_v3 = {
            "version": 2,
            'num_of_report_dir': 1,
            "tools": [{
                "name": "cppcheck",
                "command": ["cppcheck", "/path/to/main2.cpp"],
                "timestamps": {
                    "begin": 1571297867,
                    "end": 1571297868
                }
            }]
        }

        expected = {
            "version": 2,
            'num_of_report_dir': 2,
            "tools": [{
                "name": "codechecker",
                "version": "6.5.1 (fd2df38)",
                "command": ["CodeChecker", "analyze"],
                "output_path": "/path/to/reports",
                "skipped": 1,
                "timestamps": {
                    "begin": 1571728770,
                    "end": 1571728771
                },
                "working_directory": "/path/to/workspace",
                "analyzers": {
                    "clang-tidy": {
                        "checkers": {"a": True},
                        "analyzer_statistics": {}
                    },
                    "clangsa": {
                        "checkers": {"b": False},
                        "analyzer_statistics": {}
                    }
                },
                "result_source_files": {
                    "/path/to/reports/main.cpp_cd.plist": "/path/to/main.cpp",
                    "/path/to/reports/main.cpp_ed.plist": "/path/to/main.cpp"
                }},
                {
                    "name": "cppcheck",
                    "analyzer_statistics": {
                        "failed": 0,
                        "failed_sources": [],
                        "successful": 1,
                        "version": "Cppcheck 1.87"
                    },
                    "command": ["cppcheck", "/path/to/main.cpp"],
                    "timestamps": {
                        "begin": 1571297867,
                        "end": 1571297868
                    }
                },
                {
                    "name": "cppcheck",
                    "command": ["cppcheck", "/path/to/main2.cpp"],
                    "timestamps": {
                        "begin": 1571297867,
                        "end": 1571297868
                    }
                }]
        }

        try:
            metadata_dir = mkdtemp()

            mf_1 = os.path.join(metadata_dir, 'm1.json')
            mf_2 = os.path.join(metadata_dir, 'm2.json')
            mf_3 = os.path.join(metadata_dir, 'm3.json')

            with open(mf_1, 'w', encoding='utf-8', errors='ignore') as f1:
                f1.write(json.dumps(metadata_v1, indent=2))

            with open(mf_2, 'w', encoding='utf-8', errors='ignore') as f2:
                f2.write(json.dumps(metadata_v2, indent=2))

            with open(mf_3, 'w', encoding='utf-8', errors='ignore') as f3:
                f3.write(json.dumps(metadata_v3, indent=2))

            res = merge_metadata_json([mf_1, mf_2, mf_3], 2)
            self.assertEqual(res, expected)
        finally:
            shutil.rmtree(metadata_dir)
