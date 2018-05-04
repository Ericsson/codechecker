#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import argparse
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
    with open(filename, 'r') as f:
        return f.read()


class HtmlBuilder:
    """
    Helper class to create html file from a report data.
    """
    def __init__(self, layout_dir):
        self.layout_dir = layout_dir

        # Mapping layout tags to files.
        self._layout_tag_files = {
            'STYLE_CSS': 'style.css',
            'CODEMIRROR_LICENSE': 'codemirror.LICENSE',
            'CODEMIRROR_CSS': 'codemirror.min.css',
            'CODEMIRROR_JS': 'codemirror.min.js',
            'CLIKE_JS': 'clike.min.js',
            'BUG_VIEWER': 'bugviewer.js'
        }

        # Get the HTML layout file content.
        self._layout = get_file_content(
            os.path.join(self.layout_dir, 'layout.html'))

        # Get the content of the HTML layout dependecies.
        self._tag_contents = {}
        for tag in self._layout_tag_files:
            self._tag_contents[tag] = get_file_content(
                os.path.join(self.layout_dir, self._layout_tag_files[tag]))

            self._layout = self._layout.replace('<${0}$>'.format(tag),
                                                self._tag_contents[tag])

    def create(self, output_path, report_data):
        """
        Create html file with the given report data to the output path.
        """
        content = self._layout.replace('<$REPORT_DATA$>',
                                       json.dumps(report_data))

        with open(output_path, 'w+') as html_output:
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

        last_report_event = bug_path_items[-1]
        source_file = files[last_report_event['location']['file']]
        report_line = last_report_event['location']['line']
        report_hash = diag['issue_hash_content_of_line_in_context']
        checker_name = diag['check_name']

        if skip_report_handler and skip_report_handler(report_hash,
                                                       source_file,
                                                       report_line,
                                                       checker_name):
            continue

        events = [i for i in bug_path_items if i.get('kind') == 'event']

        report = []
        for index, event in enumerate(events):
            file_id = event['location']['file']
            if file_id not in file_sources:
                file_path = files[file_id]
                source_data = open(file_path, 'r')
                file_sources[file_id] = {'id': file_id,
                                         'path': file_path,
                                         'content': source_data.read()}

            report.append({'line': event.location['line'],
                           'col':  event.location['col'],
                           'file': event.location['file'],
                           'msg':  event.message,
                           'step': index + 1})
        reports.append(report)

    return {'files': file_sources,
            'reports': reports}


def plist_to_html(file_path, output_path, html_builder,
                  skip_report_handler=None):
    """
    Prints the results in the given file to HTML file.

    Returns the skipped plist files because of source
    file conent change.
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


def parse(input_path, output_path, layout_dir, clean=False,
          skip_report_handler=None):
    files = []
    input_path = os.path.abspath(input_path)

    output_dir = os.path.abspath(output_path)
    if clean and os.path.isdir(output_dir):
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
        output_path))

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

    parser.add_argument('-l', '--layout',
                        dest="layout_dir",
                        required=False,
                        default=os.path.join(os.path.abspath(__file__),
                                             '..',
                                             'dist'),
                        help="Directory which contains dependency HTML, CSS "
                             "and JavaScript files.")

    parser.add_argument('-c', '--clean',
                        dest="clean",
                        required=False,
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="Delete the output results stored in the output "
                             "directory. (By default, it would keep HTML "
                             "files and overwrite only those files that "
                             "belongs to a plist file given by the input "
                             "argument.")


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

    for input_path in args.input:
        parse(input_path, args.output_dir, args.layout_dir, 'clean' in args)


if __name__ == "__main__":
    main()
