# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import io
import json
import logging
import os
import shutil
import sys

from collections import defaultdict
from string import Template
from typing import Callable, Dict, List, Optional, Set, Tuple

from codechecker_report_converter.report import BugPathEvent, \
    InvalidFileContentMsg, File, MacroExpansion, Report, report_file, \
    reports as reports_helper
from codechecker_report_converter.report.statistics import Statistics
from codechecker_report_converter.report.checker_labels import CheckerLabels

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from mypy_extensions import TypedDict


LOG = logging.getLogger('report-converter')


SkipReportHandler = Callable[
    [str, str, int, str, dict, Dict[int, str]],
    Tuple[bool, list]
]


class HTMLBugPathEvent(TypedDict):
    message: str
    fileId: str
    line: int
    column: int


HTMLBugPathEvents = List[HTMLBugPathEvent]


class HTMLMacroExpansion(HTMLBugPathEvent):
    name: str


HTMLMacroExpansions = List[HTMLMacroExpansion]


class Checker(TypedDict):
    name: str
    url: Optional[str]


class HTMLReport(TypedDict):
    fileId: str
    reportHash: Optional[str]
    checker: Checker
    analyzerName: Optional[str]
    line: int
    column: int
    message: str
    events: HTMLBugPathEvents
    macros: HTMLMacroExpansions
    notes: HTMLBugPathEvents
    reviewStatus: Optional[str]
    severity: Optional[str]


HTMLReports = List[HTMLReport]


class FileSource(TypedDict):
    id: str
    filePath: str
    content: str


FileSources = Dict[str, FileSource]


class HtmlReportLink(TypedDict):
    report: HTMLReport
    link: str


def get_file_content(file_path: str) -> str:
    """ Return file content of the given file. """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


