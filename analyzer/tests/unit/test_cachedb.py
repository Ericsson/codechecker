# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests analyzer CacheDB operations"""

import unittest
import shutil
import os
from libtest import env
from codechecker_analyzer.cachedb import CacheDB


class CacheDBTest(unittest.TestCase):
    """Tests analyzer CacheDB operations"""

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE

        TEST_WORKSPACE = env.get_workspace('cachedb')
        self.test_workspace = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def insert_dummy_data(self, cachedb: CacheDB):
        cachedb.insert_plist_sources(
            "foo.plist", ["a.h", "a.c", "b.c"])
        cachedb.insert_plist_sources(
            "bar.plist", ["c.c", "a.c", "b.h"])

    def test_cachedb_creation(self):
        """Tests if the SQLite database was created"""

        CacheDB(self.test_workspace, True)
        db_path = os.path.join(self.test_workspace, "cache.sqlite")
        self.assertTrue(os.path.isfile(db_path))

    def test_cachedb_insert(self):

        cachedb = CacheDB(self.test_workspace, True)
        self.insert_dummy_data(cachedb)

        self.assertCountEqual(cachedb.get_indexed_plist_files(),
                              ["foo.plist", "bar.plist"])

    def test_cachedb_insert_with_closing(self):

        cachedb = CacheDB(self.test_workspace, True)
        self.insert_dummy_data(cachedb)
        cachedb.close_connection()

        cachedb = CacheDB(self.test_workspace)
        self.assertCountEqual(cachedb.get_indexed_plist_files(),
                              ["foo.plist", "bar.plist"])

    def test_cachedb_querying(self):
        cachedb = CacheDB(self.test_workspace, True)
        self.insert_dummy_data(cachedb)

        self.assertCountEqual(cachedb.plist_query(["a.h"]),
                              ["foo.plist"])
        self.assertCountEqual(cachedb.plist_query(["c.c"]),
                              ["bar.plist"])
        self.assertCountEqual(cachedb.plist_query(["a.c"]),
                              ["foo.plist", "bar.plist"])

    def test_cachedb_querying2(self):
        cachedb = CacheDB(self.test_workspace, True)
        self.insert_dummy_data(cachedb)

        self.assertCountEqual(cachedb.plist_query(["a.h", "c.c"]),
                              ["foo.plist", "bar.plist"])
        self.assertCountEqual(cachedb.plist_query(["a.h", "c.c", "b.h"]),
                              ["foo.plist", "bar.plist"])
        self.assertCountEqual(cachedb.plist_query(["c.c", "b.h"]),
                              ["bar.plist"])
