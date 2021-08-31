#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import argparse
import io
import json
import os
import plistlib
import shutil
import sys

from collections import defaultdict
from string import Template
from typing import Callable, Dict, List, Optional, Set, Tuple
from xml.parsers.expat import ExpatError

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from mypy_extensions import TypedDict


SkipReportHandler = Callable[
    [str, str, int, str, dict, Dict[int, str]],
    Tuple[bool, list]
]

TrimPathPrefixHandler = Callable[[str], str]
SeverityMap = Dict[str, str]


class Location(TypedDict):
    col: int
    file: int
    line: int


class Event(TypedDict):
    location: Location
    message: str


class Macro(TypedDict):
    location: Location
    expansion: str
    name: str


class Note(TypedDict):
    location: Location
    message: str


Events = List[Event]
Macros = List[Macro]
Notes = List[Note]


class Report(TypedDict):
    events: Events
    macros: Macros
    notes: Notes
    path: str
    reportHash: str
    checkerName: str
    reviewStatus: Optional[str]
    severity: Optional[str]


Reports = List[Report]


class FileSource(TypedDict):
    id: int
    path: str
    content: str


FileSources = Dict[int, FileSource]


class ReportData(TypedDict):
    files: FileSources
    reports: Reports


class HtmlReport(TypedDict):
    html_file: str
    report: Report


def get_last_mod_time(file_path: str) -> int:
    """ Return the last modification time of a file. """
    return os.stat(file_path)[9]


