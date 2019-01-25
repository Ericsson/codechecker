# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
The TU collector collects the files which constitute the translation unit.
These files are compressed in a .zip file. This test intends to check if the
.zip file contains some files which are required to be there for sure.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import nose
import os
import subprocess
import tempfile
import unittest
import zipfile

from tu_collector import tu_collector


class TUCollectorTest(unittest.TestCase):
    def setUp(self):
        PKG_ROOT = os.path.join(os.environ['REPO_ROOT'],
                                'build', 'CodeChecker')
        TU_COLLECTOR_DIR = os.path.join(os.environ['REPO_ROOT'],
                                        'vendor', 'tu_collector')

        self._codechecker_cmd = os.path.join(PKG_ROOT, 'bin', 'CodeChecker')
        self._test_proj_dir = os.path.join(TU_COLLECTOR_DIR,
                                           'tests', 'project')

    def test_file_existence(self):
        source_file = os.path.join(self._test_proj_dir, 'main.cpp')

        build_json = tempfile.mkstemp('.json')[1]
        proc = subprocess.Popen([self._codechecker_cmd, 'log',
                                 '-b', 'g++ -o /dev/null ' + source_file,
                                 '-o', build_json])
        proc.communicate()

        zip_file_name = tempfile.mkstemp(suffix='.zip')[1]
        tu_collector.zip_tu_files(zip_file_name, build_json)

        with zipfile.ZipFile(zip_file_name) as archive:
            files = archive.namelist()

        os.remove(build_json)
        os.remove(zip_file_name)

        self.assertTrue(
            any(map(lambda path: path.endswith('/main.cpp'), files)))
        self.assertTrue(
            any(map(lambda path: path.endswith('/vector'), files)))
