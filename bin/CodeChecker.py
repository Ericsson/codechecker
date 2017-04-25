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
import imp
import json
import os
import signal
import sys

import shared

from libcodechecker import arg_handler
from libcodechecker import logger
from libcodechecker.logger import LoggerFactory
from libcodechecker import util
from libcodechecker.cmd import cmd_line_client
from libcodechecker.analyze.analyzers import analyzer_types

LOG = LoggerFactory.get_new_logger('MAIN')

analyzers = ' '.join(list(analyzer_types.supported_analyzers))


# -----------------------------------------------------------------------------
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


def main(subcommands=None):
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

        # TODO: Delete these once a later version rolls.
        old_subcommands = []

        def _warn_deprecated_command(cmd_name):
            # Write to stderr so the output is not captured by pipes, e.g.
            # with the "checkers" command, the "-" in the new command's name
            # would mess up pipe usage.
            err_msg = "[WARNING] The called command 'CodeChecker {0}' is " \
                      "DEPRECATED since version A.B. A new version is "    \
                      "available as 'codechecker-{0}'.\nThe DEPRECATED "   \
                      "command will be REPLACED when version X.Y is "      \
                      "released.\nPlease see 'codechecker-{0} --help' on " \
                      "details how to run the new version.\n".format(cmd_name)

            # This warning is implemented for showing later on, once old
            # behaviour commands are deprecated. We don't warn between 5.8 and
            # 6.0 for now.
            # sys.stderr.write(err_msg)

        workspace_help_msg = 'Directory where the CodeChecker can' \
            ' store analysis related data.'

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
        old_subcommands.append('checkers')

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
                                              help='Start and manage the '
                                                   'CodeChecker web server.')
        old_subcommands.append('server')

        server_parser.add_argument('-w', '--workspace', type=str,
                                   dest="workspace",
                                   default=util.get_default_workspace(),
                                   help=workspace_help_msg)

        server_parser.add_argument('-l', '--list',
                                   action='store_true',
                                   dest="list",
                                   required=False,
                                   help='List servers started by your user.')

        server_parser.add_argument('-s', '--stop',
                                   action='store_true',
                                   dest="stop",
                                   required=False,
                                   help='Stops the server associated with '
                                        'the given view-port and workspace.')

        server_parser.add_argument('--stop-all',
                                   action='store_true',
                                   dest="stop_all",
                                   required=False,
                                   help='Stops all of your running '
                                        'CodeChecker instances.')

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
                                   help='Viewing the results is possible not '
                                        'only by browsers or clients '
                                        'started locally.')

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
        old_subcommands.append('cmd')
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
        old_subcommands.append('debug')

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
        # Package version info.
        version_parser = subparsers.add_parser('version',
                                               help='Print package version '
                                                    'information.')
        old_subcommands.append('version')

        version_parser.set_defaults(func=arg_handler.handle_version_info)
        logger.add_verbose_arguments(version_parser)

        if subcommands:
            # Load the 'libcodechecker' module and acquire its path.
            file, path, descr = imp.find_module("libcodechecker")
            libcc_path = imp.load_module("libcodechecker",
                                         file, path, descr).__path__[0]

            # Try to check if the user has already given us a subcommand to
            # execute. If so, don't load every available parts of CodeChecker
            # to ensure a more optimised run.
            if len(sys.argv) > 1:
                first_command = sys.argv[1]
                if first_command in subcommands:
                    LOG.debug("Supplied an existing, valid subcommand: " +
                              first_command)

                    if 'CC_FROM_LEGACY_INVOKE' not in os.environ:
                        # Consider only the given command as an available one.
                        subcommands = [first_command]
                    else:
                        if first_command in old_subcommands:
                            # Certain commands as of now have a 'new' and an
                            # 'old' invocation and execution. In case of an
                            # 'old' invocation is passed ('CodeChecker
                            # command'), do NOT load the 'new' argument parser
                            # and executed method.
                            #
                            # TODO: Delete this once the new commands are
                            # fleshed out and old are deprecated later on.
                            _warn_deprecated_command(first_command)
                            subcommands = []

            for subcommand in subcommands:
                if 'CC_FROM_LEGACY_INVOKE' in os.environ and \
                        subcommand in old_subcommands:
                    # Make sure 'old' commands have a priority in the listing
                    # when '--help' is queried.
                    continue

                LOG.debug("Creating arg parser for subcommand " + subcommand)

                try:
                    # Even though command verbs and nouns are joined by a
                    # hyphen, the Python files contain underscores.
                    command_file = os.path.join(libcc_path,
                                                subcommand.replace('-', '_') +
                                                ".py")

                    # Load the module's source code, located under
                    # libcodechecker/sub_command.py.
                    # We can't use find_module() and load_module() here as both
                    # a file AND a package exists with the same name, and
                    # find_module() would find
                    # libcodechecker/sub_command/__init__.py first.
                    # Thus, manual source-code reading is required.
                    # NOTE: load_source() loads the compiled .pyc, if such
                    # exists.
                    command_module = imp.load_source(subcommand, command_file)

                    # Now that the module is loaded, construct an
                    # ArgumentParser for it.
                    sc_parser = subparsers.add_parser(
                        subcommand, **command_module.get_argparser_ctor_args())

                    command_module.add_arguments_to_parser(sc_parser)

                except (IOError, ImportError):
                    LOG.warning("Couldn't import module for subcommand '" +
                                subcommand + "'... ignoring.")
                    import traceback
                    traceback.print_exc(file=sys.stdout)

        args = parser.parse_args()
        if 'verbose' in args:
            LoggerFactory.set_log_level(args.verbose)
        args.func(args)

        if 'CC_FROM_LEGACY_INVOKE' in os.environ and \
                first_command and first_command in old_subcommands:
            _warn_deprecated_command(first_command)

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
        sys.exit(1)


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    LOG.debug(sys.path)
    LOG.debug(sys.version)
    LOG.debug(sys.executable)
    LOG.debug(os.environ.get('LD_LIBRARY_PATH'))

    # Load the available CodeChecker subcommands.
    # This list is generated dynamically by scripts/build_package.py, and is
    # always meant to be available alongside the CodeChecker.py.
    commands_cfg = os.path.join(os.path.dirname(__file__), "commands.json")

    with open(commands_cfg) as cfg_file:
        commands = json.load(cfg_file)

    LOG.debug("Available CodeChecker subcommands: ")
    LOG.debug(commands)

    main(commands)
