# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import sqlite3
import itertools
import os
from typing import List


class CacheDB:
    """
    SQLite database located in the report directory,
    designed to speed up the parsing process.
    """

    __sqlitedb_path: str
    __con: sqlite3.Connection
    __cur: sqlite3.Cursor

    def __init__(self, report_dir: str, clean: bool = False):
        """
        Initiates the cache database and creates the necessary tables.

        Args:
            report_dir (str): path to the report directory
            clean (bool): If set to True, the previous database
                will be dropped and a new one is created.
        """
        self.__sqlitedb_path = os.path.join(report_dir, "cache.sqlite")

        if clean and os.path.exists(self.__sqlitedb_path):
            os.remove(self.__sqlitedb_path)

        self.__create_connection()

    def __create_connection(self):
        self.__con = sqlite3.connect(self.__sqlitedb_path)
        self.__cur = self.__con.cursor()
        self.__create_tables()

    def close_connection(self):
        """
        Closes the connection to the cache database and writes
        changes to the disk.
        """
        self.__con.close()

    def __table_exists(self, name: str) -> bool:
        res = self.__cur.execute("SELECT name FROM sqlite_master WHERE name=?",
                                 [name])
        return res.fetchone() is not None

    def __create_tables(self):
        if not self.__table_exists("plist_lookup"):
            self.__cur.execute("CREATE TABLE plist_lookup"
                               "(plist TEXT, source TEXT)")

    def insert_plist_sources(self, plist_file: str, source_files: List[str]):
        """
        Inserts the plist file and its associated source files into the
        cache database. These source files are located in the 'files' section
        of an individual plist file.

        Args:
            plist_file (str): path to the plist file
            source_files (List[str]): list of source files mapped to
                the plist file
        """

        data = list(zip(itertools.repeat(plist_file), source_files))
        self.__cur.executemany("INSERT INTO plist_lookup VALUES(?, ?)", data)
        self.__con.commit()

    def plist_query(self, source_files: List[str]) -> List[str]:
        """
        Returns all plist files associated with any of the given source files
        by querying the cache database.

        Args:
            source_files (List[str]): list of source files to be looked up
                from the cache database.
        """

        placeholders = ','.join('?' for _ in source_files)
        res = self.__cur.execute("SELECT plist FROM plist_lookup WHERE source"
                                 f" IN ({placeholders})", source_files)
        return list(set(map(lambda e: e[0], res)))

    def get_indexed_plist_files(self) -> List[str]:
        """
        Returns already indexed plist files from the cache database.
        """
        res = self.__cur.execute("SELECT DISTINCT plist FROM plist_lookup")
        return list(map(lambda e: e[0], res))
