#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import argparse
import logging
import os
import shutil
import sys

# If we run this script in an environment where 'codechecker_report_converter'
# module is not available we should add the grandparent directory of this file
# to the system path.
# TODO: This section will not be needed when CodeChecker will be delivered as
# a python package and will be installed in a virtual environment with all the
# dependencies.
if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.realpath(__file__))
    os.sys.path.insert(0, os.path.dirname(current_dir))

from codechecker_report_converter.clang_tidy.analyzer_result import \
    ClangTidyAnalyzerResult  # noqa
from codechecker_report_converter.cppcheck.analyzer_result import \
    CppcheckAnalyzerResult  # noqa
from codechecker_report_converter.infer.analyzer_result import \
    InferAnalyzerResult  # noqa
from codechecker_report_converter.sanitizers.address.analyzer_result import \
    ASANAnalyzerResult  # noqa
from codechecker_report_converter.sanitizers.memory.analyzer_result import \
    MSANAnalyzerResult  # noqa
from codechecker_report_converter.sanitizers.thread.analyzer_result import \
    TSANAnalyzerResult  # noqa
from codechecker_report_converter.sanitizers.ub.analyzer_result import \
    UBSANAnalyzerResult  # noqa
from codechecker_report_converter.spotbugs.analyzer_result import \
    SpotBugsAnalyzerResult  # noqa
from codechecker_report_converter.eslint.analyzer_result import \
    ESLintAnalyzerResult  # noqa
from codechecker_report_converter.pylint.analyzer_result import \
    PylintAnalyzerResult  # noqa
from codechecker_report_converter.tslint.analyzer_result import \
    TSLintAnalyzerResult  # noqa
from codechecker_report_converter.golint.analyzer_result import \
    GolintAnalyzerResult  # noqa
from codechecker_report_converter.pyflakes.analyzer_result import \
    PyflakesAnalyzerResult  # noqa
from codechecker_report_converter.markdownlint.analyzer_result import \
    MarkdownlintAnalyzerResult  # noqa
from codechecker_report_converter.coccinelle.analyzer_result import \
    CoccinelleAnalyzerResult  # noqa
from codechecker_report_converter.smatch.analyzer_result import \
    SmatchAnalyzerResult  # noqa
from codechecker_report_converter.kerneldoc.analyzer_result import \
    KernelDocAnalyzerResult  # noqa
from codechecker_report_converter.sphinx.analyzer_result import \
    SphinxAnalyzerResult  # noqa
from codechecker_report_converter.sparse.analyzer_result import \
    SparseAnalyzerResult  # noqa
from codechecker_report_converter.cpplint.analyzer_result import \
    CpplintAnalyzerResult  # noqa
from codechecker_report_converter.sanitizers.leak.analyzer_result import \
    LSANAnalyzerResult  # noqa


LOG = logging.getLogger('ReportConverter')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


class RawDescriptionDefaultHelpFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter
):
    """ Adds default values to argument help and retains any formatting in
    descriptions. """
    pass


supported_converters = {
    ClangTidyAnalyzerResult.TOOL_NAME: ClangTidyAnalyzerResult,
    CppcheckAnalyzerResult.TOOL_NAME: CppcheckAnalyzerResult,
    InferAnalyzerResult.TOOL_NAME: InferAnalyzerResult,
    GolintAnalyzerResult.TOOL_NAME: GolintAnalyzerResult,
    ASANAnalyzerResult.TOOL_NAME: ASANAnalyzerResult,
    ESLintAnalyzerResult.TOOL_NAME: ESLintAnalyzerResult,
    MSANAnalyzerResult.TOOL_NAME: MSANAnalyzerResult,
    PylintAnalyzerResult.TOOL_NAME: PylintAnalyzerResult,
    PyflakesAnalyzerResult.TOOL_NAME: PyflakesAnalyzerResult,
    TSANAnalyzerResult.TOOL_NAME: TSANAnalyzerResult,
    TSLintAnalyzerResult.TOOL_NAME: TSLintAnalyzerResult,
    UBSANAnalyzerResult.TOOL_NAME: UBSANAnalyzerResult,
    SpotBugsAnalyzerResult.TOOL_NAME: SpotBugsAnalyzerResult,
    MarkdownlintAnalyzerResult.TOOL_NAME: MarkdownlintAnalyzerResult,
    CoccinelleAnalyzerResult.TOOL_NAME: CoccinelleAnalyzerResult,
    SmatchAnalyzerResult.TOOL_NAME: SmatchAnalyzerResult,
    KernelDocAnalyzerResult.TOOL_NAME: KernelDocAnalyzerResult,
    SphinxAnalyzerResult.TOOL_NAME: SphinxAnalyzerResult,
    SparseAnalyzerResult.TOOL_NAME: SparseAnalyzerResult,
    CpplintAnalyzerResult.TOOL_NAME: CpplintAnalyzerResult,
    LSANAnalyzerResult.TOOL_NAME: LSANAnalyzerResult
}

