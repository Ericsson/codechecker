# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Test compilation database collection."""


import json
import os
import shutil
import tempfile
import unittest

from codechecker_analyzer import compilation_database


class TestCompilationDatabase(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """
        Make a temporary directory which contains a sample project to test.
        """

        # /tmp/project_dir             (cls.project_dir)
        #   |-sub                      (cls.project_dir)
        #   |  |-compile_commands.json (cls.comp_db_outer) (contains: inner.c)
        #   |  |-inner.c
        #   |  `-main.c
        #   |-compile_commands.json    (cls.comp_db_inner) (contains: outer.c,
        #                                                             inner.c)
        #   `-outer.c

        cls.project_dir = tempfile.mkdtemp()
        cls.project_sub_dir = os.path.join(cls.project_dir, "sub")

        cls.comp_db_outer = \
            os.path.join(cls.project_dir, "compile_commands.json")
        cls.comp_db_inner = \
            os.path.join(cls.project_sub_dir, "compile_commands.json")

        cls.source_file_outer = os.path.join(cls.project_dir, "outer.c")
        cls.source_file_inner = os.path.join(cls.project_sub_dir, "inner.c")
        cls.source_file_main = os.path.join(cls.project_sub_dir, "main.c")

        os.makedirs(cls.project_sub_dir)

        comp_db = [{
            "directory": cls.project_dir,
            "command": "gcc outer.c",
            "file": "outer.c"
        }, {
            "directory": cls.project_sub_dir,
            "command": "gcc inner.c",
            "file": "inner.c"
        }]

        comp_db_sub = [{
            "directory": cls.project_sub_dir,
            "command": "gcc inner.c",
            "file": "inner.c"
        }]

        def write_to_file(content: str, filename: str):
            with open(filename, "w", encoding="utf-8", errors="ignore") as f:
                f.write(content)

        write_to_file(json.dumps(comp_db), cls.comp_db_outer)
        write_to_file(json.dumps(comp_db_sub), cls.comp_db_inner)
        write_to_file("int main() {}", cls.source_file_outer)
        write_to_file("int main() {}", cls.source_file_inner)
        write_to_file("int main() {}", cls.source_file_main)

    @classmethod
    def teardown_class(cls):
        """
        Clean temporary directory and files.
        """
        shutil.rmtree(cls.project_dir)

    def test_find_closest_compilation_database(self):
        """
        Find the closest compilation database to each test source file.
        """
        closest = compilation_database.find_closest_compilation_database(
            TestCompilationDatabase.source_file_outer)

        self.assertEqual(closest, TestCompilationDatabase.comp_db_outer)

        closest = compilation_database.find_closest_compilation_database(
            TestCompilationDatabase.source_file_inner)

        self.assertEqual(closest, TestCompilationDatabase.comp_db_inner)

        closest = compilation_database.find_closest_compilation_database(
            TestCompilationDatabase.source_file_main)

        self.assertEqual(closest, TestCompilationDatabase.comp_db_inner)

    def test_gather_compilation_database(self):
        """
        Test if the correct set of build actions return to each test source
        file.

        WARNING! compilation_database.gather_compilation_database() function is
        looking for compile_commands.json up to the root directory. In this
        test-case we assume that the test project is somewhere under
        /tmp/<tempdir>/... This test project directory is created by
        setup_class(). If this test fails then it is possible that there is
        another compile_commands.json in the file system on the path up to the
        root.
        """
        def compile_commands(comp_db):
            return set([comp_action["command"] for comp_action in comp_db])

        # Check the assumption described in the function's documentation.
        self.assertTrue(
            all(db.startswith(self.project_dir)
                for db in compilation_database.find_all_compilation_databases(
                    self.project_dir)),
            "There must not be a compile_commands.json file on the path to "
            f"{self.project_dir}")

        # Build actions for files.

        comp_db = compilation_database.gather_compilation_database(
            TestCompilationDatabase.source_file_outer)

        self.assertEqual(len(comp_db), 1)
        self.assertIn("gcc outer.c", compile_commands(comp_db))

        comp_db = compilation_database.gather_compilation_database(
            TestCompilationDatabase.source_file_inner)

        self.assertEqual(len(comp_db), 1)
        self.assertIn("gcc inner.c", compile_commands(comp_db))

        comp_db = compilation_database.gather_compilation_database(
            TestCompilationDatabase.source_file_main)

        # In case a compile_commands.json is found outside of the project dir.
        if len(comp_db) != 0:
            for comp_action in comp_db:
                self.assertNotEqual(
                    comp_action["directory"],
                    self.project_dir)
                self.assertNotEqual(
                    comp_action["directory"],
                    self.project_sub_dir)

        # Build actions for directories.

        comp_db = compilation_database.gather_compilation_database(
            TestCompilationDatabase.project_dir)

        self.assertEqual(len(comp_db), 2)
        self.assertIn("gcc outer.c", compile_commands(comp_db))
        self.assertIn("gcc inner.c", compile_commands(comp_db))

        comp_db = compilation_database.gather_compilation_database(
            TestCompilationDatabase.project_sub_dir)

        self.assertEqual(len(comp_db), 1)
        self.assertIn("gcc inner.c", compile_commands(comp_db))

        # Non-existing file or directory.

        comp_db = compilation_database.gather_compilation_database(
            os.path.join(TestCompilationDatabase.project_dir, "non_existing"))

        self.assertIsNone(comp_db)
