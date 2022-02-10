# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
'CodeChecker log' executes a build action and registers a compilation database
for the given build, using an external tool such as scan-build-py or ld-logger.

This module contains the basic definitions for how 'CodeChecker log' is to be
invoked and ran.
"""


import argparse
import os

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.buildlog import build_manager
from codechecker_analyzer.buildlog.host_check import check_intercept
from codechecker_analyzer.buildlog.host_check import check_ldlogger

from codechecker_common import arg, logger


epilog_env_var = f"""
  CC_LOGGER_ABS_PATH       If the environment variable is defined, all relative
                           paths in the compilation commands after '-I,
                           -idirafter, -imultilib, -iquote, -isysroot -isystem,
                           -iwithprefix, -iwithprefixbefore, -sysroot,
                           --sysroot' will be converted to absolute PATH when
                           written into the compilation database.
  CC_LOGGER_DEBUG_FILE     Output file to print log messages. By default if we
                           run the log command in debug mode it will generate
                           a 'codechecker.logger.debug' file beside the log
                           file.
  CC_LOGGER_DEF_DIRS       If the environment variable is defined, the logger
                           will extend the compiler argument list in the
                           compilation database with the pre-configured include
                           paths of the logged compiler.
  CC_LOGGER_GCC_LIKE       Set to to a colon separated list to change which
                           compilers should be logged. For example (default):
                           export CC_LOGGER_GCC_LIKE="gcc:g++:clang:clang++:
                           cc:c++". The logger will match any compilers with
                           'gcc', 'g++', 'clang', 'clang++', 'cc' and 'c++' in
                           their filenames.
  CC_LOGGER_KEEP_LINK      If its value is not 'true' then object files will be
                           removed from the build action. For example in case
                           of this build command: 'gcc main.c object1.o
                           object2.so' the 'object1.o' and 'object2.so' will be
                           removed and only 'gcc main.c' will be captured. If
                           only object files are provided to the compiler then
                           the complete build action will be thrown away. This
                           means that build actions which only perform linking
                           will not be captured. We consider a file as object
                           file if its extension is '.o', '.so' or '.a'.
"""


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    # Prefer using ldlogger over intercept-build.
    is_ldlogger = check_ldlogger(os.environ)
    is_intercept = False if is_ldlogger else check_intercept(os.environ)
    ldlogger_settings = """
ld-logger can be fine-tuned with some environment variables. For details see
the following documentation:
https://github.com/Ericsson/codechecker/blob/master/analyzer/tools/
build-logger/README.md#usage""" if not is_ldlogger else ""

    return {
        'prog': 'CodeChecker log',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': """
Runs the given build command and records the executed compilation steps. These
steps are written to the output file in a JSON format.

Available build logger tool that will be used is '{0}'.{1}
""".format('intercept-build' if is_intercept else 'ld-logger',
           ldlogger_settings),

        'epilog': f"""
Environment variables
------------------------------------------------
{epilog_env_var}
""",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Run a build command and collect the executed compilation "
                "commands, storing them in a JSON file."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        type=str,
                        dest="logfile",
                        default=argparse.SUPPRESS,
                        required=True,
                        help="Path of the file to write the collected "
                             "compilation commands to. If the file already "
                             "exists, it will be overwritten.")

    parser.add_argument('-b', '--build',
                        type=str,
                        dest="command",
                        default=argparse.SUPPRESS,
                        required=True,
                        help="The build command to execute. Build commands "
                             "can be simple calls to 'g++' or 'clang++' or "
                             "'make', but a more complex command, or the call "
                             "of a custom script file is also supported.")

    parser.add_argument('-k', '--keep-link',
                        dest="keep_link",
                        default=argparse.SUPPRESS,
                        action="store_true",
                        help="If this flag is given then the output log file "
                             "will contain the linking build actions too.")

    parser.add_argument('-q', '--quiet',
                        dest="quiet",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Do not print the output of the build tool into "
                             "the output of this command.")

    parser.add_argument('--verbose',
                        type=str,
                        dest='verbose',
                        choices=logger.CMDLINE_LOG_LEVELS,
                        default=argparse.SUPPRESS,
                        help="Set verbosity level. If the value is 'debug' or "
                             "'debug_analyzer' it will create a "
                             "'codechecker.logger.debug' debug log file "
                             "beside the given output file. It will contain "
                             "debug information of compilation database "
                             "generation. You can override the location of "
                             "this file if you set the 'CC_LOGGER_DEBUG_FILE' "
                             "environment variable to a different file path.")

    parser.set_defaults(func=main)


def main(args):
    """
    Generates a build log by running the original build command.
    No analysis is done.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    args.logfile = os.path.realpath(args.logfile)

    # It is possible that the log file will not be created or it will be empty
    # for example when the build command is an empty string or when there is no
    # compiler command to log. For this reason we will create this log file if
    # it does not exist and we will insert an empty array to it, so it will be
    # a valid json file.
    with open(args.logfile, 'w',
              encoding="utf-8", errors="ignore") as logfile:
        logfile.write("[\n]")

    context = analyzer_context.get_context()
    verbose = args.verbose if 'verbose' in args else None

    build_manager.perform_build_command(args.logfile,
                                        args.command,
                                        context,
                                        'keep_link' in args,
                                        silent='quiet' in args,
                                        verbose=verbose)
