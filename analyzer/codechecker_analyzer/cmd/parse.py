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


import argparse
import os
import sys
from typing import Dict, Optional, Set

from codechecker_report_converter.util import dump_json_output, \
    load_json_or_empty
from codechecker_report_converter.report import report_file, \
    reports as reports_helper
from codechecker_report_converter.report.output import baseline, codeclimate, \
    gerrit, json as report_to_json, plaintext
from codechecker_report_converter.report.output.html import \
    html as report_to_html
from codechecker_report_converter.report.statistics import Statistics
from codechecker_report_converter.source_code_comment_handler import \
    REVIEW_STATUS_VALUES


from codechecker_analyzer import analyzer_context, suppress_handler

from codechecker_common import arg, logger, cmd_config
from codechecker_common.skiplist_handler import SkipListHandler, \
    SkipListHandlers


LOG = logger.get_logger('system')


def init_logger(level, stream=None, logger_name='system'):
    logger.setup_logger(level, stream)
    global LOG
    LOG = logger.get_logger(logger_name)


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

    cmd_config.add_option(parser)

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

    parser.add_argument('--trim-path-prefix',
                        type=str,
                        nargs='*',
                        dest="trim_path_prefix",
                        required=False,
                        default=argparse.SUPPRESS,
                        help="Removes leading path from files which will be "
                             "printed. For instance if you analyze files "
                             "'/home/jsmith/my_proj/x.cpp' and "
                             "'/home/jsmith/my_proj/y.cpp', but would prefer "
                             "to have them displayed as 'my_proj/x.cpp' and "
                             "'my_proj/y.cpp' in the web/CLI interface, "
                             "invoke CodeChecker with '--trim-path-prefix "
                             "\"/home/jsmith/\"'."
                             "If multiple prefixes are given, the longest "
                             "match will be removed. You may also use Unix "
                             "shell-like wildcards (e.g. '/*/jsmith/').")

    parser.add_argument('--review-status',
                        nargs='*',
                        dest="review_status",
                        metavar='REVIEW_STATUS',
                        choices=REVIEW_STATUS_VALUES,
                        default=["confirmed", "unreviewed"],
                        help="Filter results by review statuses. Valid "
                             "values are: {0}".format(
                                 ', '.join(REVIEW_STATUS_VALUES)))

    group = parser.add_argument_group("file filter arguments")

    group.add_argument('-i', '--ignore', '--skip',
                       dest="skipfile",
                       required=False,
                       default=argparse.SUPPRESS,
                       help="Path to the Skipfile dictating which project "
                            "files should be omitted from analysis. Please "
                            "consult the User guide on how a Skipfile "
                            "should be laid out.")

    group.add_argument('--file',
                       nargs='+',
                       dest="files",
                       metavar='FILE',
                       required=False,
                       default=argparse.SUPPRESS,
                       help="Filter results by file path. "
                            "The file path can contain multiple * "
                            "quantifiers which matches any number of "
                            "characters (zero or more). So if you have "
                            "/a/x.cpp and /a/y.cpp then \"/a/*.cpp\" "
                            "selects both.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(
        func=main, func_process_config_file=cmd_config.process_config_file)


def ch_workdir(metadata: Optional[Dict]):
    """ Change working directory to the one noted in metadata.json if this
    file exists and contains "working_directory".
    """
    if not metadata or 'working_directory' not in metadata:
        return

    working_dir = metadata['working_directory']
    try:
        os.chdir(working_dir)
    except OSError as oerr:
        LOG.debug(oerr)
        LOG.error("Working directory %s is missing.\nCan not parse reports "
                  "safely.", working_dir)
        sys.exit(1)


def get_metadata(dir_path: str) -> Optional[Dict]:
    """ Get metadata from the given dir path or None if not exists. """
    metadata_file = os.path.join(dir_path, "metadata.json")
    if os.path.exists(metadata_file):
        return load_json_or_empty(metadata_file)

    return None


def main(args):
    """
    Entry point for parsing some analysis results and printing them to the
    stdout in a human-readable format.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'export' in args and args.export not in [None, 'table', 'html']:
        stream = 'stderr'

    init_logger(args.verbose if 'verbose' in args else None, stream)

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

    def get_output_file_path(default_file_name: str) -> Optional[str]:
        """ Return an output file path. """
        if output_file_path:
            return output_file_path

        if output_dir_path:
            return os.path.join(output_dir_path, default_file_name)

    skip_handlers = SkipListHandlers()
    if 'files' in args:
        items = [f"+{file_path}" for file_path in args.files]
        items.append("-*")
        skip_handlers.append(SkipListHandler("\n".join(items)))
    if 'skipfile' in args:
        with open(args.skipfile, 'r', encoding='utf-8', errors='ignore') as f:
            skip_handlers.append(SkipListHandler(f.read()))

    trim_path_prefixes = args.trim_path_prefix if \
        'trim_path_prefix' in args else None

    all_reports = []
    statistics = Statistics()
    file_cache = {}  # For memory effiency.
    changed_files: Set[str] = set()
    processed_path_hashes = set()
    processed_file_paths = set()
    print_steps = 'print_steps' in args

    html_builder: Optional[report_to_html.HtmlBuilder] = None
    if export == 'html':
        html_builder = report_to_html.HtmlBuilder(
            context.path_plist_to_html_dist,
            context.checker_labels)

    for dir_path, file_paths in report_file.analyzer_result_files(args.input):
        metadata = get_metadata(dir_path)
        for file_path in file_paths:
            reports = report_file.get_reports(
                file_path, context.checker_labels, file_cache)

            reports = reports_helper.skip(
                reports, processed_path_hashes, skip_handlers, suppr_handler,
                src_comment_status_filter)

            statistics.num_of_analyzer_result_files += 1
            for report in reports:
                if report.changed_files:
                    changed_files.update(report.changed_files)

                statistics.add_report(report)

                if trim_path_prefixes:
                    report.trim_path_prefixes(trim_path_prefixes)

            all_reports.extend(reports)

            # Print reports continously.
            if not export:
                file_report_map = plaintext.get_file_report_map(
                    reports, file_path, metadata)
                plaintext.convert(
                    file_report_map, processed_file_paths, print_steps)
            elif export == 'html':
                print(f"Parsing input file '{file_path}'.")
                report_to_html.convert(
                    file_path, reports, output_dir_path,
                    html_builder)

    if export is None:  # Plain text output
        statistics.write()
    elif export == 'html':
        html_builder.finish(output_dir_path, statistics)
    elif export == 'json':
        data = report_to_json.convert(all_reports)
        dump_json_output(data, get_output_file_path("reports.json"))
    elif export == 'codeclimate':
        data = codeclimate.convert(all_reports)
        dump_json_output(data, get_output_file_path("reports.json"))
    elif export == 'gerrit':
        data = gerrit.convert(all_reports)
        dump_json_output(data, get_output_file_path("reports.json"))
    elif export == 'baseline':
        data = baseline.convert(all_reports)
        output_path = get_output_file_path("reports.baseline")
        if output_path:
            baseline.write(output_path, data)

    reports_helper.dump_changed_files(changed_files)

    if statistics.num_of_reports:
        sys.exit(2)
