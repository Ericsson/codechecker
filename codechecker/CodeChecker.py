# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

'''
main codechecker script

'''
import os
import sys
import signal
import argparse

import shared

from codechecker_lib import logger
from codechecker_lib import arg_handler

from cmdline_client import cmd_line_client

LOG = logger.get_new_logger('MAIN')


# ------------------------------------------------------------------------------
class OrderedCheckersAction(argparse.Action):
    '''
    Action to store enabled and disabled checkers
    and keep ordering from command line
    '''
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(OrderedCheckersAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):
        if 'ordered_checker_args' not in namespace:
            setattr(namespace, 'ordered_checker_args', [])
        previous_values = namespace.ordered_checker_args
        if self.dest == 'enable':
            previous_values.append((value, True))
        else:
            previous_values.append((value, False))
        setattr(namespace, 'ordered_checker_args', previous_values)

# ------------------------------------------------------------------------------
class DeprecatedOptionAction(argparse.Action):
    '''
    Deprecated argument action
    '''
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
        super(DeprecatedOptionAction, self).__init__(option_strings,
                                                     dest,
                                                     nargs='?',
                                                     const='deprecated_option',
                                                     default=None,
                                                     type=None,
                                                     choices=None,
                                                     required=False,
                                                     help='DEPRECATED argument!',
                                                     metavar='DEPRECATED')

    def __call__(self, parser, namespace, value=None, option_string=None):
        LOG.warning("Deprecated command line option in use: '" + option_string + "'")


def add_database_arguments(parser):
    '''Helper method for adding database arguments to an argument parser.'''

    parser.add_argument('--sqlite', action=DeprecatedOptionAction)
    parser.add_argument('--postgresql', dest="postgresql",
                        action='store_true', required=False,
                        help='Use PostgreSQL database.')
    parser.add_argument('--dbport', type=int, dest="dbport",
                        default=8764, required=False,
                        help='Postgres server port.')
    parser.add_argument('--dbaddress', type=str, dest="dbaddress",
                        default="localhost", required=False,
                        help='Postgres database server address')
    parser.add_argument('--dbname', type=str, dest="dbname",
                        default="codechecker", required=False,
                        help='Name of the database.')
    parser.add_argument('--dbusername', type=str, dest="dbusername",
                        default='codechecker', required=False,
                        help='Database user name.')

