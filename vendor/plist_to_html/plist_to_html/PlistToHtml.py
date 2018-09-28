#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import argparse
import codecs
import json
import os
import plistlib
import shutil
from xml.parsers.expat import ExpatError


def get_last_mod_time(file_path):
    """
    Return the last modification time of a file.
    """
    return os.stat(file_path)[9]


def get_file_content(filename):
    with codecs.open(filename, 'r', 'UTF-8') as f:
        return f.read()


class HtmlBuilder:
    """
    Helper class to create html file from a report data.
    """
    def __init__(self, layout_dir, severity_map=None):
        self._severity_map = severity_map if severity_map else {}
        self.layout_dir = layout_dir
        self.generated_html_reports = {}

        # Mapping layout tags to files.
        self._layout_tag_files = {
            'STYLE_CSS': 'style.css',
            'ICON_CSS': 'icon.css',
            'CODEMIRROR_LICENSE': 'codemirror.LICENSE',
            'CODEMIRROR_CSS': 'codemirror.min.css',
            'CODEMIRROR_JS': 'codemirror.min.js',
            'CLIKE_JS': 'clike.min.js',
            'BUG_VIEWER': 'bugviewer.js',
            'BROWSER_SUPPORT': 'browsersupport.js'
        }

        # Get the HTML layout file content.
        self._layout = get_file_content(
            os.path.join(self.layout_dir, 'layout.html'))

        self._index = get_file_content(
            os.path.join(self.layout_dir, 'index.html'))

        # Get the content of the HTML layout dependencies.
        self._tag_contents = {}
        for tag in self._layout_tag_files:
            self._tag_contents[tag] = get_file_content(
                os.path.join(self.layout_dir, self._layout_tag_files[tag]))

            self._layout = self._layout.replace('<${0}$>'.format(tag),
                                                self._tag_contents[tag])

            self._index = self._index.replace('<${0}$>'.format(tag),
                                              self._tag_contents[tag])

    def create(self, output_path, report_data):
        """
        Create html file with the given report data to the output path.
        """
        # Add severity levels for reports.
        for report in report_data['reports']:
            checker = report['checkerName']
            report['severity'] = self._severity_map.get(checker, 'UNSPECIFIED')

        self.generated_html_reports[output_path] = report_data['reports']
        content = self._layout.replace('<$REPORT_DATA$>',
                                       json.dumps(report_data))

        with codecs.open(output_path, 'w+', 'UTF-8') as html_output:
            html_output.write(content)

    def create_index_html(self, output_dir):
        """
        Creates an index.html file which lists all available bugs which was
        found in the processed plist files. This also creates a link for each
        bug to the created html file where the bug can be found.
        """

        # Create table header.
        table_reports = '''
            <tr>
              <th>&nbsp;</th>
              <th>File</th>
              <th>Severity</th>
              <th>Checker name</th>
              <th>Message</th>
              <th>Bug path length</th>
            </tr>'''

        # Sort reports based on file path levels.
        report_data = []
        for html_file in self.generated_html_reports:
            for report in self.generated_html_reports[html_file]:
                report_data.append({'html_file': html_file, 'report': report})
        report_data = sorted(report_data,
                             key=lambda d: d['report']['path'])

        # Create table lines.
        for i, data in enumerate(report_data):
            html_file = data['html_file']
            report = data['report']

            events = report['events']
            checker = report['checkerName']
            severity = report['severity']

            table_reports += '''
              <tr>
                <td>{0}</td>
                <td>
                  <a href="{1}#reportHash={2}">{3} @ Line {4}</a>
                </td>
                <td class="severity">
                  <i class="severity-{5}"></i>
                </td>
                <td>{6}</td>
                <td>{7}</td>
                <td class="bug-path-length">{8}</td>
              </tr>'''.format(i + 1,
                              os.path.basename(html_file),
                              report['reportHash'],
                              report['path'],
                              events[-1]['line'],
                              severity.lower(),
                              checker,
                              events[-1]['msg'],
                              len(events))

        content = self._index.replace('<$TABLE_REPORTS$>', table_reports)
        output_path = os.path.join(output_dir, 'index.html')
        with codecs.open(output_path, 'w+', 'UTF-8') as html_output:
            html_output.write(content)


