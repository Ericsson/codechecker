# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
The TU collector collects the files which constitute the translation unit.
These files are compressed in a .zip file. This test intends to check if the
.zip file contains some files which are required to be there for sure.
"""


import json
import os
import tempfile
import unittest
import zipfile

from tu_collector import tu_collector


class TUCollectorTest(unittest.TestCase):
    def setUp(self):

        dir_path = os.path.dirname(os.path.realpath(__file__))
        self._test_proj_dir = os.path.join(dir_path, 'project')

    def test_file_existence(self):

        compile_json = os.path.join(self._test_proj_dir,
                                    'compile_command.json')

        compile_cmd_data = {}
        with open(compile_json, mode='rb') as cmpjson:
            compile_cmd_data = json.load(cmpjson)

        # Overwrite the directory paths.
        # This is needed because the tests run on different machines
        # so the directory path changes in each case.
        for cmp in compile_cmd_data:
            cmp['directory'] = self._test_proj_dir

        zip_file_name = tempfile.mkstemp(suffix='.zip')[1]
        tu_collector.zip_tu_files(zip_file_name, compile_cmd_data)

        with zipfile.ZipFile(zip_file_name) as archive:
            files = archive.namelist()

        os.remove(zip_file_name)

        self.assertTrue(
            any([path.endswith(os.path.join('/', 'main.c')) for path in files]))
        self.assertTrue(
            any([path.endswith(os.path.join('/', 'main.cpp')) for path in files]))
        self.assertTrue(
            any([path.endswith(os.path.join('/', 'vector')) for path in files]))
        self.assertTrue(
            any([path.endswith(os.path.join('/', 'hello.c')) for path in files]))
        self.assertIn('compilation_database.json', files)
