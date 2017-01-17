# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Main CodeChecker script.
"""
from __future__ import print_function

import argparse
from argparse import ArgumentDefaultsHelpFormatter as ADHF
import os
import signal
import sys

import shared

from cmdline_client import cmd_line_client
from codechecker_lib import arg_handler
from codechecker_lib import util
from codechecker_lib import logger
from codechecker_lib.logger import LoggerFactory
from codechecker_lib.analyzers import analyzer_types

LOG = LoggerFactory.get_new_logger('MAIN')

analyzers = ' '.join(list(analyzer_types.supported_analyzers))


class OrderedCheckersAction(argparse.Action):
    """
    Action to store enabled and disabled checkers
    and keep ordering from command line.

    Create separate lists based on the checker names for
    each analyzer.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(OrderedCheckersAction, self).__init__(option_strings, dest,
                                                    **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):

        if 'ordered_checkers' not in namespace:
            namespace.ordered_checkers = []
        ordered_checkers = namespace.ordered_checkers
        ordered_checkers.append((value, self.dest == 'enable'))

        namespace.ordered_checkers = ordered_checkers


# ------------------------------------------------------------------------------
class DeprecatedOptionAction(argparse.Action):
    """
    Deprecated argument action.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(DeprecatedOptionAction, self). \
            __init__(option_strings,
                     dest,
                     nargs='?',
                     const='deprecated_option',
                     default=None,
                     type=None,
                     choices=None,
                     required=False,
                     help="DEPRECATED argument!",
                     metavar='DEPRECATED')

    def __call__(self, parser, namespace, value=None, option_string=None):
        LOG.warning("Deprecated command line option in use: '" +
                    option_string + "'")


def add_database_arguments(parser):
    """ Helper method for adding database arguments to an argument parser. """

    parser.add_argument('--sqlite', action=DeprecatedOptionAction)
    parser.add_argument('--postgresql', dest="postgresql",
                        action='store_true', required=False,
                        help='Use PostgreSQL database.')
    parser.add_argument('--dbport', type=int, dest="dbport",
                        default=5432, required=False,
                        help='Postgres server port.')
    # WARNING dbaddress default value influences workspace creation (SQLite).
    parser.add_argument('--dbaddress', type=str, dest="dbaddress",
                        default="localhost", required=False,
                        help='Postgres database server address.')
    parser.add_argument('--dbname', type=str, dest="dbname",
                        default="codechecker", required=False,
                        help='Name of the database.')
    parser.add_argument('--dbusername', type=str, dest="dbusername",
                        default='codechecker', required=False,
                        help='Database user name.')


def add_analyzer_arguments(parser):
    """
    Analyzer related arguments.
    """
    parser.add_argument('-e', '--enable',
                        default=argparse.SUPPRESS,
                        action=OrderedCheckersAction,
                        help='Enable checker.')
    parser.add_argument('-d', '--disable',
                        default=argparse.SUPPRESS,
                        action=OrderedCheckersAction,
                        help='Disable checker.')
    parser.add_argument('--keep-tmp', action="store_true",
                        dest="keep_tmp", required=False,
                        help="Keep temporary report files"
                        "generated during the analysis.")

    parser.add_argument('--analyzers', nargs='+',
                        dest="analyzers", required=False,
                        default=[analyzer_types.CLANG_SA,
                                 analyzer_types.CLANG_TIDY],
                        help="Select which analyzer should be enabled.\n"
                        "Currently supported analyzers are: " +
                        analyzers + "\ne.g. '--analyzers " + analyzers + "'")

    parser.add_argument('--saargs', dest="clangsa_args_cfg_file",
                        required=False, default=argparse.SUPPRESS,
                        help="File with arguments which will be forwarded"
                        "directly to the Clang static analyzer"
                        "without modification.")

    parser.add_argument('--tidyargs', dest="tidy_args_cfg_file",
                        required=False, default=argparse.SUPPRESS,
                        help="File with arguments which will be forwarded"
                        "directly to the Clang tidy analyzer"
                        "without modification.")


def main():
    """
    CodeChecker main command line.
    """

    def signal_handler(sig, frame):
        """
        Without this handler the PostgreSQL
        server does not terminate at signal.
        """
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        parser = argparse.ArgumentParser(
            prog='CodeChecker',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description='''
Run the CodeChecker source analyzer framework.
See the subcommands for specific features.''',
            epilog='''
Example usage:
--------------
Analyzing a project with default settings:
CodeChecker check -b "cd ~/myproject && make" -n myproject

Start the viewer to see the results:
CodeChecker server

See the results in a web browser: localhost:8001
See results in  the command line: CodeChecker cmd results -p 8001 -n myproject

To analyze a small project quickcheck feature can be used.
The results will be printed only to the standard output.
(No database will be used)

CodeChecker quickcheck -b "cd ~/myproject && make"
''')

        subparsers = parser.add_subparsers(help='commands')

        workspace_help_msg = 'Directory where the CodeChecker can' \
            ' store analysis related data.'

        name_help_msg = 'Name of the analysis.'

        jobs_help_msg = 'Number of jobs.' \
            'Start multiple processes for faster analysis.'

        log_argument_help_msg = "Path to the log file which is created "
        "during the build. \nIf there is an already generated log file "
        "with the compilation commands\ngenerated by 'CodeChecker log' or "
        "'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS' \n CodeChecker check can "
        "use it for the analysis in that case running the original build "
        "will \nbe left out from the analysis process (no log is needed)."

        suppress_help_msg = "Path to suppress file.\nSuppress file can be used"
        "to suppress analysis results during the analysis.\nIt is based on the"
        "bug identifier generated by the compiler which is experimental.\nDo"
        "not depend too much on this file because identifier or file format "
        "can be changed.\nFor other in source suppress features see the user"
        "guide."

        # --------------------------------------
        # check commands
        check_parser = subparsers.add_parser('check',
                                             formatter_class=ADHF,
                                             help=''' \
Run the supported source code analyzers on a project.''')

        check_parser.add_argument('-w', '--workspace', type=str,
                                  default=util.get_default_workspace(),
                                  dest="workspace",
                                  help=workspace_help_msg)

        check_parser.add_argument('-n', '--name', type=str,
                                  dest="name", required=True,
                                  default=argparse.SUPPRESS,
                                  help=name_help_msg)

        checkgroup = check_parser.add_mutually_exclusive_group(required=True)

        checkgroup.add_argument('-b', '--build', type=str, dest="command",
                                default=argparse.SUPPRESS,
                                required=False, help='''\
Build command which is used to build the project.''')

        checkgroup.add_argument('-l', '--log', type=str, dest="logfile",
                                default=argparse.SUPPRESS,
                                required=False,
                                help=log_argument_help_msg)

        check_parser.add_argument('-j', '--jobs', type=int, dest="jobs",
                                  default=1, required=False,
                                  help=jobs_help_msg)

        check_parser.add_argument('-u', '--suppress', type=str,
                                  dest="suppress",
                                  default=argparse.SUPPRESS,
                                  required=False,
                                  help=suppress_help_msg)
        check_parser.add_argument('-c', '--clean',
                                  default=argparse.SUPPRESS,
                                  action=DeprecatedOptionAction)

        check_parser.add_argument('--update', action=DeprecatedOptionAction,
                                  dest="update", default=False, required=False,
                                  help="Incremental parsing, update the "
                                       "results of a previous run. "
                                       "Only the files changed since the last "
                                       "build will be reanalyzed. Depends on"
                                       " the build system.")

        check_parser.add_argument('--force', action="store_true",
                                  dest="force", default=False, required=False,
                                  help="Delete analysis results form the "
                                       "database if a run with the "
                                       "given name already exists.")

        check_parser.add_argument('-s', '--skip', type=str, dest="skipfile",
                                  default=argparse.SUPPRESS,
                                  required=False, help='Path to skip file.')

        check_parser.add_argument('--quiet-build',
                                  action='store_true',
                                  default=False,
                                  required=False,
                                  help='Do not print out the output of the '
                                       'original build.')

        check_parser.add_argument('--add-compiler-defaults',
                                  action='store_true',
                                  default=False,
                                  required=False,
                                  help='Fetch built in compiler include'
                                       'paths and defines '
                                       'and pass them to Clang. This is'
                                       'useful when you do cross-compilation.')

        add_analyzer_arguments(check_parser)
        add_database_arguments(check_parser)
        logger.add_verbose_arguments(check_parser)
        check_parser.set_defaults(func=arg_handler.handle_check)

        # --------------------------------------
        # QuickCheck commands.
        qcheck_parser = subparsers.add_parser('quickcheck',
                                              formatter_class=ADHF,
                                              help='Run CodeChecker for a'
                                                   'project without database.')

        qcheckgroup = qcheck_parser.add_mutually_exclusive_group(required=True)

        qcheckgroup.add_argument('-b', '--build', type=str, dest="command",
                                 default=argparse.SUPPRESS,
                                 required=False, help='Build command.')

        qcheckgroup.add_argument('-l', '--log', type=str, dest="logfile",
                                 required=False,
                                 default=argparse.SUPPRESS,
                                 help=log_argument_help_msg)

        qcheck_parser.add_argument('-s', '--steps', action="store_true",
                                   dest="print_steps", help='Print steps.')

        qcheck_parser.add_argument('--quiet-build',
                                   action='store_true',
                                   default=False,
                                   required=False,
                                   help='Do not print out the output of the '
                                        'original build.')
        qcheck_parser.add_argument('-i', '--skip', type=str, dest="skipfile",
                                   default=argparse.SUPPRESS,
                                   required=False, help='Path to skip file.')
        qcheck_parser.add_argument('-j', '--jobs', type=int, dest="jobs",
                                   default=1, required=False,
                                   help=jobs_help_msg)
        qcheck_parser.add_argument('-u', '--suppress', type=str,
                                   dest="suppress",
                                   default=argparse.SUPPRESS,
                                   required=False,
                                   help=suppress_help_msg)
        qcheck_parser.add_argument('--add-compiler-defaults',
                                   action='store_true',
                                   default=False,
                                   required=False,
                                   help='Fetch built in compiler include paths'
                                        ' and defines and pass them to Clang.'
                                        'This is useful when you'
                                        'do cross-compilation.')
        add_analyzer_arguments(qcheck_parser)
        logger.add_verbose_arguments(qcheck_parser)
        qcheck_parser.set_defaults(func=arg_handler.handle_quickcheck)

        # --------------------------------------
        # Log commands.
        logging_p = subparsers.add_parser('log',
                                          formatter_class=ADHF,
                                          help='Runs the given build '
                                               'command. During the '
                                               'build the compilation '
                                               'commands are collected '
                                               'and stored into a '
                                               'compilation command '
                                               'json file '
                                               '(no analysis is done '
                                               'during the build).')

        logging_p.add_argument('-o', '--output', type=str, dest="logfile",
                               default=argparse.SUPPRESS,
                               required=True,
                               help='Path to the log file.')

        logging_p.add_argument('-b', '--build', type=str, dest="command",
                               default=argparse.SUPPRESS,
                               required=True, help='Build command.')

        logger.add_verbose_arguments(logging_p)
        logging_p.set_defaults(func=arg_handler.handle_log)

        # --------------------------------------
        # Checkers parser.
        checker_p = subparsers.add_parser('checkers',
                                          formatter_class=ADHF,
                                          help='List the available checkers '
                                               'for the supported analyzers '
                                               'and show their default status '
                                               '(+ for being enabled, '
                                               '- for being disabled by '
                                               'default).')

        checker_p.add_argument('--analyzers', nargs='+',
                               dest="analyzers", required=False,
                               help='Select which analyzer checkers '
                               'should be listed.\nCurrently supported '
                               'analyzers:\n' + analyzers)

        logger.add_verbose_arguments(checker_p)
        checker_p.set_defaults(func=arg_handler.handle_list_checkers)

        # --------------------------------------
        # Server.
        server_parser = subparsers.add_parser('server',
                                              formatter_class=ADHF,
                                              help='Start the codechecker '
                                                   'web server.')
        server_parser.add_argument('-w', '--workspace', type=str,
                                   dest="workspace",
                                   default=util.get_default_workspace(),
                                   help=workspace_help_msg)

        server_parser.add_argument('-v', '--view-port', type=int,
                                   dest="view_port",
                                   default=8001, required=False,
                                   help='Port used for viewing.')

        server_parser.add_argument('-u', '--suppress', type=str,
                                   dest="suppress",
                                   required=False,
                                   help='Path to suppress file.')

        server_parser.add_argument('--not-host-only', action="store_true",
                                   dest="not_host_only",
                                   help='Viewing the results is possible not'
                                        'only by browsers or clients'
                                        ' started locally.')

        server_parser.add_argument('--check-port', type=int, dest="check_port",
                                   default=None, required=False,
                                   help='Port used for checking.')

        server_parser.add_argument('--check-address', type=str,
                                   dest="check_address", default="localhost",
                                   required=False, help='Server address.')

        add_database_arguments(server_parser)
        logger.add_verbose_arguments(server_parser)
        server_parser.set_defaults(func=arg_handler.handle_server)

        # --------------------------------------
        # Cmd_line.
        cmd_line_parser = subparsers.add_parser('cmd',
                                                help='Command line client')
        cmd_line_client.register_client_command_line(cmd_line_parser)

        # --------------------------------------
        # Debug parser.
        debug_parser = subparsers.add_parser('debug',
                                             formatter_class=ADHF,
                                             help='Generate gdb debug dump '
                                                  'files for all the failed '
                                                  'compilation commands in '
                                                  'the last analyzer run.\n'
                                                  'Requires a database with '
                                                  'the failed compilation '
                                                  'commands.')

        debug_parser.add_argument('-w', '--workspace', type=str,
                                  dest="workspace",
                                  default=util.get_default_workspace(),
                                  help=workspace_help_msg)

        debug_parser.add_argument('-f', '--force', action="store_true",
                                  dest="force", required=False, default=False,
                                  help='Overwrite already generated files.')

        add_database_arguments(debug_parser)
        logger.add_verbose_arguments(debug_parser)
        debug_parser.set_defaults(func=arg_handler.handle_debug)

        # --------------------------------------
        # Plist parser.
        plist_parser = subparsers.add_parser('plist',
                                             formatter_class=ADHF,
                                             help='Parse plist files in '
                                                  'the given directory and '
                                                  'store them to the database '
                                                  'or print to the standard '
                                                  'output.')

        plist_parser.add_argument('-w', '--workspace', type=str,
                                  dest="workspace",
                                  default=util.get_default_workspace(),
                                  help=workspace_help_msg)

        plist_parser.add_argument('-n', '--name', type=str,
                                  dest="name", required=True,
                                  default=argparse.SUPPRESS,
                                  help=name_help_msg)

        plist_parser.add_argument('-d', '--directory', type=str,
                                  dest="directory", required=True,
                                  help='Path of a directory containing plist '
                                  ' files to parse.')

        plist_parser.add_argument('-j', '--jobs', type=int, dest="jobs",
                                  default=1, required=False,
                                  help=jobs_help_msg)

        plist_parser.add_argument('-s', '--steps', action="store_true",
                                  dest="print_steps", help='Print steps.')

        plist_parser.add_argument('--stdout', action="store_true",
                                  dest="stdout",
                                  required=False, default=False,
                                  help='Print results to stdout instead of '
                                       'storing to the database.')

        plist_parser.add_argument('--force', action="store_true",
                                  dest="force", default=False, required=False,
                                  help='Delete analysis results form the '
                                       'database if a run with the given '
                                       'name already exists.')

        add_database_arguments(plist_parser)
        logger.add_verbose_arguments(plist_parser)
        plist_parser.set_defaults(func=arg_handler.handle_plist)

        # --------------------------------------
        # Package version info.
        version_parser = subparsers.add_parser('version',
                                               help='Print package version '
                                                    'information.')
        version_parser.set_defaults(func=arg_handler.handle_version_info)
        logger.add_verbose_arguments(version_parser)

        args = parser.parse_args()
        LoggerFactory.set_log_level(args.verbose)
        args.func(args)

    except KeyboardInterrupt as kb_err:
        LOG.info(str(kb_err))
        LOG.info("Interrupted by user...")
        sys.exit(1)

    except shared.ttypes.RequestFailed as thrift_ex:
        LOG.info("Server error.")
        LOG.info("Error code: " + str(thrift_ex.error_code))
        LOG.info("Error message: " + str(thrift_ex.message))
        sys.exit(1)

    # Handle all exception, but print stacktrace. It is needed for atexit.
    # atexit does not work correctly when an unhandled exception occurred.
    # So in this case, the servers left running when the script exited.
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    LOG.debug(sys.path)
    LOG.debug(sys.version)
    LOG.debug(sys.executable)
    LOG.debug(os.environ.get('LD_LIBRARY_PATH'))

    main()
