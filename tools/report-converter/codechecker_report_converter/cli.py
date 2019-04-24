#!/usr/bin/env python3
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------


import argparse
import logging
import os
import shutil

from codechecker_report_converter.clang_tidy.analyzer_result import \
    ClangTidyAnalyzerResult
from codechecker_report_converter.cppcheck.analyzer_result import \
    CppcheckAnalyzerResult
from codechecker_report_converter.sanitizers.address.analyzer_result import \
    ASANAnalyzerResult
from codechecker_report_converter.sanitizers.memory.analyzer_result import \
    MSANAnalyzerResult
from codechecker_report_converter.sanitizers.thread.analyzer_result import \
    TSANAnalyzerResult
from codechecker_report_converter.sanitizers.ub.analyzer_result import \
    UBSANAnalyzerResult


LOG = logging.getLogger('ReportConverter')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


supported_converters = {
    ClangTidyAnalyzerResult.TOOL_NAME: ClangTidyAnalyzerResult,
    CppcheckAnalyzerResult.TOOL_NAME: CppcheckAnalyzerResult,
    ASANAnalyzerResult.TOOL_NAME: ASANAnalyzerResult,
    MSANAnalyzerResult.TOOL_NAME: MSANAnalyzerResult,
    TSANAnalyzerResult.TOOL_NAME: TSANAnalyzerResult,
    UBSANAnalyzerResult.TOOL_NAME: UBSANAnalyzerResult
}


def output_to_plist(analyzer_result, parser_type, output_dir, clean=False):
    """ Creates .plist files from the given output to the given output dir. """
    if clean and os.path.isdir(output_dir):
        LOG.info("Previous analysis results in '%s' have been removed, "
                 "overwriting with current result", output_dir)
        shutil.rmtree(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    parser = supported_converters[parser_type]()
    parser.transform(analyzer_result, output_dir)


def __add_arguments_to_parser(parser):
    """ Add arguments to the the given parser. """
    parser.add_argument('input',
                        type=str,
                        metavar='file',
                        default=argparse.SUPPRESS,
                        help="Code analyzer output result file which will be "
                             "parsed and used to generate a CodeChecker "
                             "report directory.")

    parser.add_argument('-o', '--output',
                        dest="output_dir",
                        required=True,
                        default=argparse.SUPPRESS,
                        help="This directory will be used to generate "
                             "CodeChecker report directory files.")

    parser.add_argument('-t', '--type',
                        dest='type',
                        metavar='TYPE',
                        required=True,
                        choices=supported_converters,
                        default=argparse.SUPPRESS,
                        help="Specify the format of the code analyzer output. "
                             "Currently supported output types are: " +
                              ', '.join(supported_converters) + ".")

    parser.add_argument('-c', '--clean',
                        dest="clean",
                        required=False,
                        action='store_true',
                        help="Delete files stored in the output directory.")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Set verbosity level.")


def main():
    """ Report converter main command line. """
    parser = argparse.ArgumentParser(
        prog="report-converter",
        description="Creates a CodeChecker report directory from the given "
                    "code analyzer output which can be stored to a "
                    "CodeChecker web server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if 'verbose' in args and args.verbose:
        LOG.setLevel(logging.DEBUG)

    return output_to_plist(args.input, args.type, args.output_dir,
                           args.clean)


if __name__ == "__main__":
    main()