def get_file_content(file_path: str) -> str:
    """ Return file content of the given file. """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def twodim_to_table(
    lines: List[List[str]],
    separate_head: bool = True,
    separate_footer: bool = False
) -> Optional[str]:
    """ Pretty-prints the given two-dimensional array's lines. """

    str_parts = []

    # Count the column width.
    widths: List[int] = []
    for line in lines:
        for i, size in enumerate([len(str(x)) for x in line]):
            while i >= len(widths):
                widths.append(0)
            if size > widths[i]:
                widths[i] = size

    # Generate the format string to pad the columns.
    print_string = ""
    for i, width in enumerate(widths):
        print_string += "{" + str(i) + ":" + str(width) + "} | "

    if not print_string:
        return ""

    print_string = print_string[:-3]

    # Print the actual data.
    str_parts.append("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for i, line in enumerate(lines):
        try:
            str_parts.append(print_string.format(*line))
        except IndexError:
            raise TypeError("One of the rows have a different number of "
                            "columns than the others")
        if i == 0 and separate_head:
            str_parts.append("-" * (sum(widths) + 3 * (len(widths) - 1)))
        if separate_footer and i == len(lines) - 2:
            str_parts.append("-" * (sum(widths) + 3 * (len(widths) - 1)))

    str_parts.append("-" * (sum(widths) + 3 * (len(widths) - 1)))

    return '\n'.join(str_parts)


class HtmlBuilder:
    """
    Helper class to create html file from a report data.
    """
    def __init__(
        self,
        layout_dir: str,
        checker_labels=None  # : Optional[CheckerLabels] = None
    ):
        self._checker_labels = checker_labels
        self.layout_dir = layout_dir
        self.generated_html_reports: Dict[str, Reports] = {}

        css_dir = os.path.join(self.layout_dir, 'css')
        js_dir = os.path.join(self.layout_dir, 'js')
        codemirror_dir = os.path.join(self.layout_dir, 'vendor',
                                      'codemirror')

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

    def get_severity(self, checker: str) -> str:
        return self._checker_labels.severity(checker) \
            if self._checker_labels else 'UNSPECIFIED'

    def create(self, output_path: str, report_data: ReportData):
        """
        Create html file with the given report data to the output path.
        """
        # Add severity levels for reports.
        for report in report_data['reports']:
            checker = report['checkerName']
            report['severity'] = self.get_severity(checker)

        self.generated_html_reports[output_path] = report_data['reports']

        substitute_data = self._tag_contents
        substitute_data.update({'report_data': json.dumps(report_data)})

        content = self._layout.substitute(substitute_data)

        with open(output_path, 'w+', encoding='utf-8',
                  errors='replace') as html_output:
            html_output.write(content)

    def create_index_html(self, output_dir: str):
        """
        Creates an index.html file which lists all available bugs which was
        found in the processed plist files. This also creates a link for each
        bug to the created html file where the bug can be found.
        """

        # Sort reports based on file path levels.
        report_data: List[HtmlReport] = []
        for html_file in self.generated_html_reports:
            for report in self.generated_html_reports[html_file]:
                report_data.append({'html_file': html_file, 'report': report})
        report_data = sorted(report_data,
                             key=lambda d: d['report']['path'])

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
            for i, data in enumerate(report_data):
                html_file = os.path.basename(data['html_file'])
                report = data['report']

                events = report['events']
                checker = report['checkerName']
                severity = report['severity'].lower() \
                    if 'severity' in report \
                    and report['severity'] is not None \
                    else ''

                review_status = report['reviewStatus'] \
                    if 'reviewStatus' in report and \
                    report['reviewStatus'] is not None \
                    else ''

                line = events[-1]['location']['line']
                rs = review_status.lower().replace(' ', '-')

                table_reports.write(f'''
                  <tr>
                    <td>{i + 1}</td>
                    <td file="{report['path']}" line="{line}">
                      <a href="{html_file}#reportHash={report['reportHash']}">
                        {report['path']} @ Line&nbsp;{line}
                      </a>
                    </td>
                    <td class="severity" severity="{severity}">
                      <i class="severity-{severity}"
                         title="{severity}"></i>
                    </td>
                    <td>{checker}</td>
                    <td>{events[-1]['message']}</td>
                    <td class="bug-path-length">{len(events)}</td>
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

        num_of_plist_files = len(self.generated_html_reports)

        num_of_reports = 0
        for html_file in self.generated_html_reports:
            num_of_reports += len(self.generated_html_reports[html_file])

        checker_statistics: Dict[str, int] = defaultdict(int)
        for html_file in self.generated_html_reports:
            for report in self.generated_html_reports[html_file]:
                checker = report['checkerName']
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
            'number_of_plist_files': str(num_of_plist_files),
            'number_of_reports': str(num_of_reports),
            'checker_statistics': checker_statistics_content,
            'severity_statistics': severity_statistics_content})

        content = self._statistics.substitute(substitute_data)

        output_path = os.path.join(output_dir, 'statistics.html')
        with open(output_path, 'w+', encoding='utf-8',
                  errors='ignore') as html_output:
            html_output.write(content)

        print("\n----==== Summary ====----")

        print("----=================----")
        print("Total number of reports: {}".format(num_of_reports))
        print("----=================----")

        print("\n----======== Statistics ========----")
        statistics_rows = [
            ["Number of processed plist files", str(num_of_plist_files)],
            ["Number of analyzer reports", str(num_of_reports)]]
        print(twodim_to_table(statistics_rows, False))

        print("\n----==== Checker Statistics ====----")
        header = ["Checker name", "Severity", "Number of reports"]
        print(twodim_to_table([header] + checker_rows))

        print("\n----==== Severity Statistics ====----")
        header = ["Severity", "Number of reports"]
        print(twodim_to_table([header] + severity_rows))


def get_report_data_from_plist(
    plist: dict,
    skip_report_handler: Optional[SkipReportHandler] = None,
    trim_path_prefixes_handler: Optional[TrimPathPrefixHandler] = None
):
    """
    Returns a dictionary with the source file contents and the reports parsed
    from the plist.
    """
    files = plist['files']
    reports: Reports = []
    file_sources: FileSources = {}

    def update_source_file(file_id: int):
        """
        Updates file source data by file id if the given file hasn't been
        processed.
        """
        if file_id not in file_sources:
            file_path = files[file_id]
            with open(file_path, 'r', encoding='utf-8',
                      errors='ignore') as source_data:
                # trim path prefixes after file loading
                if trim_path_prefixes_handler:
                    file_path = trim_path_prefixes_handler(file_path)
                file_sources[file_id] = {'id': file_id,
                                         'path': file_path,
                                         'content': source_data.read()}

    for diag in plist['diagnostics']:
        bug_path_items = [item for item in diag['path']]

        source_file = files[diag['location']['file']]
        report_line = diag['location']['line']
        report_hash = diag['issue_hash_content_of_line_in_context']
        checker_name = diag['check_name']
        source_code_comments: list = []

        if skip_report_handler:
            skip, source_code_comments = skip_report_handler(report_hash,
                                                             source_file,
                                                             report_line,
                                                             checker_name,
                                                             diag,
                                                             files)
            if skip:
                continue

        # Processing bug path events.
        events: Events = []
        for path in bug_path_items:
            kind = path.get('kind')
            if kind == 'event':
                events.append({'location': path['location'],
                               'message': path['message']})
            else:
                continue

            update_source_file(path['location']['file'])

        # Processing macro expansions.
        macros: Macros = []
        for macro in diag.get('macro_expansions', []):
            macros.append({'location': macro['location'],
                           'expansion': macro['expansion'],
                           'name': macro['name']})

            update_source_file(macro['location']['file'])

        # Processing notes.
        notes: Notes = []
        for note in diag.get('notes', []):
            notes.append({'location': note['location'],
                          'message': note['message']})

            update_source_file(note['location']['file'])

        # trim path prefixes after skip_report_handler filtering
        if trim_path_prefixes_handler:
            source_file = trim_path_prefixes_handler(source_file)

        reviewStatus = None
        if len(source_code_comments) == 1:
            reviewStatus = source_code_comments[0]['status'] \
                .capitalize().replace('_', ' ')

        reports.append({'events': events,
                        'macros': macros,
                        'notes': notes,
                        'path': source_file,
                        'reportHash': report_hash,
                        'checkerName': checker_name,
                        'reviewStatus': reviewStatus,
                        'severity': None})

    return {'files': file_sources,
            'reports': reports}


def plist_to_html(
    file_path: str,
    output_path: str,
    html_builder: HtmlBuilder,
    skip_report_handler: Optional[SkipReportHandler] = None,
    trim_path_prefixes_handler: Optional[TrimPathPrefixHandler] = None
) -> Tuple[Optional[str], Set[str]]:
    """
    Prints the results in the given file to HTML file.

    Returns the skipped plist files because of source
    file content change.
    """
    changed_source: Set[str] = set()
    if not file_path.endswith(".plist"):
        print("\nSkipping input file {0} as it is not a plist.".format(
            file_path))
        return file_path, changed_source

    print("\nParsing input file '" + file_path + "'")
    try:
        plist = {}
        with open(file_path, 'rb') as plist_file:
            plist = plistlib.load(plist_file)

        report_data = get_report_data_from_plist(plist,
                                                 skip_report_handler,
                                                 trim_path_prefixes_handler)

        plist_mtime = get_last_mod_time(file_path)

        source_changed = False

        for sf in plist.get('files', []):
            sf_mtime = get_last_mod_time(sf)
            if sf_mtime > plist_mtime:
                source_changed = True
                changed_source.add(sf)

        if source_changed:
            return file_path, changed_source

        if report_data is None or not report_data['reports']:
            print('No report data in {0} file.'.format(file_path))
            return file_path, changed_source

        html_filename = os.path.basename(file_path) + '.html'
        html_output_path = os.path.join(output_path, html_filename)
        html_builder.create(html_output_path, report_data)

        print('Html file was generated: {0}'.format(html_output_path))
        return None, changed_source

    except (ExpatError, plistlib.InvalidFileException) as err:
        print('Failed to process plist file: ' + file_path +
              ' wrong file format?', err)
        return file_path, changed_source
    except AttributeError as ex:
        print('Failed to get important report data from plist.', ex)
        return file_path, changed_source
    except IndexError as iex:
        print('Indexing error during processing plist file ' + file_path, iex)
        return file_path, changed_source
    except Exception as ex:
        print('Error during processing reports from the plist file: ' +
              file_path, ex)
        return file_path, changed_source


def parse(
    input_path: str,
    output_path: str,
    layout_dir: str,
    skip_report_handler: Optional[SkipReportHandler] = None,
    html_builder: Optional[HtmlBuilder] = None,
    trim_path_prefixes_handler: Optional[TrimPathPrefixHandler] = None
) -> Set[str]:
    """
    Parses plist files from the given input directory to the output directory.
    Return a set of changed files.
    """
    files = []
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_path)

    if os.path.exists(output_path):
        print("Previous analysis results in '{0}' have been removed, "
              "overwriting with current results.".format(output_dir))
        shutil.rmtree(output_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.isfile(input_path):
        files.append(input_path)
    elif os.path.isdir(input_path):
        _, _, file_names = next(os.walk(input_path), ([], [], []))
        files = [os.path.join(input_path, file_name) for file_name
                 in file_names]

    # Skipped plist reports from html generation because it is not a
    # plist file or there are no reports in it.
    skipped_report = set()

    # Source files which modification time changed since the last analysis.
    changed_source_files: Set[str] = set()

    if not html_builder:
        html_builder = HtmlBuilder(layout_dir)

    for file_path in files:
        sr, changed_source = plist_to_html(file_path,
                                           output_path,
                                           html_builder,
                                           skip_report_handler,
                                           trim_path_prefixes_handler)
        if changed_source:
            changed_source_files = changed_source_files.union(changed_source)
        if sr:
            skipped_report.add(sr)

    return changed_source_files


def __add_arguments_to_parser(parser: argparse.ArgumentParser):
    parser.add_argument('input',
                        type=str,
                        nargs='+',
                        metavar='file/folder',
                        help="The plist files and/or folders containing "
                             "analysis results which should be parsed.")

    parser.add_argument('-o', '--output',
                        dest="output_dir",
                        required=True,
                        help="Generate HTML output files in the given folder.")

    curr_file_dir = os.path.dirname(os.path.realpath(__file__))
    parser.add_argument('-l', '--layout',
                        dest="layout_dir",
                        required=False,
                        default=os.path.join(curr_file_dir,
                                             '..', 'plist_to_html', 'static'),
                        help="Directory which contains dependency HTML, CSS "
                             "and JavaScript files.")


def main():
    """ Plist parser main command line. """
    parser = argparse.ArgumentParser(
        prog="plist-to-html",
        description="Parse and create HTML files from one or more '.plist' "
                    "result files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if isinstance(args.input, str):
        args.input = [args.input]

    # Source files which modification time changed since the last analysis.
    changed_source_files = set()

    html_builder = HtmlBuilder(args.layout_dir)
    for input_path in args.input:
        changed_files = parse(input_path, args.output_dir, args.layout_dir,
                              None, html_builder)
        changed_source_files.union(changed_files)

    html_builder.create_index_html(args.output_dir)
    html_builder.create_statistics_html(args.output_dir)

    print('\nTo view statistics in a browser run:\n> firefox {0}'.format(
        os.path.join(args.output_dir, 'statistics.html')))

    print('\nTo view the results in a browser run:\n> firefox {0}'.format(
        os.path.join(args.output_dir, 'index.html')))

    if changed_source_files:
        changed_files = '\n'.join([' - ' + f for f in changed_source_files])
        print("\nThe following source file contents changed since the "
              "latest analysis:\n{0}\nPlease analyze your project again to "
              "update the reports!".format(changed_files))


if __name__ == "__main__":
    main()
