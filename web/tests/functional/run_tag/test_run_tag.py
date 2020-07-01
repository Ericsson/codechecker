#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Run tag function test. """


import json
import os
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Order, \
    ReportFilter, RunSortMode, RunSortType

from libtest import codechecker
from libtest import env


class TestRunTag(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        self._test_dir = os.path.join(self.test_workspace, 'test_files')

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

        self._source_file = "main.cpp"

        # Init project dir.
        makefile = "all:\n\t$(CXX) -c main.cpp -o /dev/null\n"
        project_info = {
            "name": "test_run_tag",
            "clean_cmd": "",
            "build_cmd": "make"
        }

        with open(os.path.join(self._test_dir, 'Makefile'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(makefile)
        with open(os.path.join(self._test_dir, 'project_info.json'), 'w',
                  encoding="utf-8", errors="ignore") as f:
            json.dump(project_info, f)

        self.sources = ["""
int main()
{
  sizeof(42);
  sizeof(43);
}""", """
int main()
{
  sizeof(43);
  sizeof(44);
  sizeof(45);
}""", """
int main()
{
  sizeof(45);
}"""]
        self.tags = ['v1.0', 'v1.1', 'v1.2']

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)

    def _create_source_file(self, version, run_name):
        with open(os.path.join(self._test_dir, self._source_file), 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write(self.sources[version])

        self._codechecker_cfg['tag'] = self.tags[version]
        codechecker.check_and_store(self._codechecker_cfg,
                                    run_name, self._test_dir)

    def __get_run_tag_counts(self, run_id, limit=None, offset=0):
        """
        Get run history tag for the given run.
        """
        test_run_tags = \
            self._cc_client.getRunHistoryTagCounts([run_id], None, None,
                                                   limit, offset)

        self.assertGreater(len(test_run_tags), 0)

        return test_run_tags

    def __reports_by_tag(self, tag_ids):
        report_filter = ReportFilter(runTag=tag_ids)
        return self._cc_client.getRunResults(None, 100, 0, [],
                                             report_filter, None, False)

    def __check_reports(self, tag):
        reports = self.__reports_by_tag([tag.id])
        self.assertEqual(tag.count, len(reports))

        for report in reports:
            self.assertLessEqual(report.detectedAt, tag.time)

    def test_file_change(self):
        """
        This tests the change of the detection status of bugs when the file
        content changes.

        CHECK 1 ----- CHECK 2 --------- CHECK 3 ---------- CHECK 4
           |             |                 |                  |
          42             |                 |                  |
           |             |                 |                  |
          43             |                 |                  |
                         |                 |                  |
                        42 ---------- [RESOLVED]              |
                         |                 |                  |
                        43 --------- [UNRESOLVED] ------- [RESOLVED]
                                           |                  |
                                          44 ------------ [RESOLVED]
                                           |                  |
                                          45 ----------- [UNRESOLVED]
        """

        # ######################## 1st check #################################

        # Check the first file version.
        self._create_source_file(0, 'test_run_tag')

        # ######################## 2nd check #################################

        # Check the first file versions again with different run name to see
        # that set a run tag filter will filter the reports by the run id.
        self._create_source_file(0, 'test_run_tag_update')

        # Get the run names which belong to this test

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        runs = self._cc_client.getRunData(None, None, 0, sort_mode)
        test_run_ids = [run.runId for run in runs]

        self.assertEqual(len(test_run_ids), 2)

        run_id = test_run_ids[1]
        test_run_tags = self.__get_run_tag_counts(run_id, 100, 0)
        run_tags_v0 = [t for t in test_run_tags if t.name == self.tags[0]]

        self.assertEqual(len(run_tags_v0), 1)
        run_tags_v0 = run_tags_v0[0]

        reports = self.__reports_by_tag([run_tags_v0.id])
        self.assertEqual(run_tags_v0.count, len(reports))

        # ######################## 3rd check #################################

        # Check the second file version.
        self._create_source_file(1, 'test_run_tag_update')

        # We do not show future bugs for later tags.
        reports = self.__reports_by_tag([run_tags_v0.id])
        self.assertEqual(run_tags_v0.count, len(reports))

        test_run_tags = self.__get_run_tag_counts(run_id)
        run_tags_v1 = [t for t in test_run_tags if t.name == self.tags[1]]

        self.assertEqual(len(run_tags_v1), 1)
        run_tags_v1 = run_tags_v1[0]
        self.__check_reports(run_tags_v1)

        # ######################## 4th check #################################

        # Check the third file version.
        self._create_source_file(2, 'test_run_tag_update')

        # We do not show future bugs for later tags.
        reports = self.__reports_by_tag([run_tags_v0.id])
        self.assertEqual(run_tags_v0.count, len(reports))

        test_run_tags = self.__get_run_tag_counts(run_id)
        run_tags_v2 = [t for t in test_run_tags if t.name == self.tags[2]]

        self.assertEqual(len(run_tags_v2), 1)
        run_tags_v2 = run_tags_v2[0]
        self.__check_reports(run_tags_v2)