# ------------------------------------------------------------------------------
def main():
    '''
    codechecker main command line
    '''

    def signal_handler(sig, frame):
        '''
        Without this handler the postgreSql
        server does not terminated at signal
        '''
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description='''Run the codechecker script.\n ''')

        subparsers = parser.add_subparsers(help='commands')

        # --------------------------------------
        # check commands
        check_parser = subparsers.add_parser('check',
                                             help='Run CodeChecker for a project.')
        check_parser.add_argument('-w', '--workspace', type=str,
                                  dest="workspace", required=True,
                                  help='Directory where the codechecker can \
                                  store analysis related data.')
        check_parser.add_argument('-n', '--name', type=str,
                                  dest="name", required=True,
                                  help='Name of the project.')

        checkgroup = check_parser.add_mutually_exclusive_group(required=True)
        checkgroup.add_argument('-b', '--build', type=str, dest="command",
                                required=False, help='Build command.')
        checkgroup.add_argument('-l', '--log', type=str, dest="logfile",
                                required=False,
                                help='Path to the log file which is created \
                                during the build.')

        check_parser.add_argument('-j', '--jobs', type=int, dest="jobs",
                                  default=1, required=False, help='Number of jobs.')
        check_parser.add_argument('-f', '--config', type=str, dest="configfile",
                                  required=False, help='Config file for the checkers.')
        check_parser.add_argument('-s', '--skip', type=str, dest="skipfile",
                                  required=False, help='Path to skip file.')
        check_parser.add_argument('-u', '--suppress', type=str, dest="suppress",
                                  required=False, help='Path to suppress file.')
        check_parser.add_argument('-e', '--enable', default=[],
                                  action=OrderedCheckersAction,
                                  help='Enable checker.')
        check_parser.add_argument('-d', '--disable', default=[],
                                  action=OrderedCheckersAction,
                                  help='Disable checker.')
        check_parser.add_argument('-c', '--clean', action=DeprecatedOptionAction)
        check_parser.add_argument('--keep-tmp', action="store_true",
                                  dest="keep_tmp", required=False,
                                  help='Keep temporary report files \
                                  after sending data to database storage server.')
        check_parser.add_argument('--update', action="store_true",
                                  dest="update", default=False, required=False,
                                  help='Incremental parsing, \
                                  update the results of a previous run.')
        add_database_arguments(check_parser)
        check_parser.set_defaults(func=arg_handler.handle_check)

        # --------------------------------------
        # quickcheck commands
        qcheck_parser = subparsers.add_parser('quickcheck',
                                              help='Run CodeChecker for a \
                                                    project without database.')
        qcheckgroup = qcheck_parser.add_mutually_exclusive_group(required=True)
        qcheckgroup.add_argument('-b', '--build', type=str, dest="command",
                                 required=False, help='Build command.')
        qcheckgroup.add_argument('-l', '--log', type=str, dest="logfile",
                                 required=False,
                                 help='Path to the log file which is created \
                                       during the build.')
        qcheck_parser.add_argument('-e', '--enable', default=[],
                                   action=OrderedCheckersAction,
                                   help='Enable checker.')
        qcheck_parser.add_argument('-d', '--disable', default=[],
                                   action=OrderedCheckersAction,
                                   help='Disable checker.')
        qcheck_parser.add_argument('-s', '--steps', action="store_true",
                                   dest="print_steps", help='Print steps.')
        qcheck_parser.set_defaults(func=arg_handler.handle_quickcheck)


        # --------------------------------------
        # log commands
        logging_parser = subparsers.add_parser('log',
                                               help='Build the project and \
                                               create a log file (no checking).')
        logging_parser.add_argument('-o', '--output', type=str, dest="logfile",
                                    required=True, help='Path to the log file.')
        logging_parser.add_argument('-b', '--build', type=str, dest="command",
                                    required=True, help='Build command.')
        logging_parser.set_defaults(func=arg_handler.handle_log)

        # --------------------------------------
        # checkers parser
        checkers_parser = subparsers.add_parser('checkers',
                                                help='List avalaible checkers.')
        checkers_parser.set_defaults(func=arg_handler.handle_list_checkers)

        # --------------------------------------
        # server
        server_parser = subparsers.add_parser('server',
                                              help='Start the codechecker database server.')
        server_parser.add_argument('-w', '--workspace', type=str,
                                   dest="workspace", required=False,
                                   help='Directory where the codechecker \
                                   stored analysis related data \
                                   (automatically created posgtreSql database).')
        server_parser.add_argument('-v', '--view-port', type=int, dest="view_port",
                                   default=11444, required=False,
                                   help='Port used for viewing.')
        server_parser.add_argument('-u', '--suppress', type=str, dest="suppress",
                                   required=False, help='Path to suppress file.')
        server_parser.add_argument('--not-host-only', action="store_true",
                                   dest="not_host_only",
                                   help='Viewing the results is possible not \
                                   only by browsers or clients started locally.')
        server_parser.add_argument('--check-port', type=int, dest="check_port",
                                   default=None, required=False,
                                   help='Port used for checking.')
        server_parser.add_argument('--check-address', type=str,
                                   dest="check_address", default="localhost",
                                   required=False, help='Server address.')
        add_database_arguments(server_parser)
        server_parser.set_defaults(func=arg_handler.handle_server)

        # --------------------------------------
        # cmd_line
        cmd_line_parser = subparsers.add_parser('cmd',
                                                help='Command line client')
        cmd_line_client.register_client_command_line(cmd_line_parser)

        # --------------------------------------
        # debug parser
        debug_parser = subparsers.add_parser('debug',
                                             help='Create debug logs \
                                             for failed buildactions')
        debug_parser.add_argument('-w', '--workspace', type=str,
                                  dest="workspace", required=False,
                                  help='Directory where the codechecker stores \
                                  analysis related data.')
        debug_parser.add_argument('-f', '--force', action="store_true",
                                  dest="force", required=False, default=False,
                                  help='Generate dump for all failed action.')
        add_database_arguments(debug_parser)
        debug_parser.set_defaults(func=arg_handler.handle_debug)

        # --------------------------------------
        # package version info
        version_parser = subparsers.add_parser('version',
                                               help='Print package version information.')
        version_parser.set_defaults(func=arg_handler.handle_version_info)

        args = parser.parse_args()
        args.func(args)

    except KeyboardInterrupt as kb_err:
        LOG.info(str(kb_err))
        LOG.info("Interupted by user...")
        sys.exit(1)

    except shared.ttypes.RequestFailed as thrift_ex:
        LOG.info("Server error.")
        LOG.info("Error code: " + str(thrift_ex.error_code))
        LOG.info("Error message: " + str(thrift_ex.message))
        sys.exit(1)

    # Handle all exception, but print stacktrace. It is needed for atexit.
    # atexit does not work correctly when an unhandled exception occured.
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
