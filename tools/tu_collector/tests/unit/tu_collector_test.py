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


import inspect
import json
import os
import tempfile
import unittest
import zipfile

from tu_collector import tu_collector


class TUCollectorTest(unittest.TestCase):
    def setUp(self):
        self._test_proj_dir = os.path.abspath(os.environ['TEST_PROJ'])

        compile_json = os.path.join(self._test_proj_dir,
                                    'compile_command.json')

        with open(compile_json, mode='rb') as cmpjson:
            self.compile_cmd_data = json.load(cmpjson)

        # Overwrite the directory paths.
        # This is needed because the tests run on different machines
        # so the directory path changes in each case.
        for cmp in self.compile_cmd_data:
            cmp['directory'] = self._test_proj_dir

    def test_file_existence(self):
        zip_file_name = tempfile.mkstemp(suffix='.zip')[1]
        tu_collector.zip_tu_files(zip_file_name, self.compile_cmd_data)

        with zipfile.ZipFile(zip_file_name) as archive:
            files = archive.namelist()

        os.remove(zip_file_name)

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'main.c')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'main.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'vector')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'hello.c')) for path in files]))

        self.assertIn('compilation_database.json', files)

    def test_ctu_collection(self):
        with tempfile.TemporaryDirectory() as ctu_deps_dir:
            ctu_action = next(filter(lambda ba: ba['file'] == 'ctu.cpp',
                                     self.compile_cmd_data))

            hash_fun = dict(
                inspect.getmembers(tu_collector))['__analyzer_action_hash']

            with open(os.path.join(ctu_deps_dir, hash_fun(ctu_action)), 'w') \
                    as f:
                f.write(os.path.join(self._test_proj_dir, 'zero.cpp'))

            with tempfile.NamedTemporaryFile(suffix='.zip') as zip_file:
                tu_collector.zip_tu_files(zip_file.name, self.compile_cmd_data,
                                          file_filter='ctu.cpp',
                                          ctu_deps_dir=ctu_deps_dir)

                with zipfile.ZipFile(zip_file.name) as archive:
                    files = archive.namelist()

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'vector')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'ctu.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'zero.cpp')) for path in files]))

        self.assertTrue(any(
            [path.endswith(os.path.join('/', 'zero.h')) for path in files]))
