# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import glob
import html
import json
import os
import re
import shutil
import unittest

from typing import ClassVar

from libtest import env

from codechecker_report_converter.report.output.html import \
    html as report_to_html
from codechecker_report_converter.report import BugPathEvent, File, \
    Report, report_file, reports as reports_helper


def get_title(html_content: str) -> str:
    """ Return the raw content of the <title> tag of the given HTML. """
    titles = re.findall(r'<title>(.*?)</title>', html_content)
    assert len(titles) == 1, titles
    return titles[0]


def read_file(file_path: str) -> str:
    """ Return the content of the given file. """
    with open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
        return f.read()


def get_project_path(test_project) -> str:
    """ Return project path for the given project. """
    return os.path.join(env.test_proj_root(), test_project)


class PlistToHtmlTest(unittest.TestCase):
    test_workspace: ClassVar[str]
    layout_dir: ClassVar[str]

    def setup_class(self):
        """ Initialize test files. """

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('plist_to_html')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        self.test_workspace = os.environ['TEST_WORKSPACE']
        self.layout_dir = os.environ['LAYOUT_DIR']

        test_file_dir_path = os.path.join(self.test_workspace, "test_files")

        test_projects = ['notes', 'macros', 'simple', 'inclusion']
        for test_project in test_projects:
            test_project_path = os.path.join(test_file_dir_path, test_project)
            shutil.copytree(get_project_path(test_project), test_project_path)

            for test_file in os.listdir(test_project_path):
                if test_file.endswith(".plist"):
                    test_file_path = os.path.join(test_project_path, test_file)
                    with open(test_file_path, 'r+',
                              encoding='utf-8', errors='ignore') as plist_file:
                        content = plist_file.read()
                        new_content = content.replace("$FILE_PATH$",
                                                      test_project_path)
                        plist_file.seek(0)
                        plist_file.truncate()
                        plist_file.write(new_content)

    def teardown_class(self):
        """ Delete the workspace associated with this test. """

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def __test_html_builder(self, proj: str) -> str:
        """
        Test building html file from the given proj's plist file.
        """
        html_builder = report_to_html.HtmlBuilder(self.layout_dir)

        proj_dir = os.path.join(self.test_workspace, 'test_files', proj)
        output_dir = os.path.join(proj_dir, 'html')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        processed_path_hashes = set()
        for file_path in glob.glob(os.path.join(proj_dir, f"*.plist")):
            file_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, f"{file_name}.html")

            reports = report_file.get_reports(file_path)
            reports = reports_helper.skip(
                reports, processed_path_hashes)

            report_to_html.convert(
                file_path, reports, output_dir, html_builder)

            html_file_exists = os.path.exists(output_path)
            if reports:
                self.assertTrue(html_file_exists)
            else:
                self.assertFalse(html_file_exists)

        html_builder.create_index_html(output_dir)
        html_builder.create_statistics_html(output_dir)

        index_html = os.path.join(output_dir, 'index.html')
        self.assertTrue(os.path.exists(index_html))

        return output_dir

    def test_get_report_data_notes(self):
        """ Get report data for plist which contains notes. """
        proj_notes = os.path.join(self.test_workspace, 'test_files', 'notes')
        plist_file = os.path.join(proj_notes, 'notes.plist')

        reports = report_file.get_reports(plist_file)

        html_builder = report_to_html.HtmlBuilder(self.layout_dir)
        html_reports, files = html_builder._get_html_reports(reports)

        self.assertEqual(len(files), 1)
        self.assertEqual(len(html_reports), 1)

        report = html_reports[0]
        self.assertEqual(len(report['notes']), 1)
        self.assertEqual(len(report['macros']), 0)
        self.assertGreaterEqual(len(report['events']), 1)
        self.assertEqual(report['checker']['name'], 'alpha.clone.CloneChecker')

    def test_get_report_data_macros(self):
        """ Get report data for plist which contains macro expansion. """
        proj_macros = os.path.join(self.test_workspace, 'test_files', 'macros')
        plist_file = os.path.join(proj_macros, 'macros.plist')

        reports = report_file.get_reports(plist_file)

        html_builder = report_to_html.HtmlBuilder(self.layout_dir)
        html_reports, files = html_builder._get_html_reports(reports)

        self.assertEqual(len(files), 1)
        self.assertEqual(len(html_reports), 1)

        report = html_reports[0]
        self.assertEqual(len(reports), 1)

        report = html_reports[0]
        self.assertEqual(len(report['notes']), 0)
        self.assertEqual(len(report['macros']), 1)
        self.assertGreaterEqual(len(report['events']), 1)
        self.assertEqual(report['checker']['name'], 'core.NullDereference')

    def test_get_report_data_simple(self):
        """ Get report data for plist which contains simple reports. """
        proj_simple = os.path.join(self.test_workspace, 'test_files', 'simple')
        plist_file = os.path.join(proj_simple, 'simple.plist')

        reports = report_file.get_reports(plist_file)

        html_builder = report_to_html.HtmlBuilder(self.layout_dir)
        html_reports, files = html_builder._get_html_reports(reports)

        self.assertEqual(len(files), 1)
        self.assertEqual(len(html_reports), 2)

        dead_stores = [r for r in html_reports if
                       r['checker']['name'] == 'deadcode.DeadStores'][0]
        self.assertEqual(len(dead_stores['notes']), 0)
        self.assertEqual(len(dead_stores['macros']), 0)
        self.assertGreaterEqual(len(dead_stores['events']), 1)

        divide_zero = [r for r in html_reports if
                       r['checker']['name'] == 'core.DivideZero'][0]
        self.assertEqual(len(divide_zero['notes']), 0)
        self.assertEqual(len(divide_zero['macros']), 0)
        self.assertGreaterEqual(len(divide_zero['events']), 1)

    def test_html_builder(self):
        """ Test building html files from plist files on multiple projects. """
        self.__test_html_builder('notes')
        self.__test_html_builder('macros')
        self.__test_html_builder('simple')

    def test_html_for_inclusion(self):
        """ Test generating html files for header inclusions. """
        output_dir = self.__test_html_builder('inclusion')
        index_html = os.path.join(output_dir, "index.html")

        with open(index_html, 'r', encoding="utf-8", errors="ignore") as f:
            content = f.read()

            # There are 3 reports in the test file.
            self.assertEqual(len(re.findall('"link": "', content)), 3)
            # The links should be relative so the static HTML folder is
            # portable.
            self.assertNotIn('"link": "/', content)

    def test_report_title_in_report_data(self):
        """ Every report gets a "file:line [checker] - CodeChecker" title. """
        proj_simple = os.path.join(self.test_workspace, 'test_files', 'simple')
        plist_file = os.path.join(proj_simple, 'simple.plist')

        reports = report_file.get_reports(plist_file)

        html_builder = report_to_html.HtmlBuilder(self.layout_dir)
        html_reports, _ = html_builder._get_html_reports(reports)

        self.assertEqual(len(html_reports), len(reports))
        for report, html_report in zip(reports, html_reports):
            self.assertEqual(
                html_report['title'],
                f"{os.path.basename(report.file.path)}:{report.line} "
                f"[{report.checker_name}] - CodeChecker")

    def test_page_titles(self):
        """ Generated pages set their title according to their content. """
        output_dir = self.__test_html_builder('simple')

        self.assertEqual(
            get_title(read_file(os.path.join(output_dir, 'index.html'))),
            "Reports - CodeChecker")
        self.assertEqual(
            get_title(read_file(os.path.join(output_dir, 'statistics.html'))),
            "Statistics - CodeChecker")

        # The per-file page initially shows the title of its first report.
        plist_file = os.path.join(
            self.test_workspace, 'test_files', 'simple', 'simple.plist')
        first_report = report_file.get_reports(plist_file)[0]
        self.assertEqual(
            get_title(read_file(
                os.path.join(output_dir, 'simple.plist.html'))),
            f"{os.path.basename(first_report.file.path)}:"
            f"{first_report.line} [{first_report.checker_name}] - "
            "CodeChecker")

    def test_title_escaping(self):
        """
        Special characters in the title are HTML-escaped in the <title> tag,
        are not HTML-escaped in the report data (it is set through
        document.title) and can't break out of the <script> tag.
        """
        proj_dir = os.path.join(self.test_workspace, 'test_files', 'escape')
        os.makedirs(proj_dir, exist_ok=True)
        source_path = os.path.join(proj_dir, 'a&b.c')
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write("int main() {\n  return 1 / 0;\n}\n")

        source_file = File(source_path)
        checker_name = 'x</script><b>"y\''
        report = Report(
            source_file, 2, 12, "Division by zero", checker_name,
            report_hash='abc',
            bug_path_events=[BugPathEvent(
                "Division by zero", source_file, 2, 12)])

        output_path = os.path.join(proj_dir, 'escape.plist.html')
        html_builder = report_to_html.HtmlBuilder(self.layout_dir)
        html_builder.create(output_path, [report])

        content = read_file(output_path)
        expected_title = f"a&b.c:2 [{checker_name}] - CodeChecker"

        self.assertEqual(get_title(content), html.escape(expected_title))
        self.assertNotIn('</script><b>', content)

        report_data = re.search(
            r'var data = (.*);\n', content).group(1)
        self.assertEqual(
            json.loads(report_data)['reports'][0]['title'], expected_title)