supported_metadata_keys = ["analyzer_command", "analyzer_version"]


def output_to_plist(analyzer_result, parser_type, output_dir, file_name,
                    clean=False, metadata=None):
    """ Creates .plist files from the given output to the given output dir. """
    if clean and os.path.isdir(output_dir):
        LOG.info("Previous analysis results in '%s' have been removed, "
                 "overwriting with current result", output_dir)
        shutil.rmtree(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    parser = supported_converters[parser_type]()
    parser.transform(analyzer_result, output_dir, file_name, metadata)


def process_metadata(metadata):
    """ Returns a tuple of valid and invalid metadata values. """
    if not metadata:
        return {}, {}

    valid_values = {}
    invalid_values = {}
    for m in metadata:
        key, value = m.split("=", 1)
        if key in supported_metadata_keys:
            valid_values[key] = value
        else:
            invalid_values[key] = value

    return valid_values, invalid_values


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
                              ', '.join(sorted(supported_converters)) + ".")

    parser.add_argument('--meta',
                        nargs='*',
                        dest='meta',
                        metavar='META',
                        required=False,
                        help="Metadata information which will be stored "
                             "alongside the run when the created report "
                             "directory will be stored to a running "
                             "CodeChecker server. It has the following "
                             "format: key=value. Valid key values are: "
                             "{0}.".format(', '.join(supported_metadata_keys)))

    parser.add_argument('--filename',
                        type=str,
                        dest='filename',
                        metavar='FILENAME',
                        default="{source_file}_{analyzer}",
                        help="This option can be used to override the default "
                             "plist file name output of this tool. This tool "
                             "can produce multiple plist files on the given "
                             "code analyzer output result file. The problem "
                             "is if we run this tool multiple times on the "
                             "same directory, it may override some plist "
                             "files. To prevent this we can generate a unique "
                             "hash into the plist file names with this "
                             "option. For example: "
                             "'{source_file}_{analyzer}_xxxxx'. {source_file} "
                             "and {analyzer} are special values which will "
                             "be replaced with the current analyzer and "
                             "source file name where the bug was found.")

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
        description="""
Creates a CodeChecker report directory from the given code analyzer output
which can be stored to a CodeChecker web server.""",
        epilog="""
Supported analyzers:
{0}""".format('\n'.join(["  {0} - {1}, {2}".format(
                         tool_name,
                         supported_converters[tool_name].NAME,
                         supported_converters[tool_name].URL)
                         for tool_name in sorted(supported_converters)])),
        formatter_class=RawDescriptionDefaultHelpFormatter
    )
    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if 'verbose' in args and args.verbose:
        LOG.setLevel(logging.DEBUG)

    valid_metadata_values, invalid_metadata_values = \
        process_metadata(args.meta)

    if invalid_metadata_values:
        LOG.error("The following metadata keys are invalid: %s. Valid key "
                  "values are: %s.",
                  ', '.join(invalid_metadata_values),
                  ', '.join(supported_metadata_keys))
        sys.exit(1)

    return output_to_plist(args.input, args.type, args.output_dir,
                           args.filename, args.clean, valid_metadata_values)


if __name__ == "__main__":
    main()
