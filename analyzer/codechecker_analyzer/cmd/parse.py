# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Defines the CodeChecker action for parsing a set of analysis results into a
human-readable format.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from collections import defaultdict
import argparse
import io
import json
import math
import os
import sys

from plist_to_html import PlistToHtml

from codechecker_analyzer import analyzer_context, suppress_handler

from codechecker_common import logger
from codechecker_common import plist_parser
from codechecker_common import util
from codechecker_common.skiplist_handler import SkipListHandler
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler
from codechecker_common.output_formatters import twodim_to_str
from codechecker_common.report import Report, get_report_path_hash
from codechecker_common.source_code_comment_handler import skip_suppress_status

LOG = logger.get_logger('system')


class PlistToPlaintextFormatter(object):
    """
    Parse and format plist reports to a more human readable format.
    """

    def __init__(self,
                 src_comment_handler,
                 skip_handler,
                 severity_map,
                 processed_path_hashes,
                 trim_path_prefixes,
                 analyzer_type="clangsa"):

        self.__analyzer_type = analyzer_type
        self.__severity_map = severity_map
        self.print_steps = False
        self.src_comment_handler = src_comment_handler
        self.skiplist_handler = skip_handler
        self._processed_path_hashes = processed_path_hashes
        self._trim_path_prefixes = trim_path_prefixes

    @staticmethod
    def __format_location(event, source_file):
        loc = event['location']
        line = util.get_line(source_file, loc['line'])
        if line == '':
            return line

        marker_line = line[0:(loc['col'] - 1)]
        marker_line = ' ' * (len(marker_line) + marker_line.count('\t'))
        return '%s%s^' % (line.replace('\t', '  '), marker_line)

    @staticmethod
    def __format_bug_event(name, severity, event, source_file):

        loc = event['location']
        fname = os.path.basename(source_file)
        if name:
            return '[%s] %s:%d:%d: %s [%s]' % (severity,
                                               source_file,
                                               loc['line'],
                                               loc['col'],
                                               event['message'],
                                               name)
        else:
            return '%s:%d:%d: %s' % (fname,
                                     loc['line'],
                                     loc['col'],
                                     event['message'])

    @staticmethod
    def __format_bug_note(note, source_file):
        """
        Format bug notes.
        """
        loc = note['location']
        file_name = os.path.basename(source_file)
        return '%s:%d:%d: %s' % (file_name,
                                 loc['line'],
                                 loc['col'],
                                 note['message'])

    @staticmethod
    def __format_macro_expansion(macro, source_file):
        """
        Format macro expansions.
        """
        loc = macro['location']
        file_name = os.path.basename(source_file)
        return "%s:%d:%d: Macro '%s' expanded to '%s'" % (file_name,
                                                          loc['line'],
                                                          loc['col'],
                                                          macro['name'],
                                                          macro['expansion'])

    @staticmethod
    def parse(plist_file):
        """
        Parse a plist report file.
        Returns:
            - list of source files
            - list of reports (type Report)
        """
        files, reports = [], []
        try:
            files, reports = plist_parser.parse_plist_file(plist_file)
        except Exception as ex:
            traceback.print_stack()
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
        finally:
            return files, reports

    def write(self, file_report_map, output=sys.stdout):
        """
        Format an already parsed plist report file to a more
        human readable format.
        The formatted text is written to the output.
        During writing the output statistics are collected.

        Write out the bugs to the output and collect report statistics.
        """

        severity_stats = defaultdict(int)
        file_stats = defaultdict(int)
        report_count = defaultdict(int)

        for file_path in sorted(file_report_map,
                                key=lambda key: len(file_report_map[key])):

            non_suppressed = 0
            sorted_reports = sorted(file_report_map[file_path],
                                    key=lambda r: r.main['location']['line'])

            for report in sorted_reports:
                path_hash = get_report_path_hash(report, report.files)
                if path_hash in self._processed_path_hashes:
                    LOG.debug("Not showing report because it is a "
                              "deduplication of an already processed report!")
                    LOG.debug("Path hash: %s", path_hash)
                    LOG.debug(report)
                    continue

                self._processed_path_hashes.add(path_hash)

                events = [i for i in report.bug_path
                          if i.get('kind') == 'event']
                f_path = report.files[events[-1]['location']['file']]
                if self.skiplist_handler and \
                        self.skiplist_handler.should_skip(f_path):
                    LOG.debug("Skipped report in '%s'", f_path)
                    LOG.debug(report)
                    continue

                last_report_event = report.bug_path[-1]
                source_file = \
                    report.files[last_report_event['location']['file']]
                trimmed_source_file = \
                    util.trim_path_prefixes(source_file,
                                            self._trim_path_prefixes)

                report_line = last_report_event['location']['line']
                report_hash = \
                    report.main['issue_hash_content_of_line_in_context']
                checker_name = report.main['check_name']

                if skip_report(report_hash, source_file, report_line,
                               checker_name, self.src_comment_handler):
                    continue

                file_stats[f_path] += 1
                severity = self.__severity_map.get(checker_name)
                severity_stats[severity] += 1
                report_count["report_count"] += 1

                output.write(self.__format_bug_event(checker_name,
                                                     severity,
                                                     last_report_event,
                                                     trimmed_source_file))
                output.write('\n')
                output.write(self.__format_location(last_report_event,
                                                    source_file))
                output.write('\n')

                if self.print_steps:
                    output.write('  Report hash: ' + report_hash + '\n')

                    # Print out macros.
                    macros = report.macro_expansions
                    if macros:
                        output.write('  Macro expansions:\n')

                        index_format = '    %%%dd, ' % \
                                       int(math.floor(
                                           math.log10(len(macros))) + 1)

                        for index, macro in enumerate(macros):
                            output.write(index_format % (index + 1))
                            source = report.files[
                                macro['location']['file']]
                            output.write(self.__format_macro_expansion(macro,
                                                                       source))
                            output.write('\n')

                    # Print out notes.
                    notes = report.notes
                    if notes:
                        output.write('  Notes:\n')

                        index_format = '    %%%dd, ' % \
                                       int(math.floor(
                                           math.log10(len(notes))) + 1)

                        for index, note in enumerate(notes):
                            output.write(index_format % (index + 1))
                            source_file = report.files[
                                note['location']['file']]
                            output.write(self.__format_bug_note(note,
                                                                source_file))
                            output.write('\n')

                    output.write('  Steps:\n')

                    index_format = '    %%%dd, ' % \
                                   int(math.floor(math.log10(len(events))) + 1)

                    for index, event in enumerate(events):
                        output.write(index_format % (index + 1))
                        source_file = report.files[event['location']['file']]
                        trimmed_source_file = \
                            util.trim_path_prefixes(source_file,
                                                    self._trim_path_prefixes)
                        output.write(
                            self.__format_bug_event(None,
                                                    None,
                                                    event,
                                                    trimmed_source_file))
                        output.write('\n')
                output.write('\n')

                non_suppressed += 1

            base_file = os.path.basename(file_path)
            if non_suppressed == 0:
                output.write('Found no defects in %s\n' % base_file)
            else:
                output.write('Found %d defect(s) in %s\n\n' %
                             (non_suppressed, base_file))

        return {"severity": severity_stats,
                "files":  file_stats,
                "reports": report_count}