class HtmlBuilder:
    """
    Helper class to create html file from a report data.
    """
    def __init__(
        self,
        layout_dir: str,
        checker_labels: Optional[CheckerLabels] = None
    ):
        self._checker_labels = checker_labels
        self.layout_dir = layout_dir
        self.generated_html_reports: Dict[str, HTMLReports] = {}
        self.files: FileSources = {}

        css_dir = os.path.join(self.layout_dir, 'css')
        js_dir = os.path.join(self.layout_dir, 'js')
        codemirror_dir = os.path.join(
            self.layout_dir, 'vendor', 'codemirror')

        # Mapping layout tags to files.
        self._layout_tag_files = {
            'style_css': os.path.join(css_dir, 'style.css'),
            'buglist_css': os.path.join(css_dir, 'buglist.css'),
            'bugview_css': os.path.join(css_dir, 'bugview.css'),
            'statistics_css': os.path.join(css_dir, 'statistics.css'),
            'icon_css': os.path.join(css_dir, 'icon.css'),
            'table_css': os.path.join(css_dir, 'table.css'),
            'codemirror_license': os.path.join(codemirror_dir,
                                               'codemirror.LICENSE'),
            'codemirror_css': os.path.join(codemirror_dir,
                                           'codemirror.min.css'),
            'codemirror_js': os.path.join(codemirror_dir, 'codemirror.min.js'),
            'clike_js': os.path.join(codemirror_dir, 'clike.min.js'),
            'bug_viewer': os.path.join(js_dir, 'bugviewer.js'),
            'bug_list': os.path.join(js_dir, 'buglist.js'),
            'browser_support': os.path.join(js_dir, 'browsersupport.js')
        }

        # Get the HTML layout file content.
        self._layout = Template(get_file_content(
            os.path.join(self.layout_dir, 'layout.html')))

        self._index = Template(get_file_content(
            os.path.join(self.layout_dir, 'index.html')))

        self._statistics = Template(get_file_content(
            os.path.join(self.layout_dir, 'statistics.html')))

        # Get the content of the HTML layout dependencies.
        self._tag_contents = {}
        for tag in self._layout_tag_files:
            self._tag_contents[tag] = get_file_content(
                self._layout_tag_files[tag])

    def get_severity(self, checker_name: str) -> str:
        """ Returns severity level for the given checker name. """
        return self._checker_labels.severity(checker_name) \
            if self._checker_labels else 'UNSPECIFIED'

    def _add_source_file(self, file: File) -> FileSource:
        """
        Updates file source data by file id if the given file hasn't been
        processed.
        """
        if file.id in self.files:
            return self.files[file.id]

        try:
            file_content = file.content
        except Exception:
            file_content = InvalidFileContentMsg

        self.files[file.id] = {
            'id': file.id, 'filePath': file.path, 'content': file_content}

        return self.files[file.id]

    def _get_doc_url(self, report: Report) -> Optional[str]:
        """ Get documentation url for the given report if exists. """
        if self._checker_labels:
            doc_urls = self._checker_labels.label_of_checker(
                report.checker_name, 'doc_url', report.analyzer_name)
            return doc_urls[0] if doc_urls else None

        return None

    def _get_html_reports(
        self,
        reports: List[Report]
    ) -> Tuple[HTMLReports, FileSources]:
        """ Get HTML reports from the given reports.

        Returns a list of html reports and references to file sources.
        """
        html_reports: HTMLReports = []
        files: FileSources = {}

        def to_bug_path_events(
            events: List[BugPathEvent]
        ) -> HTMLBugPathEvents:
            """ Converts the given events to html compatible format. """
            html_events: HTMLBugPathEvents = []
            for event in events:
                files[event.file.id] = self._add_source_file(event.file)

                html_events.append({
                    'message': event.message,
                    'fileId': event.file.id,
                    'line': event.line,
                    'column': event.column,
                })
            return html_events

        def to_macro_expansions(
            macro_expansions: List[MacroExpansion]
        ) -> HTMLMacroExpansions:
            """ Converts the given events to html compatible format. """
            html_macro_expansions: HTMLMacroExpansions = []
            for macro_expansion in macro_expansions:
                files[macro_expansion.file.id] = self._add_source_file(
                    macro_expansion.file)

                html_macro_expansions.append({
                    'message': macro_expansion.message,
                    'name': macro_expansion.name,
                    'fileId': macro_expansion.file.id,
                    'line': macro_expansion.line,
                    'column': macro_expansion.column,
                })
            return html_macro_expansions

        for report in reports:
            files[report.file.id] = self._add_source_file(report.file)

            html_reports.append({
                'fileId': report.file.id,
                'reportHash': report.report_hash,
                'checker': {
                    'name': report.checker_name,
                    'url': self._get_doc_url(report)
                },
                'analyzerName': report.analyzer_name,
                'line': report.line,
                'column': report.column,
                'message': report.message,
                'events': to_bug_path_events(report.bug_path_events),
                'macros': to_macro_expansions(report.macro_expansions),
                'notes': to_bug_path_events(report.notes),
                'reviewStatus': report.review_status,
                'severity': self.get_severity(report.checker_name)
            })

        return html_reports, files

    def create(
        self,
        output_file_path: str,
        reports: List[Report]
    ) -> Tuple[Optional[HTMLReports], Set[str]]:
        """
        Create html file from the given analyzer result file to the output
        path.
        """
        changed_files = reports_helper.get_changed_files(reports)

        if changed_files:
            return None, changed_files

        html_reports, files = self._get_html_reports(reports)

        self.generated_html_reports[output_file_path] = html_reports

        substitute_data = self._tag_contents
        substitute_data.update({
            'report_data': json.dumps({
                'files': files,
                'reports': html_reports
            })
        })

        content = self._layout.substitute(substitute_data)

        with open(output_file_path, 'w+',
                  encoding='utf-8', errors='replace') as f:
            f.write(content)

        return html_reports, changed_files

    def create_index_html(self, output_dir: str):
        """
        Creates an index.html file which lists all available bugs which was
        found in the processed plist files. This also creates a link for each
        bug to the created html file where the bug can be found.
        """
        # Sort reports based on file path levels.
        html_report_links: List[HtmlReportLink] = []
        for html_file, reports in self.generated_html_reports.items():
            for report in reports:
                html_report_links.append({'link': html_file, 'report': report})

        html_report_links.sort(
            key=lambda data: self.files[data['report']['fileId']]['filePath'])

        with io.StringIO() as table_reports:
            # Create table header.
            table_reports.write('''
                <tr>
                  <th id="report-id">&nbsp;</th>
                  <th id="file-path">File</th>
                  <th id="severity">Severity</th>
                  <th id="checker-name">Checker name</th>
                  <th id="message">Message</th>
                  <th id="bug-path-length">Bug path length</th>
                  <th id="review-status">Review status</th>
                </tr>''')

            # Create table lines.
            for i, data in enumerate(html_report_links):
                html_file = os.path.basename(data['link'])
                report = data['report']

                severity = report['severity'].lower() \
                    if 'severity' in report \
                    and report['severity'] is not None \
                    else ''

                review_status = report['reviewStatus'] \
                    if 'reviewStatus' in report and \
                    report['reviewStatus'] is not None \
                    else ''

                events = report['events']
                if events:
                    line = events[-1]['line']
                    message = events[-1]['message']
                    bug_path_length = len(events)
                else:
                    line = report['line']
                    message = report['message']
                    bug_path_length = 1

                rs = review_status.lower().replace(' ', '-')
                file_path = self.files[report['fileId']]['filePath']

                checker = report['checker']
                doc_url = checker.get('url')
                if doc_url:
                    checker_name_col_content = f'<a href="{doc_url}" '\
                        f'target="_blank">{checker["name"]}</a>'
                else:
                    checker_name_col_content = checker["name"]

                table_reports.write(f'''
                  <tr>
                    <td>{i + 1}</td>
                    <td file="{file_path}" line="{line}">
                      <a href="{html_file}#reportHash={report['reportHash']}">
                        {file_path} @ Line&nbsp;{line}
                      </a>
                    </td>
                    <td class="severity" severity="{severity}">
                      <i class="severity-{severity}"
                         title="{severity}"></i>
                    </td>
                    <td>{checker_name_col_content}</td>
                    <td>{message}</td>
                    <td class="bug-path-length">{bug_path_length}</td>
                    <td class="review-status review-status-{rs}">
                      {review_status}
                    </td>
                  </tr>''')

            substitute_data = self._tag_contents
            substitute_data.update({'table_reports': table_reports.getvalue()})

        content = self._index.substitute(substitute_data)
        output_path = os.path.join(output_dir, 'index.html')
        with open(output_path, 'w+', encoding='utf-8',
                  errors='replace') as html_output:
            html_output.write(content)

    def create_statistics_html(self, output_dir: str):
        """
        Creates an statistics.html file which contains statistics information
        from the HTML generation process.
        """
        def severity_order(severity: str) -> int:
            """
            This function determines in which order severities should be
            printed to the output. This function can be given via "key"
            attribute to sort() function.
            """
            severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'STYLE',
                          'UNSPECIFIED']
            return severities.index(severity)

        num_of_analyzer_result_files = len(self.generated_html_reports)

        num_of_reports = 0
        for html_file in self.generated_html_reports:
            num_of_reports += len(self.generated_html_reports[html_file])

        checker_statistics: Dict[str, int] = defaultdict(int)
        for html_file in self.generated_html_reports:
            for report in self.generated_html_reports[html_file]:
                checker = report['checker']['name']
                checker_statistics[checker] += 1

        checker_rows: List[List[str]] = []
        severity_statistics: Dict[str, int] = defaultdict(int)

        with io.StringIO() as string:
            for checker_name in sorted(checker_statistics):
                severity = self.get_severity(checker_name)
                string.write('''
                  <tr>
                    <td>{0}</td>
                    <td class="severity" severity="{1}">
                      <i class="severity-{1}" title="{1}"></i>
                    </td>
                    <td>{2}</td>
                  </tr>
                '''.format(checker_name, severity.lower(),
                           checker_statistics[checker_name]))
                checker_rows.append([checker_name, severity,
                                    str(checker_statistics[checker_name])])
                severity_statistics[severity] += \
                    checker_statistics[checker_name]
            checker_statistics_content = string.getvalue()

        severity_rows: List[List[str]] = []

        with io.StringIO() as string:
            for severity in sorted(severity_statistics, key=severity_order):
                num = severity_statistics[severity]
                string.write('''
                  <tr>
                    <td class="severity" severity="{0}">
                      <i class="severity-{0}" title="{0}"></i>
                    </td>
                    <td>{1}</td>
                  </tr>
                '''.format(severity.lower(), num))
                severity_rows.append([severity, str(num)])
            severity_statistics_content = string.getvalue()

        substitute_data = self._tag_contents
        substitute_data.update({
            'num_of_analyzer_result_files': str(num_of_analyzer_result_files),
            'number_of_reports': str(num_of_reports),
            'checker_statistics': checker_statistics_content,
            'severity_statistics': severity_statistics_content})

        content = self._statistics.substitute(substitute_data)

        output_path = os.path.join(output_dir, 'statistics.html')
        with open(output_path, 'w+', encoding='utf-8',
                  errors='ignore') as html_output:
            html_output.write(content)

    def finish(self, output_dir_path: str, statistics: Statistics):
        """ Creates common html files and print summary messages. """
        self.create_index_html(output_dir_path)
        self.create_statistics_html(output_dir_path)
        statistics.write()

        print(f"\nTo view statistics in a browser run:\n> firefox "
              f"{os.path.join(output_dir_path, 'statistics.html')}")

        print(f"\nTo view the results in a browser run:\n> firefox "
              f"{os.path.join(output_dir_path, 'index.html')}")


