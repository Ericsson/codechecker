#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test storage of analysis statistics.
"""


import json
import os
import subprocess
import unittest
import zipfile

from codechecker_server.tmp import TemporaryDirectory

from libtest import codechecker
from libtest import env


def extract(zip_file, output_dir):
    with zipfile.ZipFile(zip_file, 'r', allowZip64=True) as zipf:
        try:
            zipf.extractall(output_dir)
        except Exception:
            print("Failed to extract received ZIP.")
            import traceback
            traceback.print_exc()
            raise


class TestStorageOfAnalysisStatistics(unittest.TestCase):
    """
    This class tests the CodeChecker analysis statistics storage feature.
    """

    def setUp(self):

        # Get the test workspace.
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        self._reports_dir = self._codechecker_cfg['reportdir']

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._test_dir = os.path.join(self.test_workspace, 'test_files')
        self._product_name = self._codechecker_cfg['viewer_product']
        self._analyzer_stats_dir = os.path.join(self.test_workspace,
                                                'analysis_statistics')
        try:
            os.makedirs(self._test_dir)
        except os.error:
            # Directory already exists.
            pass

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Change working dir to testfile dir so CodeChecker can be run easily.
        self.__old_pwd = os.getcwd()
        os.chdir(self._test_dir)

        self._source_file = os.path.join(self._test_dir, "main.cpp")

        # Init project dir.
        makefile_content = "all:\n\t$(CXX) -c main.cpp -o /dev/null\n"
        project_info_content = {
            "name": "hello",
            "clean_cmd": "",
            "build_cmd": "make"
        }

        makefile = os.path.join(self._test_dir, 'Makefile')
        with open(makefile, 'w', encoding="utf-8", errors="ignore") as make_f:
            make_f.write(makefile_content)

        project_info = os.path.join(self._test_dir, 'project_info.json')
        with open(project_info, 'w',
                  encoding="utf-8", errors="ignore") as info_f:
            json.dump(project_info_content, info_f)

        self.sources = ["""
int main()
{
  return 1 / 0; // Division by zero
}""", """
int main()
{
  return 0;
  xxx // Will cause a compilation error
}"""]

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)

    def _create_source_file(self, version):
        with open(self._source_file, 'w',
                  encoding='utf-8', errors='ignore') as source_f:
            source_f.write(self.sources[version])

        build_json = os.path.join(self._test_dir, "build.json")

        # Create a compilation database.
        build_log = [
            {
                "directory": self.test_workspace,
                "command": "gcc -c " + self._source_file,
                "file": self._source_file
            },
            {
                "directory": self.test_workspace,
                "command": "clang -c " + self._source_file,
                "file": self._source_file
            }
        ]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self._reports_dir]

        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._test_dir,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        codechecker.store(self._codechecker_cfg, 'example')

    def _check_analyzer_statistics_zip(self):
        """
        Checks if compilation database file and failed zips which exists in the
        report directory can be found in the uploaded analyzer statistics zip.
        """
        product_stat_dir = os.path.join(self._analyzer_stats_dir,
                                        self._product_name)
        # Check that directory for product under analyzer statistics dir
        # has been created.
        self.assertTrue(os.path.exists(product_stat_dir))

        # Test that the product stat directory is not empty.
        self.assertTrue(os.listdir(product_stat_dir))

        zip_file = os.path.join(product_stat_dir, 'example.zip')
        with TemporaryDirectory() as zip_dir:
            extract(zip_file, zip_dir)

            # Check that analyzer files exist in the uploaded zip.
            analyzer_files = ['compile_cmd.json',
                              'compiler_info.json',
                              'metadata.json']
            for analyzer_file in analyzer_files:
                orig_file = os.path.join(self._reports_dir, analyzer_file)
                uploaded_file = os.path.join(zip_dir, orig_file.lstrip(os.sep))
                self.assertTrue(os.path.exists(uploaded_file))

            # Check that failed zips exist in the uploaded zip.
            orig_failed_dir = os.path.join(self._reports_dir,
                                           'failed')
            if os.path.exists(orig_failed_dir):
                failed_dir = os.path.join(zip_dir, orig_failed_dir)
                self.assertTrue(os.path.exists(failed_dir))

    def test_storage_empty_report_dir(self):
        """
        Check that storing an empty report directory will not store analyzer
        statistics information on the server.
        """
        # Remove analyzer statistics directory if it exists before store.
        if os.path.exists(self._analyzer_stats_dir):
            os.removedirs(self._analyzer_stats_dir)

        # Remove reports directory if it exists and create an empty one.
        if os.path.exists(self._reports_dir):
            os.removedirs(self._reports_dir)

        os.mkdir(self._reports_dir)

        # Trying to store the empty directory.
        codechecker.store(self._codechecker_cfg, 'example')

        # Check that we do not store any analyzer statistic information.
        self.assertFalse(os.path.exists(self._analyzer_stats_dir))

    def test_storage_simple_report_dir(self):
        """
        Checks if compilation database can be found in the uploaded zip.
        """
        self._create_source_file(0)
        self._check_analyzer_statistics_zip()

    def test_storage_failed_zips(self):
        """
        Checks if compilation database and failed zips can be found in the
        uploaded zip.
        """
        run_ids = None

        # Check if there is no failed files in the database yet.
        num_of_failed_files = self._cc_client.getFailedFilesCount(run_ids)
        self.assertEqual(num_of_failed_files, 0)

        failed_files = self._cc_client.getFailedFiles(run_ids)
        self.assertEqual(len(failed_files), 0)

        # Store the failure.
        self._create_source_file(1)
        self._check_analyzer_statistics_zip()

        # Check the failed files again in the database.
        num_of_failed_files = self._cc_client.getFailedFilesCount(run_ids)
        self.assertEqual(num_of_failed_files, 2)

        failed_files = self._cc_client.getFailedFiles(run_ids)
        self.assertEqual(len(failed_files), 1)
        self.assertTrue(self._source_file in failed_files)

        failed_file_info = failed_files[self._source_file]
        self.assertEqual(len(failed_file_info), 1)
        self.assertEqual(failed_file_info[0].runName, 'example')
