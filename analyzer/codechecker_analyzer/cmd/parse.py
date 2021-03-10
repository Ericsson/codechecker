# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Defines the CodeChecker action for parsing a set of analysis results into a
human-readable format.
"""


from collections import defaultdict
import argparse
import json
import math
import os
from operator import itemgetter
import sys
import traceback
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from plist_to_html import PlistToHtml

from codechecker_analyzer import analyzer_context, suppress_handler

from codechecker_common import arg, logger, plist_parser, util, cmd_config
from codechecker_common.checker_labels import CheckerLabels
from codechecker_common.output import baseline, json as out_json, twodim, \
    codeclimate, gerrit
from codechecker_common.skiplist_handler import SkipListHandler
from codechecker_common.source_code_comment_handler import \
    REVIEW_STATUS_VALUES, SourceCodeCommentHandler, SpellException
from codechecker_common.report import Report

from codechecker_report_hash.hash import get_report_path_hash

LOG = logger.get_logger('system')

EXPORT_TYPES = ['html', 'json', 'codeclimate', 'gerrit', 'baseline']

epilog_env_var = f"""
  CC_CHANGED_FILES       Path of changed files json from Gerrit. Use it when
                         generating gerrit output.
  CC_REPO_DIR            Root directory of the sources, i.e. the directory
                         where the repository was cloned. Use it when
                         generating gerrit output.
  CC_REPORT_URL          URL where the report can be found. Use it when
                         generating gerrit output.
