# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handler for the subcommand that is used to start and manage CodeChecker
servers, which are used to query analysis report information.
"""

import argparse
import errno
import json
import os
import socket
import sys

from libcodechecker import generic_package_context
from libcodechecker import generic_package_suppress_handler
from libcodechecker import host_check
from libcodechecker import output_formatters
from libcodechecker import session_manager
from libcodechecker import util
from libcodechecker.analyze import analyzer_env
from libcodechecker.database_handler import SQLServer
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory
from libcodechecker.server import client_db_access_server
from libcodechecker.server import instance_manager

LOG = LoggerFactory.get_new_logger('SERVER')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker server',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "The CodeChecker Web server is used to handle the "
                       "storage and navigation of analysis results. A "
                       "started server can be connected to via a Web "
                       "browser, or by using the 'CodeChecker cmd' "
                       "command-line client.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Start and manage the CodeChecker Web server."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    # TODO: --workspace is an outdated concept in 'store'. Later on,
    # it shall be deprecated, as changes to db_handler commence.
    parser.add_argument('-w', '--workspace',
                        type=str,
                        dest="workspace",
                        default=util.get_default_workspace(),
                        required=False,
                        help="Directory where CodeChecker can store analysis "
                             "result related data, such as the database. "
                             "(Cannot be specified at the same time with "
                             "'--sqlite' or '--config-directory'.)")

    parser.add_argument('-f', '--config-directory',
                        type=str,
                        dest="config_directory",
                        default=util.get_default_workspace(),
                        required=False,
                        help="Directory where CodeChecker server should read "
                             "server-specific configuration (such as "
                             "authentication settings) from.")

    parser.add_argument('--host',
                        type=str,
                        dest="listen_address",
                        default="localhost",
                        required=False,
                        help="The IP address or hostname of the server on "
                             "which it should listen for connections.")

    # TODO: -v/--view-port is too verbose. The server's -p/--port is used
    # symmetrically in 'CodeChecker cmd' anyways.
    parser.add_argument('-v', '--view-port',  # TODO: <- Deprecate and remove.
                        '-p', '--port',
                        type=int,
                        dest="view_port",
                        metavar='PORT',
                        default=8001,
                        required=False,
                        help="The port which will be used as listen port for "
                             "the server.")

    # TODO: This should be removed later on, in favour of --host.
    parser.add_argument('--not-host-only',
                        dest="not_host_only",
                        action="store_true",
                        required=False,
                        help="If specified, storing and viewing the results "
                             "will be possible not only by browsers and "
                             "clients running locally, but to everyone, who "
                             "can access the server over the Internet. "
                             "(Equivalent to specifying '--host \"\"'.)")

    # TODO: Refactor the tests so that these arguments can be eliminated.
    # These values have absolutely no use outside what the automated tests
    # specify.
    checksrv = parser.add_argument_group(
        "analysis result storage server",
        "(These options have no actual use apart from an internal usage in "
        "the automated testing of CodeChecker features.)")

    checksrv.add_argument('--check-address',
                          type=str,
                          dest="check_address",
                          default="localhost",
                          required=False,
                          help="Set on which IP address or hostname the "
                               "analysis result server should listen.")

    checksrv.add_argument('--check-port',
                          type=int,
                          dest="check_port",
                          default=argparse.SUPPRESS,
                          required=None,
                          help="Also start an analysis result storage server "
                               "alongside the \"viewer\". This server could "
                               "be used by remote clients to store new "
                               "analysis results to the database the viewer "
                               "server is using. Set on which port the "
                               "analysis result server should listen.")

    # TODO: Other commands using suppress files no longer use -u as an
    # opt-string in favour of the more explicit --suppress.
    parser.add_argument('-u', '--suppress',
                        type=str,
                        dest="suppress",
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Path of the suppress file to use. The suppress "
                             "file is used to store which analysis results "
                             "are marked 'suppressed', which is a distinct "
                             "category on the result viewing interface. "
                             "NOTE: The suppress file relies on the "
                             "\"bug identifier\" generated by the analyzers "
                             "which is experimental, take care when relying "
                             "on it.")

    dbmodes = parser.add_argument_group("database arguments")

    dbmodes = dbmodes.add_mutually_exclusive_group(required=False)

    dbmodes.add_argument('--sqlite',
                         type=str,
                         dest="sqlite",
                         metavar='SQLITE_FILE',
                         default=os.path.join(
                             util.get_default_workspace(),
                             "codechecker.sqlite"),
                         required=False,
                         help="Path of the SQLite database file to use.")

    dbmodes.add_argument('--postgresql',
                         dest="postgresql",
                         action='store_true',
                         required=False,
                         default=argparse.SUPPRESS,
                         help="Specifies that a PostgreSQL database is to be "
                              "used instead of SQLite. See the \"PostgreSQL "
                              "arguments\" section on how to configure the "
                              "database connection.")

    pgsql = parser.add_argument_group("PostgreSQL arguments",
                                      "Values of these arguments are ignored, "
                                      "unless '--postgresql' is specified!")

    # WARNING: '--dbaddress' default value influences workspace creation
    # in SQLite.
    # TODO: --dbSOMETHING arguments are kept to not break interface from
    # old command. Database using commands such as "CodeChecker store" no
    # longer supports these --- it would be ideal to break and remove args
    # with this style and only keep --db-SOMETHING.
    pgsql.add_argument('--dbaddress', '--db-host',
                       type=str,
                       dest="dbaddress",
                       default="localhost",
                       required=False,
                       help="Database server address.")

    pgsql.add_argument('--dbport', '--db-port',
                       type=int,
                       dest="dbport",
                       default=5432,
                       required=False,
                       help="Database server port.")

    pgsql.add_argument('--dbusername', '--db-username',
                       type=str,
                       dest="dbusername",
                       default='codechecker',
                       required=False,
                       help="Username to use for connection.")

    pgsql.add_argument('--dbname', '--db-name',
                       type=str,
                       dest="dbname",
                       default="codechecker",
                       required=False,
                       help="Name of the database to use.")

    instance_mgmnt = parser.add_argument_group("running server management")

    instance_mgmnt = instance_mgmnt. \
        add_mutually_exclusive_group(required=False)

    instance_mgmnt.add_argument('-l', '--list',
                                dest="list",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="List the servers that has been started "
                                     "by you.")

    # TODO: '-s' was removed from 'quickcheck', it shouldn't be here either?
    instance_mgmnt.add_argument('-s', '--stop',
                                dest="stop",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Stops the server associated with "
                                     "the given view-port and workspace.")

    instance_mgmnt.add_argument('--stop-all',
                                dest="stop_all",
                                action='store_true',
                                default=argparse.SUPPRESS,
                                required=False,
                                help="Stops all of your running CodeChecker "
                                     "server instances.")

    add_verbose_arguments(parser)

    def __handle(args):
        """Custom handler for 'server' so custom error messages can be
        printed without having to capture 'parser' in main."""

        def arg_match(options):
            """Checks and selects the option string specified in 'options'
            that are present in the invocation argv."""
            matched_args = []
            for option in options:
                if any([arg if option.startswith(arg) else None
                        for arg in sys.argv[1:]]):
                    matched_args.append(option)
                    continue

            return matched_args

        # See if there is a "PostgreSQL argument" specified in the invocation
        # without '--postgresql' being there. There is no way to distinguish
        # a default argument and a deliberately specified argument without
        # inspecting sys.argv.
        options = ['--dbaddress', '--dbport', '--dbusername', '--dbname',
                   '--db-host', '--db-port', '--db-username', '--db-name']
        psql_args_matching = arg_match(options)
        if any(psql_args_matching) and\
                'postgresql' not in args:
            first_matching_arg = next(iter([match for match
                                            in psql_args_matching]))
            parser.error("argument {0}: not allowed without "
                         "argument --postgresql".format(first_matching_arg))
            # parser.error() terminates with return code 2.

        # --not-host-only is a "shortcut", actually a to-be-deprecated
        # call which means '--host ""'.
        # TODO: Actually deprecate --not-host-only later on.
        options = ['--not-host-only', '--host']
        if set(arg_match(options)) == set(options):
            parser.error("argument --not-host-only: not allowed with "
                         "argument --host, as it is a shortcut to --host "
                         "\"\"")
        else:
            # Apply the shortcut.
            if len(arg_match(['--not-host-only'])) > 0:
                args.listen_address = ""  # listen on every interface

            # --not-host-only is just a shortcut optstring, no actual use
            # is intended later on.
            delattr(args, 'not_host_only')

        # --workspace and --sqlite cannot be specified either, as
        # both point to a database location.
        options = ['--sqlite', '--workspace']
        options_short = ['--sqlite', '-w']
        if set(arg_match(options)) == set(options) or \
                set(arg_match(options_short)) == set(options_short):
            parser.error("argument --sqlite: not allowed with "
                         "argument --workspace")

        # --workspace and --config-directory also aren't allowed together now,
        # the latter one is expected to replace the earlier.
        options = ['--config-directory', '--workspace']
        options_short = ['--config-directory', '-w']
        if set(arg_match(options)) == set(options) or \
                set(arg_match(options_short)) == set(options_short):
            parser.error("argument --config-directory: not allowed with "
                         "argument --workspace")

        # If workspace is specified, sqlite is workspace/codechecker.sqlite
        # and config_directory is the workspace directory.
        if len(arg_match(['--workspace', '-w'])) > 0:
            args.config_directory = args.workspace
            args.sqlite = os.path.join(args.workspace,
                                       'codechecker.sqlite')

        # Workspace should not exist as a Namespace key.
        # TODO: Keep workspace setting until the separate PostgreSQL
        # initialization is done, not the current auto setup.
        # delattr(args, 'workspace')

        if 'postgresql' not in args:
            # Later called database modules need the argument to be actually
            # present, even though the default is suppressed in the optstring.
            setattr(args, 'postgresql', False)
        else:
            # If --postgresql is given, --sqlite is useless.
            delattr(args, 'sqlite')

        # If everything is fine, do call the handler for the subcommand.
        main(args)

    parser.set_defaults(func=__handle)


def __instance_management(args):
    """Handles the instance-manager commands --list/--stop/--stop-all."""

    # TODO: The server stopping and listing must be revised on its invocation
    # once "workspace", as a concept, is removed.
    # QUESTION: What is the bestest way here to identify a server for the user?
    if 'list' in args:
        instances = instance_manager.list()

        instances_on_multiple_hosts = any(True for inst in instances
                                          if inst['hostname'] !=
                                          socket.gethostname())
        if not instances_on_multiple_hosts:
            head = ['Workspace', 'View port']
        else:
            head = ['Workspace', 'Computer host', 'View port']

        rows = []
        for instance in instance_manager.list():
            if not instances_on_multiple_hosts:
                rows.append((instance['workspace'], str(instance['port'])))
            else:
                rows.append((instance['workspace'],
                             instance['hostname']
                             if instance['hostname'] != socket.gethostname()
                             else '',
                             str(instance['port'])))

        print("Your running CodeChecker servers:")
        print(output_formatters.twodim_to_str('table', head, rows))
    elif 'stop' in args or 'stop_all' in args:
        for i in instance_manager.list():
            # A STOP only stops the server associated with the given workspace
            # and view-port.
            if i['hostname'] != socket.gethostname() or (
                    args.stop and not (i['port'] == args.view_port and
                                       os.path.abspath(
                                       i['workspace']) ==
                                       os.path.abspath(
                                           args.config_directory))):
                continue

            try:
                util.kill_process_tree(i['pid'])
                LOG.info("Stopped CodeChecker server running on port {0} "
                         "in workspace {1} (PID: {2})".
                         format(i['port'], i['workspace'], i['pid']))
            except:
                # Let the exception come out if the commands fail
                LOG.error("Couldn't stop process PID #" + str(i['pid']))
                raise


def main(args):
    """
    Start or manage a CodeChecker report server.
    """

    if 'list' in args or 'stop' in args or 'stop_all' in args:
        __instance_management(args)
        sys.exit(0)

    # Actual server starting from this point.
    if not host_check.check_zlib():
        raise Exception("zlib is not available on the system!")

    # WARNING
    # In case of SQLite args.dbaddress default value is used
    # for which the is_localhost should return true.
    if util.is_localhost(args.dbaddress) and \
            not os.path.exists(args.config_directory):
        os.makedirs(args.config_directory)

    # Make sure the SQLite file can be created if it not exists.
    if 'sqlite' in args and \
            not os.path.isdir(os.path.dirname(args.sqlite)):
        os.makedirs(os.path.dirname(args.sqlite))

    if 'suppress' not in args:
        LOG.warning("No suppress file was given, suppressed results will "
                    "be only stored in the database.")
        suppress_handler = generic_package_suppress_handler. \
            GenericSuppressHandler(None, False)
    else:
        if not os.path.exists(args.suppress):
            LOG.error("Suppress file " + args.suppress + " not found!")
            sys.exit(1)

        LOG.debug("Using suppress file: " +
                  str(args.suppress))
        suppress_handler = generic_package_suppress_handler. \
            GenericSuppressHandler(args.suppress, True)

    context = generic_package_context.get_context()
    context.codechecker_workspace = args.config_directory
    session_manager.SessionManager.CodeChecker_Workspace = \
        args.config_directory
    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.migration_root,
                                             check_env)

    LOG.debug("Starting database server.")
    sql_server.start(context.db_version_info, wait_for_start=True,
                     init=True)

    # Start database viewer.
    db_connection_string = sql_server.get_connection_string()

    checker_md_docs = os.path.join(context.doc_root, 'checker_md_docs')
    checker_md_docs_map = os.path.join(checker_md_docs,
                                       'checker_doc_map.json')
    with open(checker_md_docs_map, 'r') as dFile:
        checker_md_docs_map = json.load(dFile)

    package_data = {'www_root': context.www_root,
                    'doc_root': context.doc_root,
                    'checker_md_docs': checker_md_docs,
                    'checker_md_docs_map': checker_md_docs_map,
                    'version': context.package_git_tag}

    try:
        client_db_access_server.start_server(package_data,
                                             args.view_port,
                                             db_connection_string,
                                             suppress_handler,
                                             args.listen_address,
                                             context)
    except socket.error as err:
        if err.errno == errno.EADDRINUSE:
            LOG.error("Server can't be started, maybe the given port number "
                      "({}) is already used. Check the connection "
                      "parameters.".format(args.view_port))
            sys.exit(1)
        else:
            raise
