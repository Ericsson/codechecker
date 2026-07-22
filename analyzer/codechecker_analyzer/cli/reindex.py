# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import sys
from codechecker_analyzer.cachedb import CacheDB
from codechecker_common import arg, logger
from codechecker_common.compatibility.multiprocessing import Pool, cpu_count
from codechecker_report_converter.report.parser import plist as plistparser
from typing import List, Tuple

LOG = logger.get_logger('system')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker reindex',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,
        'description': """
The analysis cache database is a SQLite database located in the
report directory, designed to speed up the parsing process.
In case it is missing or outdated, one can use the 'reindex' command to
recreate/update this database.""",
        'help': "Recreate/update the cache database given a report directory."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='+',
                        metavar='folder',
                        help="The analysis result folder(s) containing "
                             "analysis results which should be "
                             "reindexed.")

    parser.add_argument('-j', '--jobs',
                        type=int,
                        dest="jobs",
                        required=False,
                        default=cpu_count(),
                        help="Number of threads to use for reindex. More "
                             "threads mean faster reindex at the cost of "
                             "using more memory.")

    parser.add_argument('-f', '--force',
                        action="store_true",
                        dest="force",
                        required=False,
                        default=False,
                        help="Drop the previous cache database and do a "
                             "clean reindex.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    logger.setup_logger(args.verbose if 'verbose' in args else None)
    for i in args.input:
        update_cache_db(i, args.force, args.jobs)


def __process_file(file_path: str) -> Tuple[str, List[str]]:
    with open(file_path, 'rb') as fp:
        plist = plistparser.parse(fp)

        file_list = [] if plist is None else \
            plistparser.get_file_list(plist, os.path.dirname(file_path))
        return (file_path, file_list)


def update_cache_db(report_dir: str, force: bool, jobs: int):
    if not os.path.isdir(report_dir):
        LOG.error("Directory %s does not exist!", report_dir)
        sys.exit(1)

    report_dir = os.path.abspath(report_dir)
    cachedb = CacheDB(report_dir, force)
    indexed_files = cachedb.get_indexed_plist_files()

    plist_files = filter(lambda f: f.endswith(
                    plistparser.EXTENSION), os.listdir(report_dir))
    plist_files = map(lambda f: os.path.abspath(
                    os.path.join(report_dir, f)), plist_files)
    plist_files = list(filter(lambda f: f not in indexed_files, plist_files))

    with Pool(jobs) as p:
        res = p.map(__process_file, plist_files)
        for (plist_file, sources) in res:
            if sources != []:
                cachedb.insert_plist_sources(plist_file, sources)

    cachedb.close_connection()