"""

epilog_exit_status = """
0 - No report
1 - CodeChecker error
2 - At least one report emitted by an analyzer
"""


class PlistToPlaintextFormatter:
    """
    Parse and format plist reports to a more human readable format.
    """

    def __init__(self,
                 src_comment_handler,
                 skip_handler: Callable[[str], bool],
                 checker_labels,
                 processed_path_hashes,
                 trim_path_prefixes,
                 src_comment_status_filter=None):

        self.__checker_labels = checker_labels
        self.print_steps = False
        self.src_comment_handler = src_comment_handler
        self._skip_handler = skip_handler
        self.src_comment_status_filter = src_comment_status_filter
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
    def __format_bug_event(name, severity, event, source_file,
                           review_status=None):

        loc = event['location']
        if name:
            out = '[%s] %s:%d:%d: %s [%s]' % (severity,
                                              source_file,
                                              loc['line'],
                                              loc['col'],
                                              event['message'],
                                              name)
            if review_status:
                rw_status = review_status.capitalize().replace('_', ' ')
                out = '%s [%s]' % (out, rw_status)

            return out
        else:
            fname = os.path.basename(source_file)
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
    def parse(plist_file) -> Tuple[Dict[int, str], List[Report]]:
        """
        Parse a plist report file.
        """
        files, reports = {}, []
        try:
            files, reports = plist_parser.parse_plist_file(plist_file)
        except Exception as ex:
            traceback.print_stack()
            LOG.error('The generated plist is not valid!')
            LOG.error(ex)
        finally:
            return files, reports

    def write(self,
              file_report_map: Dict[str, List[Report]],
              output=sys.stdout):
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
                path_hash = get_report_path_hash(report)
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
                if self._skip_handler(f_path):
                    LOG.debug("Skipped report in '%s'", f_path)
                    LOG.debug(report)
                    continue

                last_report_event = report.bug_path[-1]
                source_file = \
                    report.files[last_report_event['location']['file']]

                report_line = last_report_event['location']['line']
                report_hash = \
                    report.main['issue_hash_content_of_line_in_context']
                checker_name = report.main['check_name']

                skip, source_code_comments = \
                    skip_report(report_hash,
                                source_file,
                                report_line,
                                checker_name,
                                self.src_comment_handler,
                                self.src_comment_status_filter)

                if self.src_comment_handler and source_code_comments:
                    self.src_comment_handler.store_suppress_bug_id(
                        report_hash, os.path.basename(source_file),
                        source_code_comments[0]['message'],
                        source_code_comments[0]['status'])

                if skip:
                    continue

                if self._trim_path_prefixes:
                    report.trim_path_prefixes(self._trim_path_prefixes)

                trimmed_source_file = \
                    report.files[last_report_event['location']['file']]

                file_stats[f_path] += 1
                severity = self.__checker_labels.severity(checker_name)
                severity_stats[severity] += 1
                report_count["report_count"] += 1

                review_status = None
                if len(source_code_comments) == 1:
                    review_status = source_code_comments[0]['status']

                output.write(self.__format_bug_event(checker_name,
                                                     severity,
                                                     last_report_event,
                                                     trimmed_source_file,
                                                     review_status))
                output.write('\n')

                # Print source code comments.
                for source_code_comment in source_code_comments:
                    output.write(source_code_comment['line'].rstrip())
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
                        output.write(
                            self.__format_bug_event(None,
                                                    None,
                                                    event,
                                                    source_file))
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
                src_comment_handler=None, src_comment_status_filter=None):
    """
    Returns a tuple where the first value will be True if the report was
    suppressed in the source code, otherwise False. The second value will be
    the list of available source code comments.
    """
    bug = {'hash_value': report_hash, 'file_path': source_file}
    if src_comment_handler and src_comment_handler.get_suppressed(bug):
        LOG.debug("Suppressed by suppress file: %s:%s [%s] %s", source_file,
                  report_line, checker_name, report_hash)
        return True, []

    sc_handler = SourceCodeCommentHandler()

    src_comment_data = []
    # Check for source code comment.
    with open(source_file, encoding='utf-8', errors='ignore') as sf:
        try:
            src_comment_data = sc_handler.filter_source_line_comments(
                sf,
                report_line,
                checker_name)
        except SpellException as ex:
            LOG.warning("%s contains %s",
                        os.path.basename(source_file),
                        str(ex))

    if not src_comment_data:
        skip = True if src_comment_status_filter and \
            'unreviewed' not in src_comment_status_filter else False
        return skip, src_comment_data

    num_of_suppress_comments = len(src_comment_data)
    if num_of_suppress_comments == 1:
        status = src_comment_data[0]['status']

        LOG.debug("Suppressed by source code comment.")

        if src_comment_status_filter and \
                status not in src_comment_status_filter:
            return True, src_comment_data

    if num_of_suppress_comments > 1:
        LOG.error("Multiple source code comment can be found "
                  "for '%s' checker in '%s' at line %d.",
                  checker_name, source_file, report_line)
        sys.exit(1)

    return False, src_comment_data


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """
    return {
        'prog': 'CodeChecker parse',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Parse and pretty-print the summary and results from one or more
'codechecker-analyze' result files. Bugs which are commented by using
"false_positive", "suppress" and "intentional" source code comments will not be
printed by the `parse` command.""",

        'epilog': f"""
Environment variables
------------------------------------------------
{epilog_env_var}

Exit status
------------------------------------------------
{epilog_exit_status}
""",

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

    parser.add_argument('--config',
                        dest='config_file',
                        required=False,
                        help="R|Allow the configuration from an "
                             "explicit JSON based configuration file. "
                             "The value of the 'parse' key in the "
                             "config file will be emplaced as command "
                             "line arguments. The format of "
                             "configuration file is:\n"
                             "{\n"
                             "  \"parse\": [\n"
                             "    \"--trim-path-prefix\",\n"
                             "    \"$HOME/workspace\"\n"
                             "  ]\n"
                             "}")

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
                             choices=EXPORT_TYPES,
                             help="R|Specify extra output format type.\n"
                                  "'codeclimate' format can be used for "
                                  "Code Climate and for GitLab integration. "
                                  "For more information see:\n"
                                  "https://github.com/codeclimate/platform/"
                                  "blob/master/spec/analyzers/SPEC.md"
                                  "#data-types\n"
                                  "'baseline' output can be used to integrate "
                                  "CodeChecker into your local workflow "
                                  "without using a CodeChecker server. For "
                                  "more information see our usage guide.")

    output_opts.add_argument('-o', '--output',
                             dest="output_path",
                             default=argparse.SUPPRESS,
                             help="Store the output in the given file/folder. "
                                  "Note: baseline files must have extension "
                                  "'.baseline'.")

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

    parser.add_argument('--review-status',
                        nargs='*',
                        dest="review_status",
                        metavar='REVIEW_STATUS',
                        choices=REVIEW_STATUS_VALUES,
                        default=["confirmed", "unreviewed"],
                        help="Filter results by review statuses. Valid "
                             "values are: {0}".format(
                                 ', '.join(REVIEW_STATUS_VALUES)))

    logger.add_verbose_arguments(parser)
    parser.set_defaults(
        func=main, func_process_config_file=cmd_config.process_config_file)


def parse_with_plt_formatter(plist_file: str,
                             metadata: Dict,
                             plist_pltf: PlistToPlaintextFormatter,
                             file_report_map: Dict[str, List[Report]]) -> Set:
    """Parse a plist with plaintext formatter and collect changed source files.

    Returns the report statistics collected by the result handler.
    """

    if not plist_file.endswith(".plist"):
        LOG.debug("Skipping input file '%s' as it is not a plist.", plist_file)
        return set()

    LOG.debug("Parsing input file '%s'", plist_file)

    result_source_files = {}
    if 'result_source_files' in metadata:
        result_source_files = metadata['result_source_files']
    else:
        for tool in metadata.get('tools', {}):
            result_src_files = tool.get('result_source_files', {})
            result_source_files.update(result_src_files.items())

    if plist_file in result_source_files:
        analyzed_source_file = \
            result_source_files[plist_file]

        if analyzed_source_file not in file_report_map:
            file_report_map[analyzed_source_file] = []

    files, reports = plist_pltf.parse(plist_file)
    plist_mtime = util.get_last_mod_time(plist_file)

    changed_files = set()
    for _, source_file in files.items():
        if plist_mtime is None:
            # Failed to get the modification time for
            # a file mark it as changed.
            changed_files.add(source_file)
            LOG.warning('%s is missing since the last analysis.', source_file)
            continue

        file_mtime = util.get_last_mod_time(source_file)
        if not file_mtime:
            changed_files.add(source_file)
            LOG.warning('%s does not exist.', source_file)
            continue

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


def _parse_convert_reports(
    input_dirs: List[str],
    out_format: str,
    checker_labels: CheckerLabels,
    trim_path_prefixes: Optional[List[str]],
    skip_handler: Callable[[str], bool]) \
        -> Tuple[Union[Dict, List], int]:
    """Parse and convert the reports from the input dirs to the out_format.

    Retuns a dictionary which can be converted to the out_format type of
    json to be printed out or saved on the disk.
    """

    assert(out_format in [fmt for fmt in EXPORT_TYPES if fmt != 'html'])

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

    all_reports = []
    for input_file in input_files:
        if not input_file.endswith('.plist'):
            continue
        _, reports = plist_parser.parse_plist_file(input_file)
        reports = [report for report in reports
                   if not skip_handler(report.file_path)]
        all_reports.extend(reports)

    if trim_path_prefixes:
        for report in all_reports:
            report.trim_path_prefixes(trim_path_prefixes)

    number_of_reports = len(all_reports)
    if out_format == "baseline":
        return (baseline.convert(all_reports), number_of_reports)

    if out_format == "codeclimate":
        return (codeclimate.convert(all_reports, checker_labels),
                number_of_reports)

    if out_format == "gerrit":
        return gerrit.convert(all_reports, checker_labels), number_of_reports

    if out_format == "json":
        return [out_json.convert_to_parse(r) for r in all_reports], \
            number_of_reports


def _generate_json_output(
    checker_labels: CheckerLabels,
    input_dirs: List[str],
    output_type: str,
    output_file_path: Optional[str],
    trim_path_prefixes: Optional[List[str]],
    skip_handler: Callable[[str], bool]
) -> int:
    """
    Generates JSON based appearance of analyzing and optionally saves it to
    file.

    This function only responsible for saving and returning data. The data
    conversion performed by underlying utility function.

    Parameters
    ----------
    checker_labels : CheckerLabels
        Binary format of a piece of configuration.
    input_dirs : List[str]
        Directories where the underlying analyzer processes have placed the
        result of analyzing.
    output_type : str
        Specifies the type of output. It can be gerrit, json, codeclimate.
    output_file_path : Optional[str]
        Path of the output file. If it contains file name then generated output
        will be written into.
    trim_path_prefixes : Optional[List[str]]
        A list of path fragments that will be trimmed from beginning of source
        file names before file names will be written to the output.
    skip_handler : Callable[[str], bool]
        A callable that call with a file name and returns a bool that indicates
        that the file should skip or not from the output.
    """

    try:
        reports, number_of_reports = _parse_convert_reports(
            input_dirs, output_type, checker_labels, trim_path_prefixes,
            skip_handler)
        output_text = json.dumps(reports)

        if output_file_path:
            with open(output_file_path, mode='w', encoding='utf-8',
                      errors="ignore") as output_f:
                output_f.write(output_text)

        print(output_text)
        return 2 if number_of_reports else 0
    except Exception as ex:
        LOG.error(ex)
        return 1


def main(args):
    """
    Entry point for parsing some analysis results and printing them to the
    stdout in a human-readable format.
    """

    logger.setup_logger(args.verbose if 'verbose' in args else None)

    try:
        cmd_config.check_config_file(args)
    except FileNotFoundError as fnerr:
        LOG.error(fnerr)
        sys.exit(1)

    export = args.export if 'export' in args else None
    if export == 'html' and 'output_path' not in args:
        LOG.error("Argument --export not allowed without argument --output "
                  "when exporting to HTML.")
        sys.exit(1)

    if export == 'gerrit' and not gerrit.mandatory_env_var_is_set():
        sys.exit(1)

    if export and export not in EXPORT_TYPES:
        LOG.error("Unknown export format: %s", export)
        sys.exit(1)

    context = analyzer_context.get_context()

    # To ensure the help message prints the default folder properly,
    # the 'default' for 'args.input' is a string, not a list.
    # But we need lists for the foreach here to work.
    if isinstance(args.input, str):
        args.input = [args.input]

    original_cwd = os.getcwd()

    src_comment_status_filter = args.review_status

    suppr_handler = None
    if 'suppress' in args:
        __make_handler = False
        if not os.path.isfile(args.suppress):
            if 'create_suppress' in args:
                with open(args.suppress, 'w',
                          encoding='utf-8', errors='ignore') as _:
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
                                       'create_suppress' in args,
                                       src_comment_status_filter)
    elif 'create_suppress' in args:
        LOG.error("Can't use '--export-source-suppress' unless '--suppress "
                  "SUPPRESS_FILE' is also given.")
        sys.exit(1)

    processed_path_hashes = set()

    skip_file_content = ""
    if 'skipfile' in args:
        with open(args.skipfile, 'r',
                  encoding='utf-8', errors='ignore') as skip_file:
            skip_file_content = skip_file.read()

    skip_handler = SkipListHandler(skip_file_content)

    trim_path_prefixes = args.trim_path_prefix if \
        'trim_path_prefix' in args else None

    output_dir_path = None
    output_file_path = None
    if 'output_path' in args:
        output_path = os.path.abspath(args.output_path)

        if export == 'html':
            output_dir_path = output_path
        else:
            if os.path.exists(output_path) and os.path.isdir(output_path):
                # For backward compatibility reason we handle the use case
                # when directory is provided to this command.
                LOG.error("Please provide a file path instead of a directory "
                          "for '%s' export type!", export)
                sys.exit(1)

            if export == 'baseline' and not baseline.check(output_path):
                LOG.error("Baseline files must have '.baseline' extensions.")
                sys.exit(1)

            output_file_path = output_path
            output_dir_path = os.path.dirname(output_file_path)

        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)

    def get_output_file_path(default_file_name) -> Optional[str]:
        """ Return an output file path. """
        if output_file_path:
            return output_file_path

        if output_dir_path:
            return os.path.join(output_dir_path, default_file_name)

    if export:
        if export == 'baseline':
            report_hashes, number_of_reports = _parse_convert_reports(
                args.input, export, context.checker_labels, trim_path_prefixes,
                skip_handler)

            output_path = get_output_file_path("reports.baseline")
            if output_path:
                baseline.write(output_path, report_hashes)

            sys.exit(2 if number_of_reports else 0)

        # The HTML part will be handled separately below.
        if export != 'html':
            output_path = get_output_file_path("reports.json")
            sys.exit(_generate_json_output(
                context.checker_labels, args.input, export, output_path,
                trim_path_prefixes, skip_handler))

    html_builder = None
    report_count = 0

    def skip_html_report_data_handler(report_hash, source_file, report_line,
                                      checker_name, diag, files):
        """
        Report handler which skips bugs which were suppressed by source code
        comments. This function will return a tuple. The first element
        will decide whether the report should be skipped or not and the second
        element will be a list of source code comments related to the actual
        report.
        """
        files_dict = {k: v for k, v in enumerate(files)}
        report = Report({'check_name': checker_name},
                        diag['path'],
                        files_dict,
                        metadata=None)
        path_hash = get_report_path_hash(report)
        if path_hash in processed_path_hashes:
            LOG.debug("Skip report because it is a deduplication of an "
                      "already processed report!")
            LOG.debug("Path hash: %s", path_hash)
            LOG.debug(diag)
            return True, []

        skip, source_code_comments = skip_report(report_hash,
                                                 source_file,
                                                 report_line,
                                                 checker_name,
                                                 suppr_handler,
                                                 src_comment_status_filter)

        if suppr_handler and source_code_comments:
            suppr_handler.store_suppress_bug_id(
                report_hash, os.path.basename(source_file),
                source_code_comments[0]['message'],
                source_code_comments[0]['status'])

        skip |= skip_handler(source_file)

        if not skip:
            processed_path_hashes.add(path_hash)
            nonlocal report_count
            report_count += 1

        return skip, source_code_comments

    file_change = set()
    severity_stats = defaultdict(int)
    file_stats = defaultdict(int)

    for input_path in args.input:
        input_path = os.path.abspath(input_path)
        os.chdir(original_cwd)
        LOG.debug("Parsing input argument: '%s'", input_path)

        if export == 'html':
            if not html_builder:
                html_builder = \
                    PlistToHtml.HtmlBuilder(context.path_plist_to_html_dist,
                                            context.checker_labels)

            LOG.info("Generating html output files:")
            PlistToHtml.parse(input_path,
                              output_dir_path,
                              context.path_plist_to_html_dist,
                              skip_html_report_data_handler,
                              html_builder,
                              util.TrimPathPrefixHandler(trim_path_prefixes))
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

        plist_pltf = PlistToPlaintextFormatter(suppr_handler,
                                               skip_handler,
                                               context.checker_labels,
                                               processed_path_hashes,
                                               trim_path_prefixes,
                                               src_comment_status_filter)
        plist_pltf.print_steps = 'print_steps' in args

        for file_path in files:
            f_change = parse_with_plt_formatter(file_path,
                                                metadata_dict,
                                                plist_pltf,
                                                file_report_map)
            file_change = file_change.union(f_change)

        report_stats = plist_pltf.write(file_report_map)
        sev_stats = report_stats.get('severity')
        for severity in sev_stats:
            severity_stats[severity] += sev_stats[severity]

        f_stats = report_stats.get('files')
        for file_path in f_stats:
            file_stats[file_path] += f_stats[file_path]

        rep_stats = report_stats.get('reports')
        report_count += rep_stats.get("report_count", 0)

    # Create index.html and statistics.html for the generated html files.
    if html_builder:
        html_builder.create_index_html(output_dir_path)
        html_builder.create_statistics_html(output_dir_path)

        print('\nTo view statistics in a browser run:\n> firefox {0}'.format(
            os.path.join(output_dir_path, 'statistics.html')))

        print('\nTo view the results in a browser run:\n> firefox {0}'.format(
            os.path.join(output_dir_path, 'index.html')))
    else:
        print("\n----==== Summary ====----")
        if file_stats:
            vals = [[os.path.basename(k), v] for k, v in
                    dict(file_stats).items()]
            vals.sort(key=itemgetter(0))
            keys = ['Filename', 'Report count']
            table = twodim.to_str('table', keys, vals, 1, True)
            print(table)

        if severity_stats:
            vals = [[k, v] for k, v in dict(severity_stats).items()]
            vals.sort(key=itemgetter(0))
            keys = ['Severity', 'Report count']
            table = twodim.to_str('table', keys, vals, 1, True)
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

    if report_count != 0:
        sys.exit(2)
