#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test storing test coverage data and querying it through the API.
"""

import os
import shutil
import unittest

from codechecker_api.python.DBAccess_v6.ttypes import ReportFilter, \
    RunFilter
from codechecker_api.python.DBAccess_v6.constants import MAX_QUERY_SIZE
from codechecker_api.python.shared.ttypes import RequestFailed

from codechecker_report_converter.analyzers.clang_tidy import \
    analyzer_result as tidy_result
from codechecker_report_converter.analyzers.lcov import \
    analyzer_result as lcov_result
from codechecker_report_converter.report import coverage

from libtest import codechecker
from libtest import env


# Source files of the test project. The keys are relative to the project
# directory.
SOURCES = {
    'main.c': "int util(int);\n"
              "int main() {\n"
              "  int x = util(1);\n"
              "  return x / 0;\n"
              "}\n",
    'lib/util.c': "int util(int x) {\n"
                  "  if (x < 0)\n"
                  "    return 0;\n"
                  "\n"
                  "  return x;\n"
                  "}\n",
    'lib/extra.c': "int extra() {\n"
                   "  return 42;\n"
                   "}\n"
}

# LCOV tracefile which refers to the source files of the test project.
# '$DIR$' is replaced with the project directory. 'lib/missing.c' does not
# exist, so its coverage must not be stored.
LCOV_FULL = """\
TN:
SF:$DIR$/main.c
FN:2,main
FNDA:1,main
DA:2,1
DA:3,1
DA:4,0
end_of_record
SF:$DIR$/lib/util.c
FNF:2
FNH:1
DA:1,1
DA:2,1
DA:3,0
DA:5,4
end_of_record
SF:$DIR$/lib/missing.c
DA:1,1
end_of_record
"""

LCOV_EXTRA = """\
TN:
SF:$DIR$/lib/extra.c
FN:1,extra
FNDA:0,extra
DA:1,0
DA:2,0
end_of_record
"""

# A clang-tidy output which contains one report in 'main.c'.
TIDY_OUTPUT = \
    "$DIR$/main.c:4:12: warning: Division by zero " \
    "[clang-analyzer-core.DivideZero]\n" \
    "  return x / 0;\n" \
    "           ^\n"


class TestCoverage(unittest.TestCase):
    """ Test storing and querying test coverage data. """

    def setup_class(self):
        """ Setup the environment for testing test coverage. """

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('coverage')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'run_names': []
        }

        # The authentication enabled server is used, so the permission
        # handling of the API functions can be tested too.
        server_access = codechecker.start_or_get_server(auth_required=True)
        server_access['viewer_product'] = 'coverage'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        codechecker_cfg.update(server_access)

        env.export_test_cfg(TEST_WORKSPACE,
                            {'codechecker_cfg': codechecker_cfg})

    def teardown_class(self):
        """ Clean up after the test. """
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):
        self._test_workspace = os.environ['TEST_WORKSPACE']
        self._codechecker_cfg = env.import_codechecker_cfg(
            self._test_workspace)

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Each test case works in its own project directory.
        self._proj_dir = os.path.join(self._test_workspace, method.__name__)
        shutil.rmtree(self._proj_dir, ignore_errors=True)

        for rel_path, content in SOURCES.items():
            file_path = os.path.join(self._proj_dir, rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def __path(self, rel_path: str) -> str:
        """ Absolute path of a source file of the test project. """
        return os.path.join(self._proj_dir, rel_path)

    def __write_input(self, file_name: str, template: str) -> str:
        """ Write an input file of report-converter to the project dir. """
        file_path = os.path.join(self._proj_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template.replace('$DIR$', self._proj_dir))
        return file_path

    def __coverage_dir(self, name: str, lcov_template: str) -> str:
        """
        Create a report directory which contains only test coverage data,
        the same way as 'report-converter -t lcov' does.
        """
        info_file = self.__write_input(name + '.info', lcov_template)
        out_dir = os.path.join(self._proj_dir, name)
        self.assertTrue(lcov_result.AnalyzerResult().transform(
            [info_file], out_dir, 'plist'))
        self.assertTrue(os.path.isfile(
            coverage.get_coverage_file_path(out_dir)))
        return out_dir

    def __report_dir(self) -> str:
        """ Create a report directory which contains a single report. """
        tidy_file = self.__write_input('tidy.out', TIDY_OUTPUT)
        out_dir = os.path.join(self._proj_dir, 'reports')
        os.makedirs(out_dir, exist_ok=True)
        self.assertTrue(tidy_result.AnalyzerResult().transform(
            [tidy_file], out_dir, 'plist'))
        return out_dir

    def __store(self, run_name: str, report_dirs: list[str],
                trim_path_prefix: str | None = None) -> int:
        """ Store the given report directories and return the run id. """
        cfg = dict(self._codechecker_cfg)
        cfg['reportdir'] = report_dirs
        if trim_path_prefix:
            cfg['trim_path_prefix'] = trim_path_prefix

        self.assertEqual(codechecker.store(cfg, run_name), 0,
                         f"Failed to store run '{run_name}'.")

        runs = self._cc_client.getRunData(
            RunFilter(names=[run_name], exactMatch=True),
            MAX_QUERY_SIZE, 0, None)
        self.assertEqual(len(runs), 1)
        return runs[0].runId

    def __coverages(self, run_id: int) -> dict:
        """ Returns the coverage summaries of a run by file path. """
        result = {}
        for cov in self._cc_client.getFileCoverages([run_id]):
            self.assertEqual(cov.runId, run_id)
            result[cov.filePath] = cov
        return result

    def test_store_reports_and_coverage(self):
        """
        Store analyzer reports and test coverage data together, then check
        the coverage summary and the line coverage of each file.
        """
        run_id = self.__store(
            'coverage_full',
            [self.__report_dir(), self.__coverage_dir('cov', LCOV_FULL)])

        # The analyzer report is stored as usual.
        self.assertEqual(self._cc_client.getRunResultCount(
            [run_id], ReportFilter(), None), 1)

        covs = self.__coverages(run_id)

        # The missing source file is skipped.
        self.assertEqual(set(covs),
                         {self.__path('main.c'), self.__path('lib/util.c')})

        main = covs[self.__path('main.c')]
        self.assertEqual((main.linesFound, main.linesHit), (3, 2))
        self.assertEqual((main.functionsFound, main.functionsHit), (1, 1))

        util = covs[self.__path('lib/util.c')]
        self.assertEqual((util.linesFound, util.linesHit), (4, 3))
        self.assertEqual((util.functionsFound, util.functionsHit), (2, 1))

        line_cov = self._cc_client.getFileLineCoverage(run_id, main.fileId)
        self.assertEqual(line_cov.runId, run_id)
        self.assertEqual(line_cov.fileId, main.fileId)
        self.assertEqual(line_cov.coveredLines, [2, 3])
        self.assertEqual(line_cov.uncoveredLines, [4])

        line_cov = self._cc_client.getFileLineCoverage(run_id, util.fileId)
        self.assertEqual(line_cov.coveredLines, [1, 2, 5])
        self.assertEqual(line_cov.uncoveredLines, [3])

        # The source code of a file with coverage is available.
        source = self._cc_client.getSourceFileData(util.fileId, True, None)
        self.assertEqual(source.fileContent, SOURCES['lib/util.c'])

    def test_store_coverage_only(self):
        """
        Store a report directory which contains only test coverage data.
        The source files are uploaded by the client, even if no report
        refers to them.
        """
        run_id = self.__store(
            'coverage_only', [self.__coverage_dir('cov', LCOV_EXTRA)])

        self.assertEqual(self._cc_client.getRunResultCount(
            [run_id], ReportFilter(), None), 0)

        covs = self.__coverages(run_id)
        self.assertEqual(list(covs), [self.__path('lib/extra.c')])

        extra = covs[self.__path('lib/extra.c')]
        self.assertEqual((extra.linesFound, extra.linesHit), (2, 0))
        self.assertEqual((extra.functionsFound, extra.functionsHit), (1, 0))

        source = self._cc_client.getSourceFileData(extra.fileId, True, None)
        self.assertEqual(source.fileContent, SOURCES['lib/extra.c'])

    def test_foreign_coverage_file_is_ignored(self):
        """
        A 'coverage/coverage.json' file of another tool (e.g. coverage.py) in
        a report directory does not make the store fail, it is just not
        stored.
        """
        report_dir = self.__report_dir()
        foreign_file = coverage.get_coverage_file_path(report_dir)
        os.makedirs(os.path.dirname(foreign_file), exist_ok=True)
        with open(foreign_file, 'w', encoding='utf-8') as f:
            f.write('{"meta": {"format": 2}, "files": {}, "totals": {}}')

        run_id = self.__store('coverage_foreign', [report_dir])

        self.assertEqual(self._cc_client.getRunResultCount(
            [run_id], ReportFilter(), None), 1)
        self.assertEqual(self.__coverages(run_id), {})

    def test_coverage_file_in_conf_dir_is_ignored(self):
        """
        A 'coverage.json' file in the 'conf' directory of a report directory
        is not test coverage data of the report directory. It is uploaded
        with the 'conf' directory, but the server does not parse it.
        """
        cov_dir = self.__coverage_dir('cov', LCOV_EXTRA)
        conf_dir = os.path.join(cov_dir, 'conf')
        os.makedirs(conf_dir, exist_ok=True)
        with open(os.path.join(conf_dir, coverage.COVERAGE_FILE_NAME), 'w',
                  encoding='utf-8') as f:
            f.write('{"files": {}}')

        run_id = self.__store('coverage_conf', [cov_dir])

        self.assertEqual(list(self.__coverages(run_id)),
                         [self.__path('lib/extra.c')])

    def test_runs_are_isolated(self):
        """
        The coverage of a source file is stored separately for each run, even
        if the runs share the same source file.
        """
        cov_dir = self.__coverage_dir('cov_full', LCOV_FULL)
        run_1 = self.__store('coverage_isolated_1', [cov_dir])

        # The second run contains different coverage of the same file.
        run_2 = self.__store('coverage_isolated_2', [self.__coverage_dir(
            'cov_main', "SF:$DIR$/main.c\nDA:2,0\nDA:3,0\nend_of_record\n")])

        main_1 = self.__coverages(run_1)[self.__path('main.c')]
        main_2 = self.__coverages(run_2)[self.__path('main.c')]

        # The two runs share the same file.
        self.assertEqual(main_1.fileId, main_2.fileId)
        self.assertEqual((main_1.linesFound, main_1.linesHit), (3, 2))
        self.assertEqual((main_2.linesFound, main_2.linesHit), (2, 0))

        self.assertEqual(self._cc_client.getFileLineCoverage(
            run_2, main_2.fileId).coveredLines, [])
        self.assertEqual(self._cc_client.getFileLineCoverage(
            run_1, main_1.fileId).coveredLines, [2, 3])

        # Coverage of multiple runs can be queried at once.
        both = self._cc_client.getFileCoverages([run_1, run_2])
        self.assertEqual(sorted({c.runId for c in both}),
                         sorted([run_1, run_2]))
        self.assertEqual(len(both), 3)

        # A file which has no coverage in a run gives empty lists.
        util_id = self.__coverages(run_1)[self.__path('lib/util.c')].fileId
        line_cov = self._cc_client.getFileLineCoverage(run_2, util_id)
        self.assertEqual(line_cov.coveredLines, [])
        self.assertEqual(line_cov.uncoveredLines, [])

    def test_restore_replaces_coverage(self):
        """
        Storing a run again with coverage data replaces its coverage. Storing
        it without coverage data keeps the previous coverage.
        """
        run_name = 'coverage_restore'
        run_id = self.__store(
            run_name, [self.__coverage_dir('cov_full', LCOV_FULL)])
        self.assertEqual(len(self.__coverages(run_id)), 2)

        # Replace the coverage with the coverage of a single other file.
        self.assertEqual(self.__store(
            run_name, [self.__coverage_dir('cov_extra', LCOV_EXTRA)]),
            run_id)
        self.assertEqual(list(self.__coverages(run_id)),
                         [self.__path('lib/extra.c')])

        # A store without coverage data keeps the coverage of the run.
        self.assertEqual(self.__store(run_name, [self.__report_dir()]),
                         run_id)
        self.assertEqual(list(self.__coverages(run_id)),
                         [self.__path('lib/extra.c')])

        # A coverage file without any stored source file clears the coverage
        # of the run, so no outdated coverage is shown.
        self.assertEqual(self.__store(run_name, [self.__coverage_dir(
            'cov_missing', "SF:$DIR$/lib/missing.c\nDA:1,1\nend_of_record\n"
        )]), run_id)
        self.assertEqual(self.__coverages(run_id), {})

    def test_trim_path_prefix(self):
        """ The '--trim-path-prefix' option is applied to coverage too. """
        run_id = self.__store(
            'coverage_trimmed', [self.__coverage_dir('cov', LCOV_FULL)],
            trim_path_prefix=self._proj_dir)

        self.assertEqual(set(self.__coverages(run_id)),
                         {'main.c', 'lib/util.c'})

    def test_run_deletion_removes_coverage(self):
        """ Removing a run removes its coverage data. """
        run_id = self.__store(
            'coverage_delete', [self.__coverage_dir('cov', LCOV_FULL)])
        self.assertEqual(len(self.__coverages(run_id)), 2)

        self.assertTrue(self._cc_client.removeRun(run_id, None))

        self.assertEqual(self._cc_client.getFileCoverages([run_id]), [])

    def test_no_view_permission(self):
        """
        Users without the PRODUCT_VIEW permission can't query coverage data.
        """
        auth_client = env.setup_auth_client(
            self._test_workspace, session_token='_PROHIBIT')
        token = auth_client.performLogin(
            "Username:Password", "permission_view_user:pvu")
        self.assertIsNotNone(token)

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=token)

        try:
            with self.assertRaises(RequestFailed):
                client.getFileCoverages([])

            with self.assertRaises(RequestFailed):
                client.getFileLineCoverage(1, 1)
        finally:
            env.setup_auth_client(self._test_workspace,
                                  session_token=token).destroySession()
