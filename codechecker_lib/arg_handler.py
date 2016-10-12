# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle command line arguments.
"""
import os
import sys
import json
import tempfile
import shutil
import multiprocessing

from viewer_server import client_db_access_server

from codechecker_lib import build_action
from codechecker_lib import client
from codechecker_lib import generic_package_context
from codechecker_lib import analyzer
from codechecker_lib import log_parser
from codechecker_lib import util
from codechecker_lib import debug_reporter
from codechecker_lib import logger
from codechecker_lib import analyzer_env
from codechecker_lib import host_check
from codechecker_lib import generic_package_suppress_handler
from codechecker_lib.database_handler import SQLServer

from codechecker_lib import build_manager

from codechecker_lib.analyzers import analyzer_types

LOG = logger.get_new_logger('ARG_HANDLER')


def handle_list_checkers(args):
    """
    List the supported checkers by the analyzers.
    List the default enabled and disabled checkers in the config.
    """
    context = generic_package_context.get_context()
    enabled_analyzers = args.analyzers
    analyzer_environment = analyzer_env.get_check_env(context.path_env_extra,
                                                      context.ld_lib_path_extra)

    if not enabled_analyzers:
        # Noting set list checkers for all supported analyzers.
        enabled_analyzers = list(analyzer_types.supported_analyzers)

    enabled_analyzer_types = set()
    for ea in enabled_analyzers:
        if ea not in analyzer_types.supported_analyzers:
            LOG.info('Not supported analyzer ' + str(ea))
            sys.exit(1)
        else:
            enabled_analyzer_types.add(ea)

    analyzer_config_map = \
        analyzer_types.build_config_handlers(args,
                                             context,
                                             enabled_analyzer_types)

    for ea in enabled_analyzers:
        # Get the config.
        config_handler = analyzer_config_map.get(ea)
        source_analyzer = analyzer_types.construct_analyzer_type(ea,
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
        LOG.error("zlib error")
        sys.exit(1)

    try:
        workspace = args.workspace
    except AttributeError:
        # If no workspace value was set for some reason
        # in args set the default value.
        workspace = util.get_default_workspace()

    # WARNING
    # In case of SQLite args.dbaddress default value is used
    # for which the is_localhost should return true.

    local_db = util.is_localhost(args.dbaddress)
    if local_db and not os.path.exists(workspace):
        os.makedirs(workspace)

    if args.suppress is None:
        LOG.warning(
            "WARNING! No suppress file was given, suppressed results will " +
            'be only stored in the database.')

    else:
        if not os.path.exists(args.suppress):
            LOG.error('Suppress file ' + args.suppress + ' not found!')
            sys.exit(1)

    context = generic_package_context.get_context()
    context.codechecker_workspace = workspace
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
        LOG.debug('Starting codechecker server and database server.')
        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)
        conn_mgr.start_report_server(context.db_version_info)
    else:
        LOG.debug('Starting database.')
        sql_server.start(context.db_version_info, wait_for_start=True,
                         init=True)

    # Start database viewer.
    db_connection_string = sql_server.get_connection_string()

    suppress_handler = generic_package_suppress_handler.GenericSuppressHandler()
    try:
        suppress_handler.suppress_file = args.suppress
        LOG.debug('Using suppress file: ' + str(suppress_handler.suppress_file))
    except AttributeError as aerr:
        # Suppress file was not set.
        LOG.debug(aerr)

    package_data = {'www_root': context.www_root, 'doc_root': context.doc_root}

    checker_md_docs = os.path.join(context.doc_root, 'checker_md_docs')

    checker_md_docs_map = os.path.join(checker_md_docs,
                                       'checker_doc_map.json')

    package_data['checker_md_docs'] = checker_md_docs

    with open(checker_md_docs_map, 'r') as dFile:
        checker_md_docs_map = json.load(dFile)

    package_data['checker_md_docs_map'] = checker_md_docs_map

    client_db_access_server.start_server(package_data,
                                         args.view_port,
                                         db_connection_string,
                                         suppress_handler,
                                         args.not_host_only,
                                         context.db_version_info)


def handle_log(args):
    """
    Generates a build log by running the original build command.
    No analysis is done.
    """
    args.logfile = os.path.realpath(args.logfile)
    if os.path.exists(args.logfile):
        os.remove(args.logfile)

    context = generic_package_context.get_context()
    open(args.logfile, 'a').close()  # Same as linux's touch.
    build_manager.perform_build_command(args.logfile,
                                        args.command,
                                        context)


def handle_debug(args):
    """
    Runs a debug command on the buildactions where the analysis
    failed for some reason.
    """
    context = generic_package_context.get_context()

    try:
        workspace = args.workspace
    except AttributeError:
        # If no workspace value was set for some reason
        # in args set the default value.
        workspace = util.get_default_workspace()

    context.codechecker_workspace = workspace
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
            LOG.error("zlib error")
            sys.exit(1)

        try:
            workspace = args.workspace
        except AttributeError:
            # If no workspace value was set for some reason
            # in args set the default value.
            workspace = util.get_default_workspace()

        workspace = os.path.realpath(workspace)
        if not os.path.isdir(workspace):
            os.mkdir(workspace)

        context = generic_package_context.get_context()
        context.codechecker_workspace = workspace
        context.db_username = args.dbusername

        log_file = build_manager.check_log_file(args)

        if not log_file:
            log_file = build_manager.generate_log_file(args,
                                                       context,
                                                       args.quiet_build)
        if not log_file:
            LOG.error("Failed to generate compilation command file: " +
                      log_file)
            sys.exit(1)

        try:
            actions = log_parser.parse_log(log_file)
        except Exception as ex:
            LOG.error(ex)
            sys.exit(1)

        if not actions:
            LOG.warning('There are no build actions in the log file.')
            sys.exit(1)

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

        conn_mgr.start_report_server(context.db_version_info)

        LOG.debug("Checker server started.")

        analyzer.run_check(args,
                           actions,
                           context)

        LOG.info("Analysis has finished.")

        db_data = ""
        if args.postgresql:
            db_data += " --postgresql" \
                       + " --dbname " + args.dbname \
                       + " --dbport " + str(args.dbport) \
                       + " --dbusername " + args.dbusername

        LOG.info("To view results run:\nCodeChecker server -w " +
                 workspace + db_data)

    except Exception as ex:
        LOG.error(ex)
        import traceback
        print(traceback.format_exc())


def _do_quickcheck(args):
    """
    Handles the "quickcheck" command.

    For arguments see main function in CodeChecker.py. It also requires an extra
    property in args object, namely workspace which is a directory path as a
    string. This function is called from handle_quickcheck.
    """

    context = generic_package_context.get_context()

    try:
        workspace = args.workspace
    except AttributeError:
        # If no workspace value was set for some reason
        # in args set the default value.
        workspace = util.get_default_workspace()

    context.codechecker_workspace = workspace

    # Load severity map from config file.
    if os.path.exists(context.checkers_severity_map_file):
        with open(context.checkers_severity_map_file, 'r') as sev_conf_file:
            severity_config = sev_conf_file.read()

        context.severity_map = json.loads(severity_config)

    log_file = build_manager.check_log_file(args)

    if not log_file:
        log_file = build_manager.generate_log_file(args,
                                                   context,
                                                   args.quiet_build)
    if not log_file:
        LOG.error("Failed to generate compilation command file: " + log_file)
        sys.exit(1)

    try:
        actions = log_parser.parse_log(log_file)
    except Exception as ex:
        LOG.error(ex)
        sys.exit(1)

    if not actions:
        LOG.warning('There are no build actions in the log file.')
        sys.exit(1)

    analyzer.run_quick_check(args, context, actions)


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
                                                 not args.stdout)

    rh.handle_plist(os.path.join(args.directory, plist))


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

        conn_mgr.start_report_server(context.db_version_info)

        with client.get_connection() as connection:
            package_version = context.version['major'] + '.' + context.version[
                'minor']
            context.run_id = connection.add_checker_run(' '.join(sys.argv),
                                                        args.name,
                                                        package_version,
                                                        args.force)

    pool = multiprocessing.Pool(args.jobs)

    try:
        items = [(plist, args, context) for plist in os.listdir(args.directory)]
        pool.map_async(consume_plist, items, 1).get(float('inf'))
        pool.close()
    except Exception:
        pool.terminate()
        raise
    finally:
        pool.join()


def handle_version_info(args):
    """
    Get and print the version information from the
    version config file and thrift API versions.
    """

    context = generic_package_context.get_context()
    version_file = context.version_file

    try:
        with open(version_file) as v_file:
            v_data = v_file.read()

        version_data = json.loads(v_data)
        base_version = version_data['version']['major'] + \
                       '.' + version_data['version']['minor']
        db_schema_version = version_data['db_version']['major'] + \
                            '.' + version_data['db_version']['minor']

        print('Base package version: \t' + base_version).expandtabs(30)
        print('Package build date: \t' +
              version_data['package_build_date']).expandtabs(30)
        print('Git hash: \t' + version_data['git_hash']).expandtabs(30)
        print('DB schema version: \t' + db_schema_version).expandtabs(30)

    except ValueError as verr:
        LOG.error('Failed to decode version information from the config file.')
        LOG.error(verr)
        sys.exit(1)

    except IOError as ioerr:
        LOG.error('Failed to read version config file: ' + version_file)
        LOG.error(ioerr)
        sys.exit(1)

    # Thift api version for the clients.
    from codeCheckerDBAccess import constants
    print('Thrift client api version: \t' + constants.API_VERSION).\
        expandtabs(30)