def get_report_data_from_plist(plist, skip_report_handler=None):
    """
    Returns a dictionary with the source file contents and the reports parsed
    from the plist.
    """
    files = plist['files']

    reports = []
    file_sources = {}
    for diag in plist['diagnostics']:
        bug_path_items = [item for item in diag['path']]

        source_file = files[diag['location']['file']]
        report_line = diag['location']['line']
        report_hash = diag['issue_hash_content_of_line_in_context']
        checker_name = diag['check_name']

        if skip_report_handler and skip_report_handler(report_hash,
                                                       source_file,
                                                       report_line,
                                                       checker_name,
                                                       diag,
                                                       files):
            continue

        events = [i for i in bug_path_items if i.get('kind') == 'event']

        report_events = []
        for index, event in enumerate(events):
            file_id = event['location']['file']
            if file_id not in file_sources:
                file_path = files[file_id]
                with codecs.open(file_path, 'r', 'UTF-8',
                                 errors='replace') as source_data:
                    file_sources[file_id] = {'id': file_id,
                                             'path': file_path,
                                             'content': source_data.read()}

            report_events.append({'line': event.location['line'],
                                  'col':  event.location['col'],
                                  'file': event.location['file'],
                                  'msg':  event.message,
                                  'step': index + 1})

        reports.append({'events': report_events,
                        'path': source_file,
                        'reportHash': report_hash,
                        'checkerName': checker_name})

    return {'files': file_sources,
            'reports': reports}


def plist_to_html(file_path, output_path, html_builder,
                  skip_report_handler=None):
    """
    Prints the results in the given file to HTML file.

    Returns the skipped plist files because of source
    file content change.
    """
    changed_source = set()
    file_paths = []
    if not file_path.endswith(".plist"):
        print("\nSkipping input file {0} as it is not a plist.".format(
            file_path))
        return file_path, changed_source

    print("\nParsing input file '" + file_path + "'")
    try:
        plist = plistlib.readPlist(file_path)

        report_data = get_report_data_from_plist(plist, skip_report_handler)

        plist_mtime = get_last_mod_time(file_path)

        source_changed = False

        for sf in plist.get('files', []):
            sf_mtime = get_last_mod_time(sf)
            if sf_mtime > plist_mtime:
                source_changed = True
                changed_source.add(sf)

        if source_changed:
            return file_path, changed_source

        if report_data is None or not len(report_data['reports']):
            print('No report data in {0} file.'.format(file_path))
            return file_path, changed_source

        html_filename = os.path.basename(file_path) + '.html'
        html_output_path = os.path.join(output_path, html_filename)
        html_builder.create(html_output_path, report_data)

        print('Html file was generated: {0}'.format(html_output_path))
        return None, changed_source

    except ExpatError as err:
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


def parse(input_path, output_path, layout_dir, skip_report_handler=None,
          html_builder=None):
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
    changed_source_files = set()

    if not html_builder:
        html_builder = HtmlBuilder(layout_dir)

    for file_path in files:
        sr, changed_source = plist_to_html(file_path,
                                           output_path,
                                           html_builder,
                                           skip_report_handler)
        if changed_source:
            changed_source_files = changed_source_files.union(changed_source)
        if sr:
            skipped_report.add(sr)

    print('\nTo view the results in a browser run:\n> firefox {0}'.format(
        os.path.join(output_path, 'index.html')))

    if changed_source_files:
        changed_files = '\n'.join([' - ' + f for f in changed_source_files])
        print("\nThe following source file contents changed since the "
              "latest analysis:\n{0}\nPlease analyze your project again to "
              "update the reports!".format(changed_files))


def __add_arguments_to_parser(parser):
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

    curr_file_dir = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument('-l', '--layout',
                        dest="layout_dir",
                        required=False,
                        default=os.path.join(curr_file_dir,
                                             '..',
                                             'dist'),
                        help="Directory which contains dependency HTML, CSS "
                             "and JavaScript files.")


def main():
    """
    Plist parser main command line.
    """
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

    html_builder = HtmlBuilder(args.layout_dir)
    for input_path in args.input:
        parse(input_path, args.output_dir, args.layout_dir, None, html_builder)

    html_builder.create_index_html(args.output_dir)


if __name__ == "__main__":
    main()