def convert(
    file_path: str,
    reports: List[Report],
    output_dir_path: str,
    html_builder: HtmlBuilder
) -> Set[str]:
    """
    Prints the results in the given file to HTML file.

    Returns the skipped analyzer result files because of source
    file content change.
    """
    if not reports:
        LOG.info(f'No report data in {file_path} file.')
        return set()

    html_filename = f"{os.path.basename(file_path)}.html"
    html_output_path = os.path.join(output_dir_path, html_filename)
    _, changed_files = html_builder.create(
        html_output_path, reports)

    if changed_files:
        return changed_files

    LOG.info(f"Html file was generated: {html_output_path}")
    return changed_files


def parse(
    input_path: str,
    output_path: str,
    layout_dir: str,
    html_builder: Optional[HtmlBuilder] = None
) -> Set[str]:
    """
    Parses analyzer result files from the given input directory to the output
    directory.

    Return a set of changed files.
    """
    files = []
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_path)

    if os.path.exists(output_path):
        LOG.info("Previous analysis results in '%s' have been removed, "
                 "overwriting with current results.", output_dir)
        shutil.rmtree(output_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.isfile(input_path):
        files.append(input_path)
    elif os.path.isdir(input_path):
        _, _, file_names = next(os.walk(input_path), ([], [], []))
        files = [os.path.join(input_path, file_name) for file_name
                 in file_names]

    # Source files which modification time changed since the last analysis.
    changed_source_files: Set[str] = set()

    if not html_builder:
        html_builder = HtmlBuilder(layout_dir)

    for file_path in files:
        if not report_file.is_supported(file_path):
            LOG.info("\nSkipping input file %s as it is not supported "
                     "analyzer result file.", file_path)
            continue

        LOG.info(f"\nParsing input file '%s'", file_path)

        reports = report_file.get_reports(file_path)
        changed_source = convert(file_path, reports, output_path, html_builder)

        if changed_source:
            changed_source_files.update(changed_source)

    return changed_source_files
