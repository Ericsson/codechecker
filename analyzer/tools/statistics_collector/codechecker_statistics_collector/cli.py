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

# If we run this script in an environment where
# 'codechecker_statistics_collector' module is not available we should add the
# grandparent directory of this file to the system path.
# TODO: This section will not be needed when CodeChecker will be delivered as
# a python package and will be installed in a virtual environment with all the
# dependencies.
if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.realpath(__file__))
    os.sys.path.append(os.path.dirname(current_dir))

from codechecker_statistics_collector import post_process_stats  # noqa


LOG = logging.getLogger('StatisticsCollector')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def __add_arguments_to_parser(parser):
    """ Add arguments to the given parser. """
    parser.add_argument('-i', '--input',
                        type=str,
                        metavar='folder',
                        required=True,
                        help="Folder which contains statistical results of "
                             "clang to collect statistics.")

    parser.add_argument('output_dir',
                        type=str,
                        help="Output directory where the statistics yaml "
                             "files will be stored into.")

    parser.add_argument('--stats-min-sample-count',
                        action='store',
                        default="10",
                        type=int,
                        dest='stats_min_sample_count',
                        help="Minimum number of samples (function call "
                             "occurrences) to be collected for a statistics "
                             "to be relevant '<MIN-SAMPLE-COUNT>'.")

    parser.add_argument('--stats-relevance-threshold',
                        action='store',
                        default="0.85",
                        type=float,
                        dest='stats_relevance_threshold',
                        help="The minimum ratio of calls of function f that "
                             "must have a certain property property to "
                             "consider it true for that function (calculated "
                             "as calls with a property/all calls). "
                             "CodeChecker will warn for calls of f do not "
                             "have that property. '<RELEVANCE_THRESHOLD>'.")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Set verbosity level.")


def main():
    """ Statistics collector main command line. """
    parser = argparse.ArgumentParser(
        prog="post-process-stats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Collect statistics from the clang analyzer output.",
        epilog="""Example:
  post-process-stats -i /path/to/pre_processed_stats /path/to/stats""")

    __add_arguments_to_parser(parser)

    args = parser.parse_args()

    if 'verbose' in args and args.verbose:
        LOG.setLevel(logging.DEBUG)

    LOG.info("Starting to post-process statistical results...")

    post_process_stats.process(args.input, args.output_dir,
                               args.stats_min_sample_count,
                               args.stats_relevance_threshold)

    LOG.info("Done.")


if __name__ == "__main__":
    main()
