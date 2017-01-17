# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle command line arguments.
"""
import json
import multiprocessing
import os
import psutil
import socket
import shutil
import sys
import tempfile

from codechecker_lib import analyzer
from codechecker_lib import analyzer_env
from codechecker_lib import build_action
from codechecker_lib import build_manager
from codechecker_lib import client
from codechecker_lib import debug_reporter
from codechecker_lib import generic_package_context
from codechecker_lib import generic_package_suppress_handler
from codechecker_lib import host_check
from codechecker_lib import instance_manager
from codechecker_lib import log_parser
from codechecker_lib import session_manager
from codechecker_lib import util
from codechecker_lib.logger import LoggerFactory
from codechecker_lib.analyzers import analyzer_types
from codechecker_lib.database_handler import SQLServer
from viewer_server import client_db_access_server

LOG = LoggerFactory.get_new_logger('ARG_HANDLER')


def log_startserver_hint(args):
    db_data = ""
    if args.postgresql:
        db_data += " --postgresql" \
                   + " --dbname " + args.dbname \
                   + " --dbport " + str(args.dbport) \
                   + " --dbusername " + args.dbusername

    LOG.info("To view results run:\nCodeChecker server -w " +
             args.workspace + db_data)


def handle_list_checkers(args):
    """
    List the supported checkers by the analyzers.
    List the default enabled and disabled checkers in the config.
    """
    context = generic_package_context.get_context()
    # If nothing is set, list checkers for all supported analyzers.
    enabled_analyzers = args.analyzers or analyzer_types.supported_analyzers
    analyzer_environment = analyzer_env.get_check_env(
        context.path_env_extra,
        context.ld_lib_path_extra)

    for ea in enabled_analyzers:
        if ea not in analyzer_types.supported_analyzers:
            LOG.error('Unsupported analyzer ' + str(ea))
            sys.exit(1)

    analyzer_config_map = \
        analyzer_types.build_config_handlers(args,
                                             context,
                                             enabled_analyzers)

    for ea in enabled_analyzers:
        # Get the config.
        config_handler = analyzer_config_map.get(ea)
        source_analyzer = \
            analyzer_types.construct_analyzer_type(ea,
                                                   config_handler,
                                                   None)

        checkers = source_analyzer.get_analyzer_checkers(config_handler,
                                                         analyzer_environment)

        default_checker_cfg = context.default_checkers_config.get(
            ea + '_checkers')

        analyzer_types.initialize_checkers(config_handler,
                                           checkers,
                                           default_checker_cfg)
        for checker_name, value in config_handler.checks().items():
            enabled, description = value
            if enabled:
                print(' + {0:50} {1}'.format(checker_name, description))
            else:
                print(' - {0:50} {1}'.format(checker_name, description))


def handle_server(args):
    """
    Starts the report viewer server.
    """
    if not host_check.check_zlib():
        sys.exit(1)

    workspace = args.workspace

    if (args.list or args.stop or args.stop_all) and \
            not (args.list ^ args.stop ^ args.stop_all):
        print("CodeChecker server: error: argument -l/--list and -s/--stop"
              "and --stop-all are mutually exclusive.")
        sys.exit(2)

    if args.list:
        instances = instance_manager.list()

        instances_on_multiple_hosts = any(True for inst in instances
                                          if inst['hostname'] !=
                                          socket.gethostname())
        if not instances_on_multiple_hosts:
            rows = [('Workspace', 'View port')]
        else:
            rows = [('Workspace', 'Computer host', 'View port')]

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
        util.print_table(rows)
        sys.exit(0)
    elif args.stop or args.stop_all:
        for i in instance_manager.list():
            # A STOP only stops the server associated with the given workspace
            # and view-port.
            if i['hostname'] != socket.gethostname() or (
                        args.stop and not (i['port'] == args.view_port and
                                           os.path.abspath(i['workspace']) ==
                                           os.path.abspath(workspace))):
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
        sys.exit(0)

    # WARNING
    # In case of SQLite args.dbaddress default value is used
    # for which the is_localhost should return true.
    if util.is_localhost(args.dbaddress) and not os.path.exists(workspace):
        os.makedirs(workspace)

    suppress_handler = generic_package_suppress_handler.\
        GenericSuppressHandler()
    if args.suppress is None:
        LOG.warning('No suppress file was given, suppressed results will '
                    'be only stored in the database.')
    else:
        if not os.path.exists(args.suppress):
            LOG.error('Suppress file ' + args.suppress + ' not found!')
            sys.exit(1)

    context = generic_package_context.get_context()
    context.codechecker_workspace = workspace
    session_manager.SessionManager.CodeChecker_Workspace = workspace
    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.codechecker_workspace,
                                             context.migration_root,
                                             check_env)
    conn_mgr = client.ConnectionManager(sql_server, args.check_address,
                                        args.check_port)
    if args.check_port:
        LOG.debug('Starting CodeChecker server and database server.')
        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)
        conn_mgr.start_report_server()
    else:
        LOG.debug('Starting database.')
        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)

    # Start database viewer.
    db_connection_string = sql_server.get_connection_string()

    suppress_handler.suppress_file = args.suppress
    LOG.debug('Using suppress file: ' + str(suppress_handler.suppress_file))

    checker_md_docs = os.path.join(context.doc_root, 'checker_md_docs')
    checker_md_docs_map = os.path.join(checker_md_docs,
                                       'checker_doc_map.json')
    with open(checker_md_docs_map, 'r') as dFile:
        checker_md_docs_map = json.load(dFile)

    package_data = {'www_root': context.www_root, 'doc_root': context.doc_root,
                    'checker_md_docs': checker_md_docs,
                    'checker_md_docs_map': checker_md_docs_map}

    client_db_access_server.start_server(package_data,
                                         args.view_port,
                                         db_connection_string,
                                         suppress_handler,
                                         args.not_host_only,
                                         context)


def handle_log(args):
    """
    Generates a build log by running the original build command.
    No analysis is done.
    """
    args.logfile = os.path.realpath(args.logfile)
    if os.path.exists(args.logfile):
        os.remove(args.logfile)

    context = generic_package_context.get_context()
    build_manager.perform_build_command(args.logfile,
                                        args.command,
                                        context)


def handle_debug(args):
    """
    Runs a debug command on the buildactions where the analysis
    failed for some reason.
    """
    context = generic_package_context.get_context()

    context.codechecker_workspace = args.workspace
    context.db_username = args.dbusername

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    sql_server = SQLServer.from_cmdline_args(args,
                                             context.codechecker_workspace,
                                             context.migration_root,
                                             check_env)
    sql_server.start(context.db_version_info, wait_for_start=True, init=False)

    debug_reporter.debug(context, sql_server.get_connection_string(),
                         args.force)


def handle_check(args):
    """
    Runs the original build and logs the buildactions.
    Based on the log runs the analysis.
    """
    try:
        if not host_check.check_zlib():
            sys.exit(1)

        args.workspace = os.path.abspath(args.workspace)
        if not os.path.isdir(args.workspace):
            os.mkdir(args.workspace)

        context = generic_package_context.get_context()
        context.codechecker_workspace = args.workspace
        context.db_username = args.dbusername

        log_file = build_manager.check_log_file(args, context)

        if not log_file:
            LOG.error("Failed to generate compilation command file: " +
                      log_file)
            sys.exit(1)

        actions = log_parser.parse_log(log_file,
                                       args.add_compiler_defaults)

        check_env = analyzer_env.get_check_env(context.path_env_extra,
                                               context.ld_lib_path_extra)

        sql_server = SQLServer.from_cmdline_args(args,
                                                 context.codechecker_workspace,
                                                 context.migration_root,
                                                 check_env)

        conn_mgr = client.ConnectionManager(sql_server, 'localhost',
                                            util.get_free_port())

        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)

        conn_mgr.start_report_server()

        LOG.debug("Checker server started.")

        analyzer.run_check(args, actions, context)

        LOG.info("Analysis has finished.")

        log_startserver_hint(args)

    except Exception as ex:
        LOG.error(ex)
        import traceback
        print(traceback.format_exc())
    finally:
        if not args.keep_tmp:
            if log_file:
                LOG.debug('Removing temporary log file: ' + log_file)
                os.remove(log_file)


def _do_quickcheck(args):
    """
    Handles the "quickcheck" command.

    For arguments see main function in CodeChecker.py.
    It also requires an extra property in args object, namely workspace which
    is a directory path as a string.
    This function is called from handle_quickcheck.
    """

    try:
        context = generic_package_context.get_context()

        context.codechecker_workspace = args.workspace
        args.name = "quickcheck"

        # Load severity map from config file.
        if os.path.exists(context.checkers_severity_map_file):
            with open(context.checkers_severity_map_file, 'r') as sev_file:
                severity_config = sev_file.read()

            context.severity_map = json.loads(severity_config)

        log_file = build_manager.check_log_file(args, context)
        actions = log_parser.parse_log(log_file,
                                       args.add_compiler_defaults)
        analyzer.run_quick_check(args, context, actions)

    except Exception as ex:
        LOG.error("Running quickcheck failed.")
    finally:
        if not args.keep_tmp:
            if log_file:
                LOG.debug('Removing temporary log file: ' + log_file)
                os.remove(log_file)


def handle_quickcheck(args):
    """
    Handles the "quickcheck" command using _do_quickcheck function.

    It creates a new temporary directory and sets it as workspace directory.
    After _do_quickcheck call it deletes the temporary directory and its
    content.
    """

    args.workspace = tempfile.mkdtemp(prefix='codechecker-qc')
    try:
        _do_quickcheck(args)
    finally:
        shutil.rmtree(args.workspace)


def consume_plist(item):
    plist, args, context = item
    LOG.info('Consuming ' + plist)

    action = build_action.BuildAction()
    action.analyzer_type = analyzer_types.CLANG_SA
    action.original_command = 'Imported from PList directly'

    rh = analyzer_types.construct_result_handler(args,
                                                 action,
                                                 context.run_id,
                                                 args.directory,
                                                 {},
                                                 None,
                                                 None,
                                                 not args.stdout)

    rh.analyzer_returncode = 0
    rh.buildaction.analyzer_type = 'Build action from plist'
    rh.buildaction.original_command = plist
    rh.analyzer_cmd = ''
    rh.analyzer.analyzed_source_file = ''  # TODO: fill from plist.
    rh.result_file = os.path.join(args.directory, plist)
    rh.handle_results()


def handle_plist(args):
    context = generic_package_context.get_context()
    context.codechecker_workspace = args.workspace
    context.db_username = args.dbusername

    if not args.stdout:
        args.workspace = os.path.realpath(args.workspace)
        if not os.path.isdir(args.workspace):
            os.mkdir(args.workspace)

        check_env = analyzer_env.get_check_env(context.path_env_extra,
                                               context.ld_lib_path_extra)

        sql_server = SQLServer.from_cmdline_args(args,
                                                 context.codechecker_workspace,
                                                 context.migration_root,
                                                 check_env)

        conn_mgr = client.ConnectionManager(sql_server,
                                            'localhost',
                                            util.get_free_port())

        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)

        conn_mgr.start_report_server()

        with client.get_connection() as connection:
            context.run_id = connection.add_checker_run(' '.join(sys.argv),
                                                        args.name,
                                                        context.version,
                                                        args.force)

    pool = multiprocessing.Pool(args.jobs)

    try:
        items = [(plist, args, context)
                 for plist in os.listdir(args.directory)]
        pool.map_async(consume_plist, items, 1).get(float('inf'))
        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()

    if not args.stdout:
        log_startserver_hint(args)


def handle_version_info(args):
    """
    Get and print the version information from the
    version config file and thrift API versions.
    """

    context = generic_package_context.get_context()

    print('Base package version: \t' + context.version).expandtabs(30)
    print('Package build date: \t' +
          context.package_build_date).expandtabs(30)
    print('Git hash: \t' + context.package_git_hash).expandtabs(30)
    print('DB schema version: \t' +
          str(context.db_version_info)).expandtabs(30)

    # Thift api version for the clients.
    from codeCheckerDBAccess import constants
    print(('Thrift client api version: \t' + constants.API_VERSION).
          expandtabs(30))