def skip_report(report_hash, source_file, report_line, checker_name,
                src_comment_handler=None):
    """
    Returns True if the report was suppressed in the source code, otherwise
    False.
    """
    bug = {'hash_value': report_hash, 'file_path': source_file}
    if src_comment_handler and src_comment_handler.get_suppressed(bug):
        LOG.debug("Suppressed by suppress file: %s:%s [%s] %s", source_file,
                  report_line, checker_name, report_hash)
        return True

    sc_handler = SourceCodeCommentHandler()

    # Check for source code comment.
    src_comment_data = sc_handler.filter_source_line_comments(
        source_file,
        report_line,
        checker_name)

    if len(src_comment_data) == 1:
        status = src_comment_data[0]['status']

        LOG.debug("Suppressed by source code comment.")
        if src_comment_handler:
            file_name = os.path.basename(source_file)
            message = src_comment_data[0]['message']
            src_comment_handler.store_suppress_bug_id(
                report_hash,
                file_name,
                message,
                status)

        if skip_suppress_status(status):
            return True

    elif len(src_comment_data) > 1:
        LOG.warning("Multiple source code comment can be found "
                    "for '%s' checker in '%s' at line %d. "
                    "This bug will not be suppressed!",
                    checker_name, source_file, report_line)
    return False


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker parse',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Parse and pretty-print the summary and results from "
                       "one or more 'codechecker-analyze' result files. Bugs "
                       "which are commented by using \"false_positive\", "
                       "\"suppress\" and \"intentional\" source code "
                       "comments will not be printed by the `parse` command.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Print analysis summary and results in a human-readable "
                "format."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='+',
                        metavar='file/folder',
                        help="The analysis result files and/or folders "
                             "containing analysis results which should be "
                             "parsed and printed.")

    parser.add_argument('-t', '--type', '--input-format',
                        dest="input_format",
                        required=False,
                        choices=['plist'],
                        default='plist',
                        help="Specify the format the analysis results were "
                             "created as.")

    output_opts = parser.add_argument_group("export arguments")
    output_opts.add_argument('-e', '--export',
                             dest="export",
                             required=False,
                             choices=['html', 'json'],
                             help="Specify extra output format type.")

    output_opts.add_argument('-o', '--output',
                             dest="output_path",
                             default=argparse.SUPPRESS,
                             help="Store the output in the given folder.")

    output_opts.add_argument('-c', '--clean',
                             dest="clean",
                             required=False,
                             action='store_true',
                             default=True,
                             help="DEPRECATED. Delete output results stored "
                                  "in the output directory. (By default, it "
                                  "would keep output files and overwrites "
                                  "only those that belongs to a plist file "
                                  "given by the input argument.")

    parser.add_argument('--suppress',
                        type=str,
                        dest="suppress",
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Path of the suppress file to use. Records in "
                             "the suppress file are used to suppress the "
                             "display of certain results when parsing the "
                             "analyses' report. (Reports to an analysis "
                             "result can also be suppressed in the source "
                             "code -- please consult the manual on how to "
                             "do so.) NOTE: The suppress file relies on the "
                             "\"bug identifier\" generated by the analyzers "
                             "which is experimental, take care when relying "
                             "on it.")

    parser.add_argument('--export-source-suppress',
                        dest="create_suppress",
                        action="store_true",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Write suppress data from the suppression "
                             "annotations found in the source files that were "
                             "analyzed earlier that created the results. "
                             "The suppression information will be written "
                             "to the parameter of '--suppress'.")

    parser.add_argument('--print-steps',
                        dest="print_steps",
                        action="store_true",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Print the steps the analyzers took in finding "
                             "the reported defect.")

    parser.add_argument('-i', '--ignore', '--skip',
                        dest="skipfile",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Path to the Skipfile dictating which project "
                             "files should be omitted from analysis. Please "
                             "consult the User guide on how a Skipfile "
                             "should be laid out.")

    parser.add_argument('--trim-path-prefix',
                        type=str,
                        nargs='*',
                        dest="trim_path_prefix",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Removes leading path from files which will be "
                             "printed. So if you have /a/b/c/x.cpp and "
                             "/a/b/c/y.cpp then by removing \"/a/b/\" prefix "
                             "will print files like c/x.cpp and c/y.cpp. "
                             "If multiple prefix is given, the longest match "
                             "will be removed.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def parse(plist_file, metadata_dict, rh, file_report_map):
    """
    Prints the results in the given file to the standard output in a human-
    readable format.

    Returns the report statistics collected by the result handler.
    """

    if not plist_file.endswith(".plist"):
        LOG.debug("Skipping input file '%s' as it is not a plist.", plist_file)
        return set()

    LOG.debug("Parsing input file '%s'", plist_file)

    if 'result_source_files' in metadata_dict and \
            plist_file in metadata_dict['result_source_files']:
        analyzed_source_file = \
            metadata_dict['result_source_files'][plist_file]

        if analyzed_source_file not in file_report_map:
            file_report_map[analyzed_source_file] = []

    files, reports = rh.parse(plist_file)

    plist_mtime = util.get_last_mod_time(plist_file)

    changed_files = set()
    for source_file in files:
        if plist_mtime is None:
            # Failed to get the modification time for
            # a file mark it as changed.
            changed_files.add(source_file)
            LOG.warning('%s is missing since the last analysis.', source_file)
            continue

        file_mtime = util.get_last_mod_time(source_file)
        if file_mtime > plist_mtime:
            changed_files.add(source_file)
            LOG.warning('%s did change since the last analysis.', source_file)

    if not changed_files:
        for report in reports:
            file_path = report.file_path
            if file_path not in file_report_map:
                file_report_map[file_path] = []

            file_report_map[file_path].append(report)

    return changed_files


def convert_reports_to_json(input_dirs):
    """ Converts reports found in the input directories to json. """
    res = []

    input_files = set()
    for input_path in input_dirs:
        input_path = os.path.abspath(input_path)
        if os.path.isfile(input_path):
            input_files.add(input_path)
        elif os.path.isdir(input_path):
            _, _, file_names = next(os.walk(input_path), ([], [], []))
            input_paths = [os.path.join(input_path, file_name) for file_name
                           in file_names]
            input_files.update(input_paths)

    for input_file in input_files:
        if not input_file.endswith('.plist'):
            continue

        _, reports = plist_parser.parse_plist_file(input_file)
        for report in reports:
            res.append(report.to_json())

    return json.dumps(res)


def main(args):
    """
    Entry point for parsing some analysis results and printing them to the
    stdout in a human-readable format.
    """

    logger.setup_logger(args.verbose if 'verbose' in args else None)

    export = args.export if 'export' in args else None
    if export == 'html' and 'output_path' not in args:
        LOG.error("Argument --export not allowed without argument --output "
                  "when exporting to HTML.")
        sys.exit(1)

    context = analyzer_context.get_context()

    # To ensure the help message prints the default folder properly,
    # the 'default' for 'args.input' is a string, not a list.
    # But we need lists for the foreach here to work.
    if isinstance(args.input, str):
        args.input = [args.input]

    original_cwd = os.getcwd()

    suppr_handler = None
    if 'suppress' in args:
        __make_handler = False
        if not os.path.isfile(args.suppress):
            if 'create_suppress' in args:
                with open(args.suppress, 'w') as _:
                    # Just create the file.
                    __make_handler = True
                    LOG.info("Will write source-code suppressions to "
                             "suppress file: %s", args.suppress)
            else:
                LOG.warning("Suppress file '%s' given, but it does not exist"
                            " -- will not suppress anything.", args.suppress)
        else:
            __make_handler = True

        if __make_handler:
            suppr_handler = suppress_handler.\
                GenericSuppressHandler(args.suppress,
                                       'create_suppress' in args)
    elif 'create_suppress' in args:
        LOG.error("Can't use '--export-source-suppress' unless '--suppress "
                  "SUPPRESS_FILE' is also given.")
        sys.exit(2)

    processed_path_hashes = set()

    skip_handler = None
    if 'skipfile' in args:
        with open(args.skipfile, 'r') as skip_file:
            skip_handler = SkipListHandler(skip_file.read())

    trim_path_prefixes = args.trim_path_prefix if \
        'trim_path_prefix' in args else None

    if export == 'json':
        res = convert_reports_to_json(args.input)
        if 'output_path' in args:
            output_path = os.path.abspath(args.output_path)
            reports_json = os.path.join(output_path, 'reports.json')
            with io.open(reports_json,
                         mode='w',
                         encoding='utf-8') as output_f:
                output_f.write(res)

        return print(res)

    def trim_path_prefixes_handler(source_file):
        """
        Callback to util.trim_path_prefixes to prevent module dependency
        of plist_to_html
        """
        return util.trim_path_prefixes(source_file, trim_path_prefixes)

    html_builder = None

    def skip_html_report_data_handler(report_hash, source_file, report_line,
                                      checker_name, diag, files):
        """
        Report handler which skips bugs which were suppressed by source code
        comments.
        """
        report = Report(None, diag['path'], files)
        path_hash = get_report_path_hash(report, files)
        if path_hash in processed_path_hashes:
            LOG.debug("Skip report because it is a deduplication of an "
                      "already processed report!")
            LOG.debug("Path hash: %s", path_hash)
            LOG.debug(diag)
            return True

        skip = skip_report(report_hash,
                           source_file,
                           report_line,
                           checker_name,
                           suppr_handler)
        if skip_handler:
            skip |= skip_handler.should_skip(source_file)

        if not skip:
            processed_path_hashes.add(path_hash)

        return skip

    file_change = set()
    severity_stats = defaultdict(int)
    file_stats = defaultdict(int)
    report_count = 0

    for input_path in args.input:
        input_path = os.path.abspath(input_path)
        os.chdir(original_cwd)
        LOG.debug("Parsing input argument: '%s'", input_path)

        if export == 'html':
            output_path = os.path.abspath(args.output_path)

            if not html_builder:
                html_builder = \
                    PlistToHtml.HtmlBuilder(context.path_plist_to_html_dist,
                                            context.severity_map)

            LOG.info("Generating html output files:")
            PlistToHtml.parse(input_path,
                              output_path,
                              context.path_plist_to_html_dist,
                              skip_html_report_data_handler,
                              html_builder,
                              trim_path_prefixes_handler)
            continue

        files = []
        metadata_dict = {}
        if os.path.isfile(input_path):
            files.append(input_path)

        elif os.path.isdir(input_path):
            metadata_file = os.path.join(input_path, "metadata.json")
            if os.path.exists(metadata_file):
                metadata_dict = util.load_json_or_empty(metadata_file)
                LOG.debug(metadata_dict)

                if 'working_directory' in metadata_dict:
                    working_dir = metadata_dict['working_directory']
                    try:
                        os.chdir(working_dir)
                    except OSError as oerr:
                        LOG.debug(oerr)
                        LOG.error("Working directory %s is missing.\n"
                                  "Can not parse reports safely.", working_dir)
                        sys.exit(1)

            _, _, file_names = next(os.walk(input_path), ([], [], []))
            files = [os.path.join(input_path, file_name) for file_name
                     in file_names]

        file_report_map = defaultdict(list)

        rh = PlistToPlaintextFormatter(suppr_handler,
                                       skip_handler,
                                       context.severity_map,
                                       processed_path_hashes,
                                       trim_path_prefixes)
        rh.print_steps = 'print_steps' in args

        for file_path in files:
            f_change = parse(file_path, metadata_dict, rh, file_report_map)
            file_change = file_change.union(f_change)

        report_stats = rh.write(file_report_map)
        sev_stats = report_stats.get('severity')
        for severity in sev_stats:
            severity_stats[severity] += sev_stats[severity]

        f_stats = report_stats.get('files')
        for file_path in f_stats:
            file_stats[file_path] += f_stats[file_path]

        rep_stats = report_stats.get('reports')
        report_count += rep_stats.get("report_count", 0)

    print("\n----==== Summary ====----")
    if file_stats:
        vals = [[os.path.basename(k), v] for k, v in
                dict(file_stats).items()]
        keys = ['Filename', 'Report count']
        table = twodim_to_str('table', keys, vals, 1, True)
        print(table)

    if severity_stats:
        vals = [[k, v] for k, v in dict(severity_stats).items()]
        keys = ['Severity', 'Report count']
        table = twodim_to_str('table', keys, vals, 1, True)
        print(table)

    print("----=================----")
    print("Total number of reports: {}".format(report_count))
    print("----=================----")

    if file_change:
        changed_files = '\n'.join([' - ' + f for f in file_change])
        LOG.warning("The following source file contents changed since the "
                    "latest analysis:\n%s\nMultiple reports were not "
                    "shown and skipped from the statistics. Please "
                    "analyze your project again to update the "
                    "reports!", changed_files)

    os.chdir(original_cwd)

    # Create index.html and statistics.html for the generated html files.
    if html_builder:
        html_builder.create_index_html(args.output_path)
        html_builder.create_statistics_html(args.output_path)

        print('\nTo view statistics in a browser run:\n> firefox {0}'.format(
            os.path.join(args.output_path, 'statistics.html')))

        print('\nTo view the results in a browser run:\n> firefox {0}'.format(
            os.path.join(args.output_path, 'index.html')))
