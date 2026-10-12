# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Unit tests for making a plist analysis output self-contained."""

import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_analyzer import self_contained


class TestMakeSelfContained(unittest.TestCase):
    """Test the plist-only self-contained post-processing step."""

    def setUp(self):
        self.output_dir = tempfile.mkdtemp(prefix="cc-selfcontained-out-")
        self.project_dir = tempfile.mkdtemp(prefix="cc-selfcontained-src-")
        self.source = os.path.join(self.project_dir, "main.c")
        with open(self.source, "w", encoding="utf-8") as f:
            f.write("int main() { return 0; }\n")
        self.plist = os.path.join(self.output_dir, "report.plist")
        data = {
            "files": [self.source],
            "diagnostics": [
                {
                    "location": {"line": 1, "col": 1, "file": 0},
                    "issue_hash_content_of_line_in_context": "deadbeef",
                    "check_name": "test.checker",
                    "description": "test issue",
                    "category": "unknown",
                    "path": [
                        {
                            "kind": "event",
                            "location": {"line": 1, "col": 1, "file": 0},
                            "depth": 0,
                            "message": "test event",
                        }
                    ],
                }
            ],
            "metadata": {},
        }
        with open(self.plist, "wb") as f:
            plistlib.dump(data, f)

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def test_single_plist_becomes_portable(self):
        """
        A plist referencing an absolute source path should, after processing,
        reference a copy under <output>/sources via a path relative to the
        plist, and that path must resolve to an existing file.
        """
        self_contained.make_self_contained(self.output_dir)

        # The source must have been copied under <output>/sources, mirroring
        # its absolute path.
        sources_dir = os.path.join(
            self.output_dir, self_contained.SOURCES_DIR_NAME
        )
        expected_copy = os.path.join(sources_dir, self.source.lstrip(os.sep))
        self.assertTrue(
            os.path.isfile(expected_copy),
            f"Expected copied source at {expected_copy}",
        )

        # The rewritten plist's files array must contain only relative paths
        with open(self.plist, "rb") as f:
            data = plistlib.load(f)

        self.assertEqual(len(data["files"]), 1)
        rewritten_entry = data["files"][0]
        self.assertFalse(
            os.path.isabs(rewritten_entry),
            "Plist file entry should be relative",
        )

        plist_dir = os.path.dirname(self.plist)
        resolved = os.path.normpath(os.path.join(plist_dir, rewritten_entry))
        self.assertTrue(os.path.isfile(resolved))
        self.assertEqual(
            os.path.realpath(resolved), os.path.realpath(expected_copy)
        )


if __name__ == "__main__":
    unittest.main()
